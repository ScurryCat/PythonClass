from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from courses.accounts import ROLE_STUDENT, ensure_account
from courses.models import Course, LearningResource, Student, StudyTask, Submission


DJANGO_COURSE = 'Django 从入门到上线'
DATA_COURSE = '数据分析与可视化'
RESOURCES = {
    DJANGO_COURSE: (
        (
            'Django 模板查找与继承',
            '排查 TemplateDoesNotExist，检查模板路径并理解模板继承。',
            'TemplateDoesNotExist,模板路径,模板继承',
            'https://docs.djangoproject.com/zh-hans/5.2/topics/templates/',
        ),
        (
            'Django 数据库迁移',
            '排查 OperationalError 和数据表不存在，学习同步迁移记录和数据库。',
            'OperationalError,数据迁移,数据表',
            'https://docs.djangoproject.com/zh-hans/5.2/topics/migrations/',
        ),
        (
            'Django ORM 查询入门',
            '练习通过 QuerySet 查询和筛选模型数据。',
            'ORM,QuerySet,查询',
            'https://docs.djangoproject.com/zh-hans/5.2/topics/db/queries/',
        ),
    ),
    DATA_COURSE: (
        (
            'pandas 缺失值处理', '识别缺失值并练习过滤、填充和插值。',
            '缺失值,填充,插值', 'https://pandas.pydata.org/docs/user_guide/missing_data.html',
        ),
        (
            'pandas 分组统计', '了解 groupby 并练习分组与聚合。',
            'groupby,分组,聚合', 'https://pandas.pydata.org/docs/user_guide/groupby.html',
        ),
        (
            'pandas 入门绘图', '创建折线、柱状和散点图。',
            '绘图,散点图,可视化', 'https://pandas.pydata.org/docs/getting_started/intro_tutorials/04_plotting.html',
        ),
    ),
}


class Command(BaseCommand):
    help = '写入两门课程的督导演示数据，可重复执行并保留已有提交'

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('seed_data', stdout=self.stdout)
        courses = Course.objects.in_bulk(RESOURCES.keys())
        django_course = courses[DJANGO_COURSE]
        now = timezone.now()
        for course_title, resources in RESOURCES.items():
            for title, description, tags, url in resources:
                LearningResource.objects.get_or_create(
                    course=courses[course_title], title=title,
                    defaults={'description': description, 'tags': tags, 'url': url},
                )

        StudyTask.objects.get_or_create(
            course=django_course, title='Web 实验排错记录',
            defaults={
                'instructions': '运行 Django 页面，记录报错、排查方法与最终结果。可上传报错截图识别文字。',
                'due_at': now + timedelta(days=7),
            },
        )
        StudyTask.objects.get_or_create(
            course=courses[DATA_COURSE], title='数据清理与分组练习',
            defaults={
                'instructions': '清理数据中的缺失值，按类别统计数量，并记录处理方法。',
                'due_at': now + timedelta(days=5),
            },
        )

        task, _ = StudyTask.objects.get_or_create(
            course=django_course, title='后台页面实践',
            defaults={
                'instructions': '完成后台列表页并说明模板与查询的实现。',
                'due_at': now - timedelta(days=2),
            },
        )
        late_student, _ = Student.objects.get_or_create(
            sno='DMDJ001', defaults={
                'name': '演示学生', 'course': django_course, 'enroll_at': timezone.localdate(),
            },
        )
        reviewed_student = Student.objects.filter(pk='2024001', course=django_course).first()
        if reviewed_student is not None:
            Submission.objects.get_or_create(
                task=task, student=reviewed_student,
                defaults={
                    'content': '已通过模板渲染课程列表，并验证空数据提示。',
                    'submitted_at': task.due_at - timedelta(hours=3),
                    'status': Submission.Status.REVIEWED,
                    'feedback': '列表展示清晰，建议增加一组排序测试。',
                    'reviewed_at': task.due_at + timedelta(hours=1),
                },
            )
        if late_student.course_id == django_course.pk:
            ensure_account(ROLE_STUDENT, late_student)
            Submission.objects.get_or_create(
                task=task, student=late_student,
                defaults={
                    'content': '已完成后台列表页，补交运行结果。',
                    'submitted_at': task.due_at + timedelta(hours=6),
                },
            )
        self.stdout.write(self.style.SUCCESS('督导演示数据已准备。'))
