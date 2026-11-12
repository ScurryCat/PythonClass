"""
一键写入演示数据，并同步讲师 / 学生的登录账号。

用法：
    python manage.py seed_data                      # 写入数据 + 补建账号，已存在的自动跳过
    python manage.py seed_data --reset              # 清空三张表和关联账号后重写（会二次确认）
    python manage.py seed_data --reset --no-input   # 无人值守清空重建
    python manage.py seed_data --reset-passwords    # 顺便把账号密码重置为默认值

数据来源：courses/seed.py
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from courses.accounts import DEFAULT_PASSWORDS, sync_accounts
from courses.models import Course, Student, Teacher, UserProfile
from courses.seed import COURSES, STUDENTS, TEACHERS

KINDS = ('讲师', '课程', '学生')


class Command(BaseCommand):
    help = '写入演示数据（讲师 / 课程 / 学生）并同步登录账号，可重复执行，不会产生重复记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='先清空 teacher / courses / student 三张表，再写入测试数据（会删除现有数据）',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='搭配 --reset 使用，跳过「是否清空」的二次确认',
        )
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='把已有教师/学生账号的密码重置为默认密码',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset'] and not self._confirm_reset(options['no_input']):
            self.stdout.write('已取消，数据库没有任何改动。')
            return

        if options['reset']:
            self._reset()

        created = dict.fromkeys(KINDS, 0)
        skipped = dict.fromkeys(KINDS, 0)

        # ---- 1. 讲师：课程要引用它，必须最先写
        for item in TEACHERS:
            obj, is_new = Teacher.objects.get_or_create(
                nickname=item['nickname'],
                defaults={
                    'introduction': item['introduction'],
                    'fans': item['fans'],
                },
            )
            if is_new:
                created['讲师'] += 1
            else:
                skipped['讲师'] += 1
                self._note_skip('讲师', obj.nickname)

        # ---- 2. 课程：用课程名（主键）+ 讲师外键
        for item in COURSES:
            teacher = Teacher.objects.filter(pk=item['teacher']).first()
            if teacher is None:
                self.stderr.write(self.style.ERROR(
                    '跳过课程「%s」：找不到讲师「%s」' % (item['title'], item['teacher'])
                ))
                continue

            obj, is_new = Course.objects.get_or_create(
                title=item['title'],
                defaults={
                    'teacher': teacher,
                    'type': item['type'],
                    'price': item['price'],
                    'volume': item['volume'],
                    'online': item['online'],
                },
            )
            if is_new:
                created['课程'] += 1
            else:
                skipped['课程'] += 1
                self._note_skip('课程', obj.title)

        # ---- 3. 学生：course 可以为空
        for item in STUDENTS:
            course = None
            if item['course']:
                course = Course.objects.filter(pk=item['course']).first()
                if course is None:
                    self.stderr.write(self.style.WARNING(
                        '学生「%s」的课程「%s」不存在，将按「未选课」写入' % (item['name'], item['course'])
                    ))

            obj, is_new = Student.objects.get_or_create(
                sno=item['sno'],
                defaults={
                    'name': item['name'],
                    'gender': item['gender'],
                    'age': item['age'],
                    'email': item['email'],
                    'phone': item['phone'],
                    'course': course,
                    'enroll_at': item['enroll_at'],
                    'introduction': item['introduction'],
                },
            )
            if is_new:
                created['学生'] += 1
            else:
                skipped['学生'] += 1
                self._note_skip('学生', obj.sno)

        account_stats = sync_accounts(reset_password=options['reset_passwords'])
        self._report(created, skipped)
        self._report_accounts(account_stats)

    # ------------------------------------------------------------------ 辅助
    def _confirm_reset(self, no_input):
        if no_input:
            return True
        self.stdout.write(self.style.WARNING(
            '警告：--reset 会删除 teacher / courses / student 里的全部数据。'
        ))
        answer = input('确定继续吗？[y/N] ')
        return answer.strip().lower() in ('y', 'yes')

    def _reset(self):
        self.stdout.write('正在清空数据…')
        # 先清理关联登录账号，避免留下没有业务数据可绑定的孤儿账号
        linked_user_ids = list(UserProfile.objects.values_list('user_id', flat=True))
        if linked_user_ids:
            get_user_model().objects.filter(pk__in=linked_user_ids).delete()
            self.stdout.write('  已删除关联登录账号：%d 个' % len(linked_user_ids))

        # 再删有外键的一方，避免受约束影响
        deleted_students, _ = Student.objects.all().delete()
        deleted_courses, _ = Course.objects.all().delete()
        deleted_teachers, _ = Teacher.objects.all().delete()
        self.stdout.write('  已删除：学生 %d / 课程 %d / 讲师 %d'
                          % (deleted_students, deleted_courses, deleted_teachers))

    def _note_skip(self, kind, key):
        self.stdout.write('  跳过已存在的%s：%s' % (kind, key))

    def _report(self, created, skipped):
        self.stdout.write('')
        self.stdout.write('-' * 52)
        for kind in KINDS:
            self.stdout.write('  %s：新增 %d 条，已存在跳过 %d 条'
                              % (kind, created[kind], skipped[kind]))
        self.stdout.write('-' * 52)
        self.stdout.write(self.style.SUCCESS(
            '完成！当前库中共有 讲师 %d / 课程 %d / 学生 %d 条记录。'
            % (Teacher.objects.count(), Course.objects.count(), Student.objects.count())
        ))
        self.stdout.write('启动服务器查看：python manage.py runserver')

    def _report_accounts(self, stats):
        self.stdout.write('')
        self.stdout.write('登录账号：')
        for role in ('teacher', 'student'):
            label = '教师' if role == 'teacher' else '学生'
            item = stats[role]
            self.stdout.write('  %s：新增 %d 个，已有 %d 个'
                              % (label, item['created'], item['existing']))
        self.stdout.write('  初始密码：教师 %s / 学生 %s'
                          % (DEFAULT_PASSWORDS['teacher'], DEFAULT_PASSWORDS['student']))
        self.stdout.write('  账号规则：教师用「昵称」登录，学生用「学号」登录。')
