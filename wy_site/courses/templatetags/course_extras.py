"""项目自用的小型模板过滤器。"""

from django import template

register = template.Library()


@register.filter
def thousands(value):
    """给整数加千分位：12800 → 12,800。

    Django 自带的 `intcomma`（humanize）在 zh-hans 语言下不会加千分位，
    所以这里直接用 Python 的格式化语法，和语言环境无关。
    """
    try:
        return '{:,}'.format(int(value))
    except (TypeError, ValueError):
        return value
