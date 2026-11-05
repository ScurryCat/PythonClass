"""
本地私有配置示例。

用法：
    copy local_settings.example.py local_settings.py

然后按自己机器的情况改 local_settings.py。
它会在 settings.py 的最末尾被导入，同名变量会覆盖 settings.py 里的值。

⚠️ local_settings.py 已经被 .gitignore 忽略，不会被提交；
   想改密码就把值填在 local_settings.py 里，**不要**填在 settings.py 里。
"""

# 生产环境请换成随机生成的密钥：
#   python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
SECRET_KEY = 'django-insecure-dev-only-please-change-me'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'course',
        'USER': 'root',
        'PASSWORD': '把你的 MySQL 密码填在这里',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
