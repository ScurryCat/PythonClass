"""模板上下文处理器：给侧边栏提供三张表的实时计数。

侧边栏在每个页面都要显示「讲师 6 / 课程 8 / 学生 12」这组数字，
所以放在上下文处理器里，不用每个视图都手动传一遍。
"""

from .models import Course, Student, Teacher


def sidebar_counts(request):
    return {
        'nav_teacher_count': Teacher.objects.count(),
        'nav_course_count': Course.objects.count(),
        'nav_student_count': Student.objects.count(),
    }
