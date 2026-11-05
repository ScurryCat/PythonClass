from django.contrib import messages
from django.db.models import Avg, Sum
from django.shortcuts import render, redirect, get_object_or_404

from .models import Teacher, Course, Student


# ==================== 显示功能（任务三） ====================
def course_list(request):
    """主页：把讲师、课程、学生三张表的数据全部展示出来

    除了三张表本身，这里还顺手算出概览区要用的几个统计量，
    省得在模板里做聚合。
    """
    teachers = Teacher.objects.all()
    courses = Course.objects.all()
    students = Student.objects.all()

    teacher_count = teachers.count()
    course_count = courses.count()
    student_count = students.count()

    # 课程类型分布（保持模型里 choices 的顺序：后端开发 / 数据挖掘 / 其他）
    type_colors = {1: 'var(--brand)', 2: 'var(--brand-2)', 0: '#94a3b8'}
    type_dist = []
    for value, label in Course._meta.get_field('type').choices:
        count = courses.filter(type=value).count()
        type_dist.append({
            'type': value,
            'label': label,
            'count': count,
            'percent': round(count * 100 / course_count, 2) if course_count else 0,
            'color': type_colors.get(value, '#94a3b8'),
        })

    # 粉丝榜前 5，按最高粉丝数换算成百分比宽度
    top_teachers = list(teachers.order_by('-fans')[:5])
    max_fans = max((t.fans for t in top_teachers), default=0)
    teacher_rank = [
        {
            'nickname': t.nickname,
            'fans': t.fans,
            'percent': round(t.fans * 100 / max_fans) if max_fans else 0,
        }
        for t in top_teachers
    ]

    enrolled = students.filter(course__isnull=False).count()
    fans_total = teachers.aggregate(total=Sum('fans'))['total'] or 0
    price_avg = courses.aggregate(avg=Avg('price'))['avg'] or 0

    return render(request, 'course.html', {
        'teachers': teachers,
        'courses': courses,
        'students': students,
        # ---- 概览区
        'teacher_count': teacher_count,
        'course_count': course_count,
        'student_count': student_count,
        'fans_total': fans_total,
        'price_avg': round(price_avg),
        'enrolled': enrolled,
        'unassigned': student_count - enrolled,
        'type_dist': type_dist,
        'teacher_rank': teacher_rank,
    })


# ==================== 添加功能（任务四） ====================
def teacher_add(request):
    """添加讲师"""
    if request.method == 'POST':
        Teacher.objects.create(
            nickname=request.POST.get('nickname'),
            introduction=request.POST.get('introduction') or '这个老师很懒，木有签名的说~',
            fans=request.POST.get('fans') or 0,
        )
        messages.success(request, '讲师「%s」添加成功！' % request.POST.get('nickname'))
        return redirect('courses:list')
    return render(request, 'teacher_add.html')


def student_add(request):
    """添加学生"""
    if request.method == 'POST':
        course_id = request.POST.get('course') or None
        # 前端传的是课程名（它就是 Course 的主键），这里换成 Course 对象
        course = Course.objects.filter(pk=course_id).first() if course_id else None
        Student.objects.create(
            sno=request.POST.get('sno'),
            name=request.POST.get('name'),
            gender=request.POST.get('gender') or 1,
            age=request.POST.get('age') or 18,
            email=request.POST.get('email') or '',
            phone=request.POST.get('phone') or '',
            course=course,
            enroll_at=request.POST.get('enroll_at'),
            introduction=request.POST.get('introduction') or '这个同学很懒，木有签名的说~',
        )
        messages.success(request, '学生「%s」添加成功！' % request.POST.get('name'))
        return redirect('courses:list')
    return render(request, 'student_add.html', {
        'courses': Course.objects.all(),
    })


# ==================== 修改功能（任务五） ====================
def teacher_update(request, nickname):
    """修改讲师：以昵称（主键）为关键字定位

    ★★ 文档里说的那个「坑」就在这里 ★★
    文档原文：「结果 修改成功，以姓名为修改标准，所以姓名不能修改」

    为什么姓名不能改？
      昵称是 teacher 表的主键，而 courses.teacher_id 是指向它的外键。
      数据库里这个外键的 UPDATE_RULE 是 NO ACTION，也就是说：
      只要还有课程挂在这个昵称上，就不允许修改它的主键值。
      所以表单里把昵称设为只读，视图也只更新简介和粉丝数，
      昵称原样保留 —— 这样数据永远是干净的。

    如果你偏要改昵称，必须按这个顺序做，少一步都会报错：
      ① 先把该讲师名下的课程 teacher_id 全部改成新昵称
      ② 再改 teacher 表的主键
      ③ 如果新昵称已经被别人占用，还要先处理冲突
    这就是文档说「修改过程中也会有报错，觉得会是什么原因？」的答案。
    """
    teacher = get_object_or_404(Teacher, nickname=nickname)
    if request.method == 'POST':
        # 昵称是主键，不修改：正常提交时原样带回来；被人手工篡改也只警告、不落库
        if request.POST.get('nickname', nickname) != nickname:
            messages.warning(request, '昵称是主键，不能修改，其它字段已更新。')

        teacher.introduction = request.POST.get('introduction') or ''
        teacher.fans = request.POST.get('fans') or 0
        teacher.save()

        messages.success(request, '讲师「%s」修改成功！' % teacher.nickname)
        return redirect('courses:list')
    return render(request, 'teacher_update.html', {'teacher': teacher})


def student_update(request, sno):
    """修改学生：以学号（主键）为关键字定位"""
    student = get_object_or_404(Student, sno=sno)
    if request.method == 'POST':
        course_id = request.POST.get('course') or None
        student.name = request.POST.get('name')
        student.gender = request.POST.get('gender') or 1
        student.age = request.POST.get('age') or 18
        student.email = request.POST.get('email') or ''
        student.phone = request.POST.get('phone') or ''
        student.course = Course.objects.filter(pk=course_id).first() if course_id else None
        student.enroll_at = request.POST.get('enroll_at')
        student.introduction = request.POST.get('introduction') or ''
        student.save()
        messages.success(request, '学生修改成功！')
        return redirect('courses:list')
    return render(request, 'student_update.html', {
        'student': student,
        'courses': Course.objects.all(),
    })


# ==================== 删除功能（任务六） ====================
def teacher_delete(request, nickname):
    """删除讲师（前端用 POST 表单提交）"""
    teacher = get_object_or_404(Teacher, nickname=nickname)
    teacher.delete()
    messages.success(request, '讲师删除成功！')
    return redirect('courses:list')


def student_delete(request, sno):
    """删除学生（前端用 POST 表单提交）"""
    student = get_object_or_404(Student, sno=sno)
    student.delete()
    messages.success(request, '学生删除成功！')
    return redirect('courses:list')
