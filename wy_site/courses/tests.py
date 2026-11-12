import datetime as dt

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from courses.accounts import (
    DEFAULT_PASSWORDS,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ensure_account,
    internal_username,
    sync_accounts,
)
from courses.admin import TeacherAdmin
from courses.forms import INVALID_LOGIN_MESSAGE
from courses.models import Student, Teacher, UserProfile

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class LoginFlowTests(TestCase):
    password = DEFAULT_PASSWORDS[ROLE_TEACHER]
    student_password = DEFAULT_PASSWORDS[ROLE_STUDENT]

    @classmethod
    def setUpTestData(cls):
        cls.teacher = Teacher.objects.create(
            nickname='老王学堂',
            introduction='测试讲师',
            fans=100,
        )
        cls.teacher_profile, _ = ensure_account(ROLE_TEACHER, cls.teacher)

        cls.student = Student.objects.create(
            sno='2024001',
            name='张小明',
            gender=1,
            age=19,
            email='zhangxiaoming@example.com',
            phone='13800138001',
            enroll_at=dt.date(2024, 9, 1),
        )
        cls.student_profile, _ = ensure_account(ROLE_STUDENT, cls.student)

    # ---------------------------------------------------------------- 辅助
    def login_teacher(self):
        return self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': self.password,
        })

    def login_student(self):
        return self.client.post(reverse('courses:login'), {
            'role': ROLE_STUDENT,
            'username': self.student.sno,
            'password': self.student_password,
        })

    # ---------------------------------------------------------------- 页面
    def test_login_page_shows_both_roles(self):
        response = self.client.get(reverse('courses:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '教师登录')
        self.assertContains(response, '学生登录')
        self.assertContains(response, '登录课程信息管理')

    def test_teacher_can_login_with_nickname(self):
        response = self.login_teacher()
        self.assertRedirects(response, reverse('courses:list'))

        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '老王学堂')
        self.assertContains(response, '教师')

    def test_student_can_login_with_sno(self):
        response = self.login_student()
        self.assertRedirects(response, reverse('courses:list'))

        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '张小明')
        self.assertContains(response, '只读')

    def test_wrong_password_is_rejected(self):
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': 'wrong-password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, INVALID_LOGIN_MESSAGE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_role_is_rejected(self):
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.student.sno,
            'password': self.student_password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, INVALID_LOGIN_MESSAGE)

    def test_unknown_username_gets_generic_error(self):
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': '不存在的老师',
            'password': 'whatever',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, INVALID_LOGIN_MESSAGE)

    # ---------------------------------------------------------------- 跳转
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('courses:login')))
        self.assertIn('next=', response.url)

    def test_login_honours_safe_next(self):
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': self.password,
            'next': reverse('courses:teacher_add'),
        })
        self.assertRedirects(response, reverse('courses:teacher_add'))

    def test_login_rejects_external_next(self):
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': self.password,
            'next': 'https://evil.example/steal',
        })
        self.assertRedirects(response, reverse('courses:list'))

    def test_login_discards_post_only_next(self):
        """会话过期后重新登录，不应该被 GET 跳到只接受 POST 的删除地址。"""
        response = self.client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': self.password,
            'next': reverse('courses:student_delete', args=[self.student.sno]),
        })
        self.assertRedirects(response, reverse('courses:list'))

    def test_login_post_without_csrf_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse('courses:login'), {
            'role': ROLE_TEACHER,
            'username': self.teacher.nickname,
            'password': self.password,
        })
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.login_teacher()
        response = self.client.get(reverse('courses:login'))
        self.assertRedirects(response, reverse('courses:list'))

    # ---------------------------------------------------------------- 权限
    def test_student_is_read_only(self):
        self.login_student()
        response = self.client.get(reverse('courses:list'))
        self.assertNotContains(response, reverse('courses:teacher_add'))
        self.assertNotContains(response, reverse('courses:student_add'))
        self.assertContains(response, '只读视图')

        response = self.client.get(reverse('courses:teacher_add'))
        self.assertRedirects(response, reverse('courses:list'))

    def test_student_cannot_post_management_action(self):
        self.login_student()
        response = self.client.post(reverse('courses:teacher_add'), {
            'nickname': '越权添加的讲师',
            'fans': '0',
        })
        self.assertRedirects(response, reverse('courses:list'))
        self.assertFalse(Teacher.objects.filter(pk='越权添加的讲师').exists())

    def test_teacher_can_open_management_forms(self):
        self.login_teacher()
        self.assertEqual(self.client.get(reverse('courses:teacher_add')).status_code, 200)
        self.assertEqual(self.client.get(reverse('courses:student_add')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('courses:student_update', args=[self.student.sno])).status_code,
            200,
        )

    def test_teacher_delete_requires_post(self):
        self.login_teacher()
        response = self.client.get(reverse('courses:teacher_delete', args=[self.teacher.nickname]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Teacher.objects.filter(pk=self.teacher.nickname).exists())

    def test_adding_teacher_creates_login_account(self):
        self.login_teacher()
        response = self.client.post(reverse('courses:teacher_add'), {
            'nickname': '新讲师',
            'introduction': '',
            'fans': '0',
        })
        self.assertRedirects(response, reverse('courses:list'))

        teacher = Teacher.objects.get(pk='新讲师')
        self.assertIsNotNone(getattr(teacher, 'login_profile', None))
        self.assertTrue(
            teacher.login_profile.user.check_password(DEFAULT_PASSWORDS[ROLE_TEACHER])
        )

    def test_adding_student_creates_login_account(self):
        self.login_teacher()
        response = self.client.post(reverse('courses:student_add'), {
            'sno': '2025999',
            'name': '新同学',
            'gender': '1',
            'age': '18',
            'email': '',
            'phone': '',
            'course': '',
            'enroll_at': '2025-09-01',
            'introduction': '',
        })
        self.assertRedirects(response, reverse('courses:list'))

        student = Student.objects.get(pk='2025999')
        self.assertIsNotNone(getattr(student, 'login_profile', None))
        self.assertTrue(
            student.login_profile.user.check_password(DEFAULT_PASSWORDS[ROLE_STUDENT])
        )

    def test_admin_delete_cleans_up_linked_account(self):
        request = RequestFactory().post('/admin/')
        request.user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin-password',
        )
        username = internal_username(ROLE_TEACHER, self.teacher)

        model_admin = TeacherAdmin(Teacher, AdminSite())
        model_admin.delete_model(request, self.teacher)

        self.assertFalse(Teacher.objects.filter(pk=self.teacher.nickname).exists())
        self.assertFalse(get_user_model().objects.filter(username=username).exists())

    def test_admin_adding_teacher_creates_login_account(self):
        request = RequestFactory().post('/admin/')
        request.user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin-password',
        )
        teacher = Teacher(nickname='后台讲师', fans=0)

        TeacherAdmin(Teacher, AdminSite()).save_model(
            request, teacher, form=None, change=False,
        )

        self.assertIsNotNone(getattr(teacher, 'login_profile', None))
        self.assertTrue(
            teacher.login_profile.user.check_password(DEFAULT_PASSWORDS[ROLE_TEACHER])
        )

    def test_student_can_be_deleted_by_teacher_and_account_is_cleaned_up(self):
        self.login_teacher()
        username = internal_username(ROLE_STUDENT, self.student)
        response = self.client.post(reverse('courses:student_delete', args=[self.student.sno]))
        self.assertRedirects(response, reverse('courses:list'))
        self.assertFalse(Student.objects.filter(pk=self.student.sno).exists())
        self.assertFalse(get_user_model().objects.filter(username=username).exists())

    def test_teacher_deleting_self_logs_out(self):
        self.login_teacher()
        username = internal_username(ROLE_TEACHER, self.teacher)
        response = self.client.post(reverse('courses:teacher_delete', args=[self.teacher.nickname]))
        self.assertRedirects(response, reverse('courses:login'))
        self.assertFalse(Teacher.objects.filter(pk=self.teacher.nickname).exists())
        self.assertFalse(get_user_model().objects.filter(username=username).exists())

        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 302)

    # ---------------------------------------------------------------- 退出
    def test_logout_requires_post_and_clears_session(self):
        self.login_teacher()
        response = self.client.get(reverse('courses:logout'))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse('courses:logout'))
        self.assertRedirects(response, reverse('courses:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 302)

    # ---------------------------------------------------------------- 账号
    def test_passwords_are_hashed(self):
        user = self.teacher_profile.user
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AccountProvisioningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Teacher.objects.create(nickname='晴天老师', fans=10)
        cls.student = Student.objects.create(
            sno='2025001',
            name='郑凯',
            gender=1,
            age=18,
            enroll_at=dt.date(2025, 9, 1),
        )

    def test_sync_accounts_creates_accounts_and_is_idempotent(self):
        stats = sync_accounts()
        self.assertEqual(stats[ROLE_TEACHER]['created'], 1)
        self.assertEqual(stats[ROLE_STUDENT]['created'], 1)
        self.assertEqual(UserProfile.objects.count(), 2)

        stats = sync_accounts()
        self.assertEqual(stats[ROLE_TEACHER]['created'], 0)
        self.assertEqual(stats[ROLE_STUDENT]['created'], 0)
        self.assertEqual(UserProfile.objects.count(), 2)

        teacher_user = self.teacher.login_profile.user
        student_user = self.student.login_profile.user
        self.assertTrue(teacher_user.check_password(DEFAULT_PASSWORDS[ROLE_TEACHER]))
        self.assertTrue(student_user.check_password(DEFAULT_PASSWORDS[ROLE_STUDENT]))

    def test_sync_accounts_can_reset_passwords(self):
        sync_accounts()
        user = self.teacher.login_profile.user
        user.set_password('a-new-password')
        user.save(update_fields=['password'])

        sync_accounts(reset_password=True)
        user.refresh_from_db()
        self.assertTrue(user.check_password(DEFAULT_PASSWORDS[ROLE_TEACHER]))
        self.assertFalse(user.check_password('a-new-password'))
