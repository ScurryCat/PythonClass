from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .accounts import ROLE_STUDENT, ROLE_TEACHER, get_user_profile
from .models import Course, Student, StudyTask, Submission
from .supervision_forms import DraftForm, RecommendationForm, ReviewForm, SubmissionForm, TaskForm


def _profile(request, role):
    profile = get_user_profile(request.user)
    if profile is None or profile.role != role:
        raise PermissionDenied
    return profile


def _course_task(student, task_id):
    return get_object_or_404(
        StudyTask.objects.select_related('course'), pk=task_id, course_id=student.course_id,
    )


def _task_state(task, submission, now):
    if submission is not None:
        return {
            'status': submission.status,
            'status_label': submission.get_status_display(),
            'late': submission.submitted_at > task.due_at,
        }
    overdue = now > task.due_at
    return {
        'status': 'overdue' if overdue else 'awaiting',
        'status_label': '逾期未交' if overdue else '待提交',
        'late': False,
    }


@login_required
@require_safe
def teacher_tasks(request):
    teacher = _profile(request, ROLE_TEACHER)
    tasks = StudyTask.objects.filter(course__teacher_id=teacher.teacher_id).select_related('course')
    return render(request, 'supervision/teacher_tasks.html', {
        'tasks': tasks,
        'has_courses': Course.objects.filter(teacher_id=teacher.teacher_id).exists(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def task_create(request):
    teacher = _profile(request, ROLE_TEACHER)
    courses = Course.objects.filter(teacher_id=teacher.teacher_id).order_by('title')
    form = TaskForm(request.POST if request.method == 'POST' else None, courses=courses)
    if request.method == 'POST' and form.is_valid():
        task = form.save()
        messages.success(request, '学习任务已发布。')
        return redirect('courses:task_progress', task_id=task.pk)
    return render(request, 'supervision/task_create.html', {
        'form': form,
        'has_courses': courses.exists(),
    })


@login_required
@require_safe
def task_progress(request, task_id):
    teacher = _profile(request, ROLE_TEACHER)
    task = get_object_or_404(
        StudyTask.objects.select_related('course'), pk=task_id, course__teacher_id=teacher.teacher_id,
    )
    submissions = {submission.student_id: submission for submission in task.submissions.all()}
    now = timezone.now()
    rows = []
    counts = {'pending': 0, 'reviewed': 0, 'overdue': 0, 'total': 0}
    for student in Student.objects.filter(course_id=task.course_id).order_by('sno'):
        submission = submissions.get(student.pk)
        state = _task_state(task, submission, now)
        rows.append({'student': student, 'submission': submission, **state})
        status = state['status']
        if status in counts:
            counts[status] += 1
    counts['total'] = len(rows)
    return render(request, 'supervision/task_progress.html', {
        'task': task,
        'rows': rows,
        'counts': counts,
    })


@login_required
@require_safe
def student_tasks(request):
    student = _profile(request, ROLE_STUDENT).student
    tasks = StudyTask.objects.filter(course_id=student.course_id).select_related('course')
    submissions = {
        submission.task_id: submission
        for submission in student.study_submissions.filter(task__course_id=student.course_id)
    }
    now = timezone.now()
    rows = []
    for task in tasks:
        submission = submissions.get(task.pk)
        rows.append({'task': task, 'submission': submission, **_task_state(task, submission, now)})
    return render(request, 'supervision/student_tasks.html', {'rows': rows, 'student': student})


@login_required
@require_http_methods(['GET', 'POST'])
def student_task(request, task_id):
    student = _profile(request, ROLE_STUDENT).student
    task = _course_task(student, task_id)
    if request.method == 'POST':
        with transaction.atomic():
            # 同一学生的首次请求也要串行，提交记录此时可能还不存在。
            get_object_or_404(
                Student.objects.select_for_update(), pk=student.pk, course_id=task.course_id,
            )
            submission = Submission.objects.select_for_update().filter(task=task, student=student).first()
            if submission is not None and submission.status != Submission.Status.RETURNED:
                messages.info(request, '这项任务已提交，请查看当前状态。')
                return redirect('courses:student_task', task_id=task.pk)

            form = SubmissionForm(request.POST, instance=submission)
            if form.is_valid():
                updated = form.save(commit=False)
                updated.task = task
                updated.student = student
                updated.submitted_at = timezone.now()
                updated.status = Submission.Status.PENDING
                updated.save()
                messages.success(request, '作业已提交。')
                return redirect('courses:student_task', task_id=task.pk)
    else:
        submission = Submission.objects.filter(task=task, student=student).first()
        form = SubmissionForm(instance=submission)

    return render(request, 'supervision/student_task.html', {
        'task': task,
        'submission': submission,
        'form': form,
        'can_submit': submission is None or submission.status == Submission.Status.RETURNED,
        **_task_state(task, submission, timezone.now()),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def submission_review(request, submission_id):
    teacher = _profile(request, ROLE_TEACHER)
    submissions = Submission.objects.filter(task__course__teacher_id=teacher.teacher_id)
    if request.method == 'POST':
        with transaction.atomic():
            submission = get_object_or_404(submissions.select_for_update(), pk=submission_id)
            if submission.status != Submission.Status.PENDING:
                messages.info(request, '这份作业已处理，请查看当前反馈。')
                return redirect('courses:submission_review', submission_id=submission.pk)

            form = ReviewForm(request.POST, submission=submission)
            if form.is_valid():
                submission.status = (
                    Submission.Status.RETURNED if form.cleaned_data['action'] == 'return'
                    else Submission.Status.REVIEWED
                )
                submission.feedback = form.cleaned_data['feedback']
                submission.reviewed_at = timezone.now()
                submission.save(update_fields=['status', 'feedback', 'reviewed_at'])
                messages.success(request, '批阅结果已发布。')
                return redirect('courses:task_progress', task_id=submission.task_id)
    else:
        submission = get_object_or_404(
            submissions.select_related('task__course', 'student'), pk=submission_id,
        )
        form = ReviewForm(submission=submission)

    return render(request, 'supervision/submission_review.html', {
        'submission': submission,
        'task': submission.task,
        'form': form,
        'can_review': submission.status == Submission.Status.PENDING,
    })


@login_required
@require_POST
def task_ocr(request, task_id):
    from .study_ai import StudyAIError, recognize_image

    student = _profile(request, ROLE_STUDENT).student
    _course_task(student, task_id)
    upload = request.FILES.get('image')
    if upload is None:
        return JsonResponse({'error': '请选择一张 PNG 或 JPEG 截图。'}, status=400)
    try:
        text = recognize_image(upload)
    except StudyAIError as error:
        return JsonResponse({'error': str(error)}, status=error.status_code)
    return JsonResponse({'text': text})


@login_required
@require_POST
def task_recommend(request, task_id):
    from .study_ai import StudyAIError, recommend_resources

    student = _profile(request, ROLE_STUDENT).student
    task = _course_task(student, task_id)
    form = RecommendationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': '截图文字和疑难点各限 2000 字。'}, status=400)
    try:
        results = recommend_resources(task, **form.cleaned_data)
    except StudyAIError as error:
        return JsonResponse({'error': str(error)}, status=error.status_code)
    return JsonResponse(results)


@login_required
@require_POST
def feedback_draft(request, submission_id):
    from .study_ai import StudyAIError, draft_feedback

    teacher = _profile(request, ROLE_TEACHER)
    submission = get_object_or_404(
        Submission.objects.select_related('task'),
        pk=submission_id,
        task__course__teacher_id=teacher.teacher_id,
    )
    if submission.status != Submission.Status.PENDING:
        return JsonResponse({'error': '这份作业已处理，请刷新查看当前状态。'}, status=409)
    form = DraftForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': '请填写批阅要点，最多 2000 字。'}, status=400)
    try:
        draft = draft_feedback(submission.task, form.cleaned_data['review_points'])
    except StudyAIError as error:
        return JsonResponse({'error': str(error)}, status=error.status_code)
    return JsonResponse({'draft': draft})
