import datetime as dt
import io
from pathlib import Path

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .accounts import ensure_account
from . import models


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SupervisionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = models.Teacher.objects.create(nickname='测试讲师')
        cls.other_teacher = models.Teacher.objects.create(nickname='另一讲师')
        cls.teacher_account, _ = ensure_account('teacher', cls.teacher)
        cls.other_teacher_account, _ = ensure_account('teacher', cls.other_teacher)

        cls.course = cls.make_course('Django 练习', cls.teacher)
        cls.other_course = cls.make_course('数据分析练习', cls.other_teacher)
        cls.student = cls.make_student('101', cls.course)
        cls.late_student = cls.make_student('102', cls.course)
        cls.waiting_student = cls.make_student('103', cls.course)
        cls.other_student = cls.make_student('201', cls.other_course)
        cls.student_account, _ = ensure_account('student', cls.student)
        cls.other_student_account, _ = ensure_account('student', cls.other_student)

    @staticmethod
    def make_course(title, teacher):
        return models.Course.objects.create(
            title=title, teacher=teacher, price=0, volume=12, online=dt.date(2025, 1, 1),
        )

    @staticmethod
    def make_student(sno, course):
        return models.Student.objects.create(
            sno=sno, name=f'演示学生 {sno}', course=course, enroll_at=dt.date(2025, 1, 1),
        )

    def task(self, **overrides):
        values = {
            'course': self.course, 'title': '实践任务', 'instructions': '记录实验结果。',
            'due_at': timezone.now() + dt.timedelta(days=1),
        }
        return models.StudyTask.objects.create(**(values | overrides))

    @staticmethod
    def url(name, pk=None):
        return reverse(f'courses:{name}', args=[pk] if pk is not None else None)

    def test_workspaces_require_login(self):
        for page in ('teacher_tasks', 'student_tasks'):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(self.url(page)).status_code, 302)

    def test_teacher_can_publish_only_to_own_course(self):
        self.client.force_login(self.teacher_account.user)
        due = timezone.localtime(timezone.now() + dt.timedelta(days=2))
        data = {'title': '模板练习', 'instructions': '提交运行结果。',
                'due_at': due.strftime('%Y-%m-%dT%H:%M')}
        self.client.post(self.url('task_create'), {**data, 'course': self.other_course.pk})
        self.assertFalse(models.StudyTask.objects.filter(title=data['title']).exists())
        response = self.client.post(
            self.url('task_create'), {**data, 'course': self.course.pk},
        )
        self.assertEqual(response.status_code, 302)
        task = models.StudyTask.objects.get(title=data['title'])
        self.assertEqual(task.course, self.course)

        self.client.force_login(self.student_account.user)
        self.assertContains(self.client.get(self.url('student_tasks')), task.title)

    def test_cross_course_access_is_denied_for_pages_and_ai(self):
        task = self.task()
        self.client.force_login(self.other_student_account.user)
        self.assertNotContains(self.client.get(self.url('student_tasks')), task.title)
        for name in ('student_task', 'task_ocr', 'task_recommend'):
            with self.subTest(name=name):
                self.assertIn(self.client.post(self.url(name, task.pk)).status_code, (403, 404))
        self.client.force_login(self.other_teacher_account.user)
        self.assertNotContains(self.client.get(self.url('teacher_tasks')), task.title)
        self.assertIn(self.client.get(self.url('task_progress', task.pk)).status_code, (403, 404))

    def test_submission_persists_and_repeat_post_cannot_overwrite(self):
        task = self.task()
        self.client.force_login(self.student_account.user)
        link = self.url('student_task', task.pk)
        payload = {'content': '我的运行结果', 'recognized_text': 'Hello Django',
                   'difficulties': '模板继承', 'student': self.other_student.pk}
        self.assertEqual(self.client.post(link, payload).status_code, 302)
        self.client.post(link, {**payload, 'content': '第二次请求'})
        submission = models.Submission.objects.get(task=task)
        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.content, payload['content'])
        self.assertEqual(submission.recognized_text, payload['recognized_text'])
        self.assertEqual(submission.difficulties, payload['difficulties'])
        self.assertContains(self.client.get(link), payload['content'])

    def test_teacher_progress_distinguishes_missing_on_time_and_late(self):
        deadline = timezone.now() - dt.timedelta(days=1)
        task = self.task(due_at=deadline)
        for student, submitted_at in (
            (self.student, deadline - dt.timedelta(minutes=1)),
            (self.late_student, deadline + dt.timedelta(minutes=1)),
        ):
            submission = models.Submission.objects.create(
                task=task, student=student, content='提交内容',
            )
            models.Submission.objects.filter(pk=submission.pk).update(submitted_at=submitted_at)

        self.client.force_login(self.teacher_account.user)
        response = self.client.get(self.url('task_progress', task.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['counts']['pending'], 2)
        self.assertEqual(response.context['counts']['overdue'], 1)
        rows = {row['student'].pk: row for row in response.context['rows']}
        self.assertFalse(rows[self.student.pk]['late'])
        self.assertTrue(rows[self.late_student.pk]['late'])
        self.assertEqual(rows[self.waiting_student.pk]['status'], 'overdue')
        self.assertContains(response, '迟交')

    def test_teacher_returns_student_resubmits_and_teacher_publishes_feedback(self):
        task = self.task(due_at=timezone.now() - dt.timedelta(days=1))
        submission = models.Submission.objects.create(
            task=task, student=self.student, content='初稿',
        )
        review_url = self.url('submission_review', submission.pk)
        self.client.force_login(self.other_teacher_account.user)
        self.assertIn(self.client.get(review_url).status_code, (403, 404))

        self.client.force_login(self.teacher_account.user)
        self.assertEqual(self.client.post(review_url, {
            'feedback': '请补充运行结果。', 'action': 'return',
        }).status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, models.Submission.Status.RETURNED)

        self.client.force_login(self.student_account.user)
        link = self.url('student_task', task.pk)
        self.assertContains(self.client.get(link), '请补充运行结果。')
        self.assertEqual(self.client.post(link, {'content': '已补充运行结果'}).status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, models.Submission.Status.PENDING)
        self.assertEqual(submission.content, '已补充运行结果')

        self.client.force_login(self.teacher_account.user)
        self.assertEqual(self.client.post(review_url, {
            'feedback': '结果齐全，继续练习。', 'action': 'review',
        }).status_code, 302)
        self.client.force_login(self.student_account.user)
        self.assertContains(self.client.get(link), '结果齐全，继续练习。')

    def test_student_write_requires_csrf(self):
        task = self.task()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student_account.user)
        for endpoint in ('student_task', 'task_ocr', 'task_recommend'):
            self.assertEqual(client.post(self.url(endpoint, task.pk)).status_code, 403)

    def test_course_recommendation_ranks_by_input_and_hides_other_courses(self):
        task = self.task()
        for course, title, term in (
            (self.course, 'Django 模板继承', '模板继承'),
            (self.course, 'Django 数据迁移', '数据迁移'),
            (self.other_course, '外部课程模板资源', '模板继承'),
        ):
            models.LearningResource.objects.create(
                course=course, title=title, description=f'{term}案例与练习', tags=term,
                url='https://docs.djangoproject.com/en/5.2/',
            )

        self.assertTrue(admin.site.is_registered(models.LearningResource))
        self.client.force_login(self.student_account.user)
        link = self.url('task_recommend', task.pk)
        for term in ('模板继承', '数据迁移'):
            with self.subTest(term=term):
                response = self.client.post(link, {'difficulties': f'如何完成{term}？'})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertLessEqual(len(result['keywords']), 5)
                self.assertTrue(result['keywords'])
                titles = [resource['title'] for resource in result['resources']]
                self.assertIn(term, titles[0])
                self.assertNotIn('外部课程模板资源', titles)
                self.assertTrue(result['resources'][0]['reason'])
        self.assertEqual(self.client.post(link, {'difficulties': '海豚鱼塘'}).json()['resources'], [])

    def test_ocr_screenshots_feed_keywords_and_recommendations(self):
        task = self.task()
        self.client.force_login(self.student_account.user)
        link = self.url('task_ocr', task.pk)
        fixture_dir = Path(__file__).resolve().parents[2] / 'docs' / 'demo'
        fixtures = (
            ('template-output.png', 'TemplateDoesNotExist', 'Django 模板查找与继承'),
            ('migration-output.png', 'OperationalError', 'Django 数据库迁移'),
        )
        for _name, term, title in fixtures:
            models.LearningResource.objects.create(
                course=self.course, title=title, description=f'{term} 排查步骤', tags=term,
                url='https://docs.djangoproject.com/en/5.2/',
            )
        for name, term, title in fixtures:
            with self.subTest(image=name):
                with (fixture_dir / name).open('rb') as image:
                    response = self.client.post(link, {'image': image})
                self.assertEqual(response.status_code, 200, response.content)
                recognized_text = response.json()['text']
                self.assertIn(term, recognized_text)
                result = self.client.post(
                    self.url('task_recommend', task.pk), {'recognized_text': recognized_text},
                ).json()
                self.assertIn(term, result['keywords'])
                self.assertEqual(result['resources'][0]['title'], title)

        invalid = SimpleUploadedFile('invalid.png', b'invalid image', 'image/png')
        self.assertEqual(self.client.post(link, {'image': invalid}).status_code, 400)
        blank = io.BytesIO()
        Image.new('RGB', (400, 200), 'white').save(blank, format='PNG')
        missing_text = SimpleUploadedFile('blank.png', blank.getvalue(), 'image/png')
        response = self.client.post(link, {'image': missing_text})
        self.assertIn(response.status_code, (400, 422))
        self.assertFalse(models.Submission.objects.filter(task=task).exists())

    @override_settings(DASHSCOPE_API_KEY='')
    def test_missing_api_key_does_not_block_manual_feedback(self):
        task = self.task()
        submission = models.Submission.objects.create(
            task=task, student=self.student, content='学生提交内容',
        )
        self.client.force_login(self.teacher_account.user)
        response = self.client.post(
            self.url('feedback_draft', submission.pk), {'review_points': '描述运行结果'},
        )
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()['error'])
        submission.refresh_from_db()
        self.assertFalse(submission.feedback)
        self.assertEqual(self.client.post(self.url('submission_review', submission.pk), {
            'feedback': '请描述运行结果。', 'action': 'review',
        }).status_code, 302)
