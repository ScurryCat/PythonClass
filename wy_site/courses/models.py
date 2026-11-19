from django.conf import settings
from django.core.validators import URLValidator
from django.db import models
from django.utils import timezone


# 讲师信息表
class Teacher(models.Model):
    nickname = models.CharField(max_length=30, primary_key=True, db_index=True, verbose_name='昵称')
    introduction = models.TextField(default='这个老师很懒，木有签名的说~', verbose_name='简介')
    fans = models.PositiveIntegerField(default=0, verbose_name='粉丝数')
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'teacher'
        verbose_name = '讲师信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.nickname


# 课程信息表
class Course(models.Model):
    title = models.CharField(max_length=100, primary_key=True, db_index=True, verbose_name='课程名')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='讲师')
    type = models.SmallIntegerField(
        choices=((1, '后端开发'), (2, '数据挖掘'), (0, '其他')),
        default=0,
        verbose_name='课程类型'
    )
    price = models.PositiveSmallIntegerField(verbose_name='价格')
    volume = models.BigIntegerField(verbose_name='容量')
    online = models.DateField(verbose_name='上线时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'courses'
        verbose_name = '课程信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


# 学生信息表
class Student(models.Model):
    GENDER_CHOICES = (
        (1, '男'),
        (0, '女'),
    )

    sno = models.CharField(max_length=20, primary_key=True, db_index=True, verbose_name='学号')
    name = models.CharField(max_length=30, verbose_name='姓名')
    gender = models.SmallIntegerField(choices=GENDER_CHOICES, default=1, verbose_name='性别')
    age = models.PositiveSmallIntegerField(default=18, verbose_name='年龄')
    email = models.EmailField(blank=True, default='', verbose_name='邮箱')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='联系电话')
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='所报课程'
    )
    enroll_at = models.DateField(verbose_name='入学时间')
    introduction = models.TextField(default='这个同学很懒，木有签名的说~', verbose_name='个人简介')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'student'
        verbose_name = '学生信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# 登录账号与业务身份的绑定表
class UserProfile(models.Model):
    """把 Django 登录账号关联到讲师或学生。

    登录凭证仍然使用 Django 自带的 auth.User 保存，密码由 Django 加盐哈希；
    这张表只负责记录「这个账号是谁、属于哪一类身份」：
      · role=teacher → teacher 字段有值、student 为空
      · role=student → student 字段有值、teacher 为空
    """

    ROLE_TEACHER = 'teacher'
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = (
        (ROLE_TEACHER, '教师'),
        (ROLE_STUDENT, '学生'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_profile',
        verbose_name='登录账号',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name='身份')
    teacher = models.OneToOneField(
        Teacher,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_profile',
        verbose_name='教师',
    )
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_profile',
        verbose_name='学生',
    )

    class Meta:
        db_table = 'user_profile'
        verbose_name = '登录账号'
        verbose_name_plural = verbose_name
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(role='teacher', teacher__isnull=False, student__isnull=True)
                    | models.Q(role='student', teacher__isnull=True, student__isnull=False)
                ),
                name='userprofile_role_target_consistent',
            ),
        ]

    def __str__(self):
        return '%s · %s' % (self.get_role_display(), self.display_name)

    @property
    def display_name(self):
        """界面上显示的名字：教师用昵称，学生用姓名。"""
        if self.role == self.ROLE_TEACHER and self.teacher_id:
            return self.teacher.nickname
        if self.role == self.ROLE_STUDENT and self.student_id:
            return self.student.name
        return self.user.get_full_name() or self.user.username

    @property
    def login_name(self):
        """用户登录时输入的用户名：教师是昵称，学生是学号。"""
        if self.role == self.ROLE_TEACHER and self.teacher_id:
            return self.teacher.nickname
        if self.role == self.ROLE_STUDENT and self.student_id:
            return self.student.sno
        return self.user.username


class StudyTask(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='study_tasks', verbose_name='课程',
    )
    title = models.CharField(max_length=150, verbose_name='任务标题')
    instructions = models.TextField(max_length=4000, verbose_name='任务要求')
    due_at = models.DateTimeField(verbose_name='截止时间')

    class Meta:
        ordering = ['due_at', 'pk']
        verbose_name = '学习任务'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '待批阅'
        RETURNED = 'returned', '退回重交'
        REVIEWED = 'reviewed', '已批阅'

    task = models.ForeignKey(
        StudyTask, on_delete=models.CASCADE, related_name='submissions', verbose_name='任务',
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='study_submissions', verbose_name='学生',
    )
    content = models.TextField(max_length=5000, verbose_name='作业内容')
    recognized_text = models.TextField(blank=True, max_length=2000, verbose_name='确认后的截图文字')
    difficulties = models.TextField(blank=True, max_length=2000, verbose_name='疑难点')
    submitted_at = models.DateTimeField(default=timezone.now, verbose_name='提交时间')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name='批阅状态',
    )
    feedback = models.TextField(blank=True, max_length=3000, verbose_name='教师反馈')
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name='反馈时间')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task', 'student'], name='one_submission_per_task_student'),
        ]
        verbose_name = '作业提交'
        verbose_name_plural = verbose_name


class LearningResource(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='learning_resources', verbose_name='课程',
    )
    title = models.CharField(max_length=150, verbose_name='资料标题')
    description = models.TextField(max_length=2000, verbose_name='简介')
    tags = models.CharField(
        blank=True, max_length=255, verbose_name='标签', help_text='用逗号分隔知识点',
    )
    url = models.URLField(validators=[URLValidator(schemes=['http', 'https'])], verbose_name='链接')

    class Meta:
        verbose_name = '课程资料'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title
