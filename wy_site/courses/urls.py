from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
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
]
