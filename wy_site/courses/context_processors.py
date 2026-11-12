"""模板上下文处理器。

侧边栏计数和当前登录身份在每个页面都要用，集中在这里注入，
避免每个视图重复传参。
"""

from .accounts import get_user_profile, user_can_manage
from .models import Course, Student, Teacher


def sidebar_counts(request):
    return {
        'nav_teacher_count': Teacher.objects.count(),
        'nav_course_count': Course.objects.count(),
        'nav_student_count': Student.objects.count(),
    }


def account_context(request):
    """给模板提供当前账号的名称、身份和可写权限。"""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {
            'current_profile': None,
            'current_role': '',
            'current_role_label': '',
            'current_display_name': '',
            'current_login_name': '',
            'can_manage': False,
        }

    profile = get_user_profile(user)
    if profile is not None:
        return {
            'current_profile': profile,
            'current_role': profile.role,
            'current_role_label': profile.get_role_display(),
            'current_display_name': profile.display_name,
            'current_login_name': profile.login_name,
            'can_manage': user_can_manage(user),
        }

    # 从 Django admin 登录的后台管理员，没有绑定教师/学生身份
    if user.is_staff or user.is_superuser:
        return {
            'current_profile': None,
            'current_role': 'admin',
            'current_role_label': '管理员',
            'current_display_name': user.get_full_name() or user.username,
            'current_login_name': user.username,
            'can_manage': True,
        }

    return {
        'current_profile': None,
        'current_role': '',
        'current_role_label': '未绑定身份',
        'current_display_name': user.get_full_name() or user.username,
        'current_login_name': user.username,
        'can_manage': False,
    }
