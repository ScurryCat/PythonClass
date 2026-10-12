from django.db import models


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
