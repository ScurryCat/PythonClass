"""登录表单。"""

from django import forms
from django.contrib.auth import authenticate, get_user_model

from .accounts import find_login_profile
from .models import UserProfile

INVALID_LOGIN_MESSAGE = '用户名或密码不正确，请检查后重试。'


class LoginForm(forms.Form):
    """教师 / 学生共用的登录表单。

    用户名不是 auth.User.username，而是教师昵称或学生学号；
    clean() 里会先按身份找到对应的登录资料，再交给 Django 校验密码。
    """

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial=UserProfile.ROLE_TEACHER,
        error_messages={
            'required': '请选择登录身份。',
            'invalid_choice': '登录身份无效，请重新选择。',
        },
    )
    username = forms.CharField(
        max_length=150,
        strip=True,
        error_messages={'required': '请输入用户名。'},
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput,
        error_messages={'required': '请输入密码。'},
    )
    remember = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # clean() 成功后，视图直接从这里取认证结果
        self.user = None
        self.profile = None

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        login_name = cleaned.get('username')
        password = cleaned.get('password')

        if role and login_name and password:
            profile = find_login_profile(role, login_name)
            if profile is None:
                # 账号不存在时也跑一次同等成本的密码哈希，避免通过响应时间枚举账号。
                get_user_model()().set_password(password)
                raise forms.ValidationError(INVALID_LOGIN_MESSAGE, code='invalid_login')
            if not profile.user.is_active:
                raise forms.ValidationError(INVALID_LOGIN_MESSAGE, code='invalid_login')

            user = authenticate(
                username=profile.user.username,
                password=password,
            )
            # ModelBackend 已校验密码和 is_active；再确认一次拿到的是绑定账号。
            if user is None or user.pk != profile.user_id:
                raise forms.ValidationError(INVALID_LOGIN_MESSAGE, code='invalid_login')

            self.user = user
            self.profile = profile

        return cleaned
