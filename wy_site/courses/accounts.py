"""登录账号相关的辅助函数。

网站没有另外建一张用户表：登录凭证放在 Django 自带的 auth.User 里，
密码由 Django 用 PBKDF2 加盐哈希；UserProfile 负责把账号绑定到
某位讲师或学生，并记录身份（teacher / student）。

用户实际输入的用户名：
    · 教师 —— 讲师昵称（teacher.nickname）
    · 学生 —— 学号（student.sno）

auth.User.username 则使用内部前缀，避免教师昵称和学生学号重名：
    · teacher__<昵称>
    · student__<学号>
这个内部用户名只在数据库里使用，不展示给登录用户。
"""

from django.contrib.auth import get_user_model

from .models import Student, Teacher, UserProfile

ROLE_TEACHER = UserProfile.ROLE_TEACHER
ROLE_STUDENT = UserProfile.ROLE_STUDENT

INTERNAL_USERNAME_PREFIX = {
    ROLE_TEACHER: 'teacher__',
    ROLE_STUDENT: 'student__',
}

# 演示环境的初始密码。正式使用时请重置密码（或直接到 Django 后台修改）。
DEFAULT_PASSWORDS = {
    ROLE_TEACHER: 'teacher123',
    ROLE_STUDENT: 'student123',
}

# 身份 → (业务模型, 用户实际输入的用户名字段)
TARGET_MODELS = {
    ROLE_TEACHER: (Teacher, 'nickname'),
    ROLE_STUDENT: (Student, 'sno'),
}

def target_display_name(role, target):
    """业务对象在界面上显示的名字。"""
    if role == ROLE_TEACHER:
        return target.nickname
    return target.name


def internal_username(role, target):
    """auth.User 里使用的内部用户名。"""
    return '%s%s' % (INTERNAL_USERNAME_PREFIX[role], target.pk)


def get_user_profile(user):
    """取当前登录用户的身份信息；匿名用户或没绑定身份时返回 None。"""
    if not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'course_profile', None)


def user_can_manage(user):
    """教师和 Django 后台管理员可以维护数据，学生只能查看。"""
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    profile = get_user_profile(user)
    return bool(profile and profile.role == ROLE_TEACHER)


def find_login_profile(role, login_name):
    """按「身份 + 用户输入的用户名」找到对应的登录资料。

    找不到时统一返回 None，由调用方给出模糊的错误提示，
    避免泄露「这个昵称/学号是否存在」。
    """
    model_field = TARGET_MODELS.get(role)
    if model_field is None or not login_name:
        return None

    model, field_name = model_field
    target = model.objects.filter(**{field_name: login_name}).first()
    if target is None:
        return None

    return getattr(target, 'login_profile', None)


def ensure_account(role, target, password=None, reset_password=False):
    """为讲师/学生补建登录账号，返回 (profile, created)。

    · 账号已存在时默认不动密码，避免每次跑 seed 都把密码重置；
    · reset_password=True 时才把密码重设为 password 或默认密码；
    · 新建账号时设置默认密码（也可以传 password 指定）。
    """
    if role not in TARGET_MODELS:
        raise ValueError('未知身份：%s' % role)

    profile = getattr(target, 'login_profile', None)
    if profile is not None:
        if reset_password:
            user = profile.user
            user.set_password(password or DEFAULT_PASSWORDS[role])
            user.save(update_fields=['password'])
        return profile, False

    User = get_user_model()
    username = internal_username(role, target)
    user = User.objects.filter(username=username).first()
    initial_password = password or DEFAULT_PASSWORDS[role]

    if user is not None:
        # 极端情况下，内部用户名可能已经和其他身份绑定，直接复用已有绑定。
        existing_profile = getattr(user, 'course_profile', None)
        if existing_profile is not None:
            return existing_profile, False

        # 复用一个没有身份绑定的历史账号时，重置密码，避免沿用未知旧密码。
        user.set_password(initial_password)
        user.save(update_fields=['password'])
    else:
        user = User.objects.create_user(username=username, password=initial_password)

    if not user.first_name:
        user.first_name = target_display_name(role, target)
        user.save(update_fields=['first_name'])

    profile = UserProfile.objects.create(
        user=user,
        role=role,
        teacher=target if role == ROLE_TEACHER else None,
        student=target if role == ROLE_STUDENT else None,
    )
    return profile, True


def sync_accounts(reset_password=False):
    """扫描所有讲师/学生，为没有账号的人补建账号。

    返回按身份统计的结果，便于 management command 打印：
        {'teacher': {'created': 0, 'existing': 6}, 'student': {...}}
    """
    stats = {}
    for role, (model, _field) in TARGET_MODELS.items():
        created = 0
        existing = 0
        for target in model.objects.all().order_by('pk'):
            _profile, is_new = ensure_account(
                role,
                target,
                reset_password=reset_password,
            )
            if is_new:
                created += 1
            else:
                existing += 1
        stats[role] = {'created': created, 'existing': existing}
    return stats


def delete_linked_account(target):
    """删除讲师/学生时，一并清理它关联的登录账号。

    返回被删除账号的 user_id（没有账号时返回 None），
    方便调用方判断是不是删掉了当前登录用户。
    """
    profile = getattr(target, 'login_profile', None)
    if profile is None:
        return None
    user_id = profile.user_id
    profile.user.delete()
    return user_id
