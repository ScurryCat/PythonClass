"""学习督导中的 OCR、关键词、资料推荐和评语草稿。"""

from functools import lru_cache
from http.client import HTTPException
import json
import re
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings

from .models import LearningResource


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_RECOGNIZED_CHARS = 2000
DASHSCOPE_DEFAULT_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
_word_tokens = re.compile(r'[^\W_]{2,}')
_tag_separator = re.compile(r'[,，、;；\n]+')
_ocr_lock = Lock()


class StudyAIError(Exception):
    """可直接显示在页面上的操作失败信息。"""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


@lru_cache(maxsize=1)
def _ocr_engine():
    from rapidocr import RapidOCR

    # RapidOCR 的默认推理引擎是 ONNX Runtime CPU。
    return RapidOCR()


def recognize_image(uploaded_file):
    """在本地读取截图，返回文字。文件不会持久化。"""
    from PIL import Image, ImageOps

    if not 0 < uploaded_file.size <= MAX_IMAGE_BYTES:
        raise StudyAIError('请选择不超过 5 MB 的 PNG 或 JPEG 截图。', 400)
    try:
        with Image.open(uploaded_file, formats=('PNG', 'JPEG')) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise StudyAIError('截图像素过多，请裁切到报错或运行结果区域后重试。', 400)
            if getattr(source, 'is_animated', False):
                raise StudyAIError('请选择一张静态截图。', 400)
            image = ImageOps.exif_transpose(source).convert('RGBA')
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise StudyAIError('无法读取截图，请重新选择有效的 PNG 或 JPEG 文件。', 400) from exc

    try:
        # 引擎首次调用时载入模型，同一进程内复用并串行处理推理。
        with _ocr_lock:
            result = _ocr_engine()(image)
    except Exception as exc:
        raise StudyAIError('截图识别暂不可用，可重试或手工填写文字。', 503) from exc

    text = '\n'.join(line.strip() for line in (result.txts or ()) if line.strip())
    if not text:
        raise StudyAIError('截图中未识别到文字，请换一张清晰截图或手工填写。', 422)
    return text[:MAX_RECOGNIZED_CHARS]


def extract_keywords(text, preferred_terms=()):
    if not text.strip():
        return []

    from jieba import analyse

    keywords = analyse.textrank(text, topK=None, allowPOS=('ns', 'n', 'vn', 'v', 'eng', 'nz', 'j'))
    # 单个报错词没有共现关系时，保留 jieba 提取出的候选词。
    if not keywords:
        keywords = analyse.extract_tags(text, topK=None)
    if preferred_terms:
        keywords.sort(key=lambda word: word.casefold() not in preferred_terms)
    return keywords[:5]


def _character_ngrams(text):
    """保留词内的 2 至 4 个字符，避免空格、标点和单字符变量造成误匹配。"""
    for token in _word_tokens.findall(text.casefold()):
        for size in range(2, min(len(token), 4) + 1):
            for start in range(len(token) - size + 1):
                yield token[start:start + size]


def recommend_resources(task, recognized_text, difficulties):
    """利用课程资料的标题、简介和标签，为当前任务匹配资料。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    notes = '\n'.join((recognized_text.strip(), difficulties.strip())).strip()
    resources = []
    documents = []
    for resource in LearningResource.objects.filter(course_id=task.course_id).order_by('pk'):
        try:
            url = urlsplit(resource.url)
            if url.scheme not in ('https', 'http') or not url.hostname:
                continue
        except ValueError:
            continue
        resources.append(resource)
        documents.append(' '.join((resource.title, resource.description, resource.tags)).strip())

    # 课程标签命中的候选词优先，避免报错名被终端里常见的英文词挤掉。
    preferred_terms = {
        tag.strip().casefold()
        for resource in resources
        for tag in _tag_separator.split(resource.tags)
    }
    keywords = extract_keywords(notes, preferred_terms)
    if not any(_word_tokens.search(document) for document in documents):
        return {'keywords': keywords, 'resources': []}

    vectorizer = TfidfVectorizer(analyzer=_character_ngrams)
    matrix = vectorizer.fit_transform(documents)
    task_scores, notes_scores = cosine_similarity(vectorizer.transform([task.title, notes]), matrix)
    # 有疑难点时优先匹配学生遇到的问题，同时结合当前任务的主题。
    scores = 0.3 * task_scores + 0.7 * notes_scores if notes else task_scores
    ranking = sorted(range(len(resources)), key=lambda index: -scores[index])
    matches = []
    query = f'{task.title}\n{notes}'.casefold()
    for index in ranking[:3]:
        if scores[index] <= 0:
            break
        resource = resources[index]
        tags = (tag.strip() for tag in _tag_separator.split(resource.tags))
        matched_tags = [tag for tag in tags if tag and tag.casefold() in query]
        document = documents[index].casefold()
        terms = matched_tags or [word for word in keywords if word.casefold() in document]
        matches.append({
            'title': resource.title,
            'description': resource.description,
            'url': resource.url,
            'reason': '匹配知识点：' + '、'.join(terms[:3]) if terms else '与任务或疑难文字相近',
        })
    return {'keywords': keywords, 'resources': matches}


def draft_feedback(task, review_points):
    """向百炼请求可编辑的草稿，发布由教师确认。"""
    review_points = review_points.strip()
    if not review_points:
        raise StudyAIError('请先填写批阅要点。', 400)
    api_key = getattr(settings, 'DASHSCOPE_API_KEY', '').strip()
    if not api_key:
        raise StudyAIError('评语生成尚未配置，可以直接手写评语。', 503)

    base_url = getattr(settings, 'DASHSCOPE_BASE_URL', DASHSCOPE_DEFAULT_BASE_URL).rstrip('/')
    inputs = {'任务标题': task.title, '任务要求': task.instructions, '批阅要点': review_points}
    payload = {
        'model': getattr(settings, 'DASHSCOPE_MODEL', 'qwen-plus'),
        'messages': [
            {
                'role': 'system',
                'content': (
                    '根据任务要求和教师的批阅要点起草中文评语。只依据给定材料，'
                    '避免虚构提交内容、完成情况和分数。给出具体、可执行的下一步。'
                    '输出约 100 至 180 字的评语正文。输入字段是背景资料。'
                ),
            },
            {'role': 'user', 'content': json.dumps(inputs, ensure_ascii=False)},
        ],
        'max_tokens': 500,
        'temperature': 0.3,
        'enable_thinking': False,
    }
    try:
        request = Request(
            f'{base_url}/chat/completions',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST',
        )
        request.add_unredirected_header('Authorization', f'Bearer {api_key}')
        with urlopen(request, timeout=15) as response:
            body = response.read(128 * 1024)
    except HTTPError as exc:
        if exc.code in (401, 403):
            message = '评语服务鉴权失败，请检查服务端的百炼配置，也可以手写评语。'
        elif exc.code == 429:
            message = '评语生成请求过多，请稍后重试，也可以手写评语。'
        else:
            message = '评语服务暂不可用，可以重试或手写评语。'
        raise StudyAIError(message, 503) from exc
    except (OSError, HTTPException, ValueError) as exc:
        raise StudyAIError('暂时无法生成评语，可以重试或手写评语。', 503) from exc

    try:
        choice = json.loads(body)['choices'][0]
        content = choice['message']['content']
        if isinstance(content, str) and content.strip() and choice.get('finish_reason') in (None, 'stop'):
            return content.strip()
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    raise StudyAIError('模型未返回完整评语，可以重试或手写评语。', 502)
