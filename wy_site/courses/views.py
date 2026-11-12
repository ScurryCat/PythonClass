from functools import wraps
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import Resolver404, resolve
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from .accounts import (
    DEFAULT_PASSWORDS,
    ROLE_STUDENT,
    ROLE_TEACHER,
    delete_linked_account,
    ensure_account,
    user_can_manage,
)
from .forms import LoginForm
from .models import Teacher, Course, Student, UserProfile
from .seed import STUDENTS, TEACHERS


# ==================== 登录 / 退出 ====================
# 这几个地址只接受 POST，登录成功后不能用 GET 跳过去（否则会 405）。
POST_ONLY_VIEW_NAMES = {
    'courses:logout',
    'courses:teacher_delete',
    'courses:student_delete',
}


def _safe_next_url(request, candidate):
    """校验登录后的跳转地址。

    只允许本站地址，防止 ?next=https://evil.example 这种开放重定向；
    同时跳过 logout / delete 这类只接受 POST 的地址，
    避免会话过期后重新登录却落到一个 GET 请求会 405 的页面。
    """
    if not candidate:
        return ''
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ''

    try:
        match = resolve(urlsplit(candidate).path)
    except Resolver404:
        return ''
    if match.view_name in POST_ONLY_VIEW_NAMES:
        return ''
    return candidate


def _role_from_request(request):
    role = request.GET.get('role')
    valid_roles = {value for value, _label in UserProfile.ROLE_CHOICES}
    return role if role in valid_roles else UserProfile.ROLE_TEACHER


def _demo_accounts(enabled):
    """登录页底部的演示账号提示（只在 DEBUG 且种子数据存在时展示）。"""
    if not enabled:
        return {'show_demo_accounts': False}

    demo_teacher_name = TEACHERS[0]['nickname'] if TEACHERS else None
    demo_student_sno = STUDENTS[0]['sno'] if STUDENTS else None
    if not demo_teacher_name or not demo_student_sno:
        return {'show_demo_accounts': False}

    demo_teacher = Teacher.objects.filter(pk=demo_teacher_name).first()
    demo_student = Student.objects.filter(pk=demo_student_sno).first()
    # 业务数据存在但还没跑 sync_accounts 时，不展示会误导人的演示密码
    if demo_teacher is None or getattr(demo_teacher, 'login_profile', None) is None:
        return {'show_demo_accounts': False}
    if demo_student is None or getattr(demo_student, 'login_profile', None) is None:
        return {'show_demo_accounts': False}

    return {
        'show_demo_accounts': True,
        'demo_teacher': demo_teacher_name,
        'demo_student': demo_student_sno,
        'demo_teacher_password': DEFAULT_PASSWORDS[ROLE_TEACHER],
        'demo_student_password': DEFAULT_PASSWORDS[ROLE_STUDENT],
    }


@sensitive_post_parameters('password')
@never_cache
def login_view(request):
    """教师 / 学生登录入口。

    前端提交 role + username + password：
      · 教师身份下 username 填讲师昵称
      · 学生身份下 username 填学号
    认证成功后使用 Django 的 login() 写入会话，不自己维护登录状态。
    """
    next_url = _safe_next_url(
        request,
        request.POST.get('next') or request.GET.get('next'),
    )

    if request.user.is_authenticated:
        return redirect(next_url or 'courses:list')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.user)
            # 勾选“记住我”用默认的 2 周有效期，不勾选则关闭浏览器即失效。
            if form.cleaned_data.get('remember'):
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)

            messages.success(
                request,
                '欢迎回来，%s（%s）！' % (
                    form.profile.display_name,
                    form.profile.get_role_display(),
                ),
            )
            return redirect(next_url or 'courses:list')
    else:
        form = LoginForm(initial={'role': _role_from_request(request)})

    context = {
        'form': form,
        'next': next_url,
    }
    context.update(_demo_accounts(settings.DEBUG))
    return render(request, 'login.html', context)


@login_required
@require_POST
def logout_view(request):
    """退出登录。只接受 POST，避免被第三方页面用一张图片就登出。"""
    auth_logout(request)
    messages.success(request, '已安全退出登录，期待下次再见。')
    return redirect('courses:login')


# ==================== 权限控制 ====================
def teacher_required(view_func):
    """要求教师（或 Django 后台管理员）身份；学生请求会被拦回首页。"""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if user_can_manage(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, '当前账号是学生身份，只能查看数据，不能执行该操作。')
        return redirect('courses:list')

    return _wrapped


# ==================== 显示功能（任务三） ====================
@login_required
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
@teacher_required
def teacher_add(request):
    """添加讲师，并同步创建对应的登录账号。"""
    if request.method == 'POST':
        with transaction.atomic():
            teacher = Teacher.objects.create(
                nickname=request.POST.get('nickname'),
                introduction=request.POST.get('introduction') or '这个老师很懒，木有签名的说~',
                fans=request.POST.get('fans') or 0,
            )
            _profile, account_created = ensure_account(ROLE_TEACHER, teacher)

        messages.success(request, '讲师「%s」添加成功！' % teacher.nickname)
        if account_created:
            messages.info(
                request,
                '登录账号已创建：用户名「%s」，初始密码「%s」，请管理员到 Django 后台修改初始密码。'
                % (teacher.nickname, DEFAULT_PASSWORDS[ROLE_TEACHER]),
            )
        return redirect('courses:list')
    return render(request, 'teacher_add.html')


@teacher_required
def student_add(request):
    """添加学生，并同步创建对应的登录账号。"""
    if request.method == 'POST':
        course_id = request.POST.get('course') or None
        # 前端传的是课程名（它就是 Course 的主键），这里换成 Course 对象
        course = Course.objects.filter(pk=course_id).first() if course_id else None
        with transaction.atomic():
            student = Student.objects.create(
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
            _profile, account_created = ensure_account(ROLE_STUDENT, student)

        messages.success(request, '学生「%s」添加成功！' % student.name)
        if account_created:
            messages.info(
                request,
                '登录账号已创建：用户名「%s」，初始密码「%s」，请管理员到 Django 后台修改初始密码。'
                % (student.sno, DEFAULT_PASSWORDS[ROLE_STUDENT]),
            )
        return redirect('courses:list')
    return render(request, 'student_add.html', {
        'courses': Course.objects.all(),
    })


# ==================== 修改功能（任务五） ====================
@teacher_required
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


@teacher_required
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
@teacher_required
@require_POST
def teacher_delete(request, nickname):
    """删除讲师（前端用 POST 表单提交）"""
    teacher = get_object_or_404(Teacher, nickname=nickname)
    current_user_id = request.user.pk
    with transaction.atomic():
        account_user_id = delete_linked_account(teacher)
        teacher.delete()

    # 如果老师把自己登录的账号删掉了，顺手退出登录，避免留下无身份会话
    if account_user_id == current_user_id:
        auth_logout(request)
        messages.info(request, '当前登录账号已随讲师资料删除，请重新登录。')
        return redirect('courses:login')

    messages.success(request, '讲师删除成功！')
    return redirect('courses:list')


@teacher_required
@require_POST
def student_delete(request, sno):
    """删除学生（前端用 POST 表单提交）"""
    student = get_object_or_404(Student, sno=sno)
    with transaction.atomic():
        delete_linked_account(student)
        student.delete()
    messages.success(request, '学生删除成功！')
    return redirect('courses:list')
