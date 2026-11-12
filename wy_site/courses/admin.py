from django.contrib import admin

from .accounts import ROLE_STUDENT, ROLE_TEACHER, delete_linked_account, ensure_account
from .models import Course, Student, Teacher


class LinkedAccountAdminMixin:
    """后台新增 / 删除讲师、学生时，同步维护关联的登录账号。

    前台视图已经做了同样的处理；这里补上 Django admin 的入口，
    保证无论从哪个入口维护业务数据，登录账号都不会缺、也不会留孤儿。
    """

    account_role = None

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if self.account_role and getattr(obj, 'login_profile', None) is None:
            ensure_account(self.account_role, obj)

    def delete_model(self, request, obj):
        delete_linked_account(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            delete_linked_account(obj)
        super().delete_queryset(request, queryset)


@admin.register(Teacher)
class TeacherAdmin(LinkedAccountAdminMixin, admin.ModelAdmin):
    account_role = ROLE_TEACHER


@admin.register(Student)
class StudentAdmin(LinkedAccountAdminMixin, admin.ModelAdmin):
    account_role = ROLE_STUDENT


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass
