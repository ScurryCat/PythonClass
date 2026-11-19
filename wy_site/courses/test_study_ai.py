from datetime import date
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .models import Course, LearningResource, Teacher
from .study_ai import StudyAIError, draft_feedback, extract_keywords, recognize_image, recommend_resources


class StudyAITests(SimpleTestCase):
    def test_invalid_screenshot_returns_input_error(self):
        upload = SimpleUploadedFile('screen.png', b'not a picture', content_type='image/png')
        with self.assertRaises(StudyAIError) as raised:
            recognize_image(upload)
        self.assertEqual(raised.exception.status_code, 400)

    def test_extract_keywords_from_learning_notes(self):
        keywords = extract_keywords('Django 模型迁移失败。检查数据库迁移记录，修复模型字段冲突。')
        self.assertTrue(any('迁移' in word for word in keywords))
        self.assertLessEqual(len(keywords), 5)
        self.assertEqual(extract_keywords('   '), [])

    @override_settings(
        DASHSCOPE_API_KEY='example-key',
        DASHSCOPE_BASE_URL='https://dashscope.aliyuncs.com/compatible-mode/v1',
        DASHSCOPE_MODEL='qwen-plus',
    )
    @patch('courses.study_ai.urlopen')
    def test_draft_uses_qwen_with_only_task_and_review_context(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(json.dumps({
            'choices': [{'message': {'content': ' 请补充迁移记录。 '}, 'finish_reason': 'stop'}],
        }).encode('utf-8'))
        task = SimpleNamespace(title='模型迁移', instructions='提交迁移命令与运行结果。')
        self.assertEqual(draft_feedback(task, '缺少迁移记录'), '请补充迁移记录。')

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), 'POST')
        self.assertTrue(request.full_url.endswith('/compatible-mode/v1/chat/completions'))
        self.assertEqual(request.get_header('Authorization'), 'Bearer example-key')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'qwen-plus')
        self.assertEqual(json.loads(payload['messages'][1]['content']), {
            '任务标题': task.title,
            '任务要求': task.instructions,
            '批阅要点': '缺少迁移记录',
        })

    @override_settings(DASHSCOPE_API_KEY='example-key')
    @patch('courses.study_ai.urlopen', side_effect=URLError('private connection details'))
    def test_draft_network_failure_preserves_manual_review(self, mock_urlopen):
        task = SimpleNamespace(title='模型迁移', instructions='提交迁移记录。')
        with self.assertRaises(StudyAIError) as raised:
            draft_feedback(task, '缺少迁移记录')
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn('手写评语', str(raised.exception))
        self.assertNotIn('private connection details', str(raised.exception))


class ResourceRecommendationTests(TestCase):
    def test_lone_variable_and_spacing_do_not_make_an_unrelated_match(self):
        today = date(2026, 11, 19)
        teacher = Teacher.objects.create(nickname='资料验证讲师')
        course = Course.objects.create(
            title='课程演示', teacher=teacher, price=0, volume=20, online=today,
        )
        LearningResource.objects.create(
            course=course, title='缓存 A 清理', description='回收存储空间。',
            tags='缓存', url='https://example.com/cache',
        )
        task = SimpleNamespace(title='数据分析', course_id=course.pk)
        result = recommend_resources(task, '', '地图 A 路径')
        self.assertEqual(result['resources'], [])
