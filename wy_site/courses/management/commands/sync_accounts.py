"""给所有还没有登录账号的讲师 / 学生补建账号。

典型场景：
  · 通过 Django 后台或前台添加了新的讲师 / 学生，想让 TA 能登录；
  · 用原生 SQL 导入了业务数据，但没有登录账号；
  · 演示账号密码被改乱了，想统一恢复成默认密码。

用法：
  python manage.py sync_accounts
  python manage.py sync_accounts --reset-passwords

密码规则：教师默认 teacher123，学生默认 student123（可在 courses/accounts.py 修改）。
"""

from django.core.management.base import BaseCommand

from courses.accounts import DEFAULT_PASSWORDS, ROLE_STUDENT, ROLE_TEACHER, sync_accounts
from courses.models import Student, Teacher


class Command(BaseCommand):
    help = '为已有讲师/学生补建登录账号；--reset-passwords 可把密码重置为默认值'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='把已有的教师/学生账号密码重置为默认密码（慎用）',
        )

    def handle(self, *args, **options):
        reset = options['reset_passwords']
        stats = sync_accounts(reset_password=reset)

        self.stdout.write('')
        self.stdout.write('-' * 56)
        for role, (model, label) in (
            (ROLE_TEACHER, (Teacher, '教师')),
            (ROLE_STUDENT, (Student, '学生')),
        ):
            item = stats[role]
            self.stdout.write(
                '%s：新增账号 %d 个，已存在 %d 个（业务数据共 %d 条）'
                % (label, item['created'], item['existing'], model.objects.count())
            )

        if reset:
            self.stdout.write(self.style.WARNING('已把所有教师/学生账号密码重置为默认密码。'))
        self.stdout.write('默认密码：教师 %s / 学生 %s'
                          % (DEFAULT_PASSWORDS[ROLE_TEACHER], DEFAULT_PASSWORDS[ROLE_STUDENT]))
        self.stdout.write('账号规则：教师用「昵称」登录，学生用「学号」登录。')
        self.stdout.write('-' * 56)
        self.stdout.write(self.style.SUCCESS('登录账号同步完成。'))
