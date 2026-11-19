from django.urls import path

from . import supervision, views

app_name = 'courses'

urlpatterns = [
    # 登录 / 退出
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 主页 —— 显示功能（任务三）
    path('', views.course_list, name='list'),

    # 讲师：添加 / 修改 / 删除（任务四、五、六）
    path('teacher/add/', views.teacher_add, name='teacher_add'),
    path('teacher/update/<str:nickname>/', views.teacher_update, name='teacher_update'),
    path('teacher/delete/<str:nickname>/', views.teacher_delete, name='teacher_delete'),

    # 学生：添加 / 修改 / 删除
    path('student/add/', views.student_add, name='student_add'),
    path('student/update/<str:sno>/', views.student_update, name='student_update'),
    path('student/delete/<str:sno>/', views.student_delete, name='student_delete'),

    # 学习督导
    path('supervision/', supervision.teacher_tasks, name='teacher_tasks'),
    path('supervision/tasks/new/', supervision.task_create, name='task_create'),
    path('supervision/tasks/<int:task_id>/', supervision.task_progress, name='task_progress'),
    path('supervision/submissions/<int:submission_id>/', supervision.submission_review, name='submission_review'),
    path('supervision/submissions/<int:submission_id>/draft/', supervision.feedback_draft, name='feedback_draft'),
    path('learning/', supervision.student_tasks, name='student_tasks'),
    path('learning/tasks/<int:task_id>/', supervision.student_task, name='student_task'),
    path('learning/tasks/<int:task_id>/ocr/', supervision.task_ocr, name='task_ocr'),
    path('learning/tasks/<int:task_id>/recommend/', supervision.task_recommend, name='task_recommend'),
]
