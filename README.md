# wy_site · Django 课程信息管理网站

一个用 Django 写的课程信息管理小网站，作为「Python + Django 网站制作」课程作业。

网站把**讲师**、**课程**、**学生**三类信息集中展示在一页上，并且每一类都支持**添加、修改、删除**，
后台还接了 Django 自带的管理系统，可以可视化维护数据。

---

## 目录

- [功能一览](#功能一览)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [URL 路由](#url-路由)
- [开发中踩到的两个坑](#开发中踩到的两个坑)
- [已知问题与可改进点](#已知问题与可改进点)

---

## 功能一览

| 模块 | 显示 | 添加 | 修改 | 删除 | 后台管理 |
|---|:---:|:---:|:---:|:---:|:---:|
| 讲师 Teacher | ✅ | ✅ | ✅ | ✅ | ✅ |
| 课程 Course | ✅ | — | — | — | ✅ |
| 学生 Student | ✅ | ✅ | ✅ | ✅ | ✅ |

其他细节：

- 主页一屏展示三张表，用 Bootstrap 表格 + 自定义样式
- 下拉框里直接选课程，学生与课程自动建立关联
- 增删改完成后回到主页，并在顶部显示一条中文提示（Django messages 框架）
- 删除按钮带二次确认，防止误点
- 后台显示中文模型名：**讲师信息 / 课程信息 / 学生信息**
- 表单页与主页共用同一套 `course.css`，风格统一

---

## 技术栈

| 项 | 版本 / 说明 |
|---|---|
| Python | 3.11 |
| Django | 5.2.18 |
| 数据库 | MySQL 8.0（字符集 `utf8mb4`） |
| 数据库驱动 | mysqlclient 2.3.0 |
| 前端 | Bootstrap 3.4.1（CDN）+ 自定义 CSS |

完整依赖见 [`requirements.txt`](requirements.txt)。

---

## 快速开始

### 1. 准备环境

需要先装好 **Python 3.8+** 和 **MySQL 8.0**。

```bash
pip install -r requirements.txt
```

### 2. 创建数据库

Django 的 `migrate` **只会建表、不会建库**，所以要先手动把库建出来：

```bash
mysql -u root -p -e "CREATE DATABASE course CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

> ⚠️ 字符集必须是 `utf8mb4`。用默认的 `latin1` 存中文讲师名会变成 `???`，
> 或者直接报 `Incorrect string value`。

### 3. 修改数据库密码

打开 `wy_site/wy_site/settings.py`，把 `DATABASES` 里的密码改成你自己的：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'course',
        'USER': 'root',
        'PASSWORD': '111111',      # ← 改成你的 MySQL 密码
        'HOST': '127.0.0.1',
        'PORT': 3306,
    }
}
```

### 4. 建表并创建管理员

```bash
cd wy_site
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动

```bash
python manage.py runserver
```

| 地址 | 说明 |
|---|---|
| http://127.0.0.1:8000/ | 网站首页 |
| http://127.0.0.1:8000/admin/ | 后台管理（用刚创建的超级用户登录） |

想先塞点演示数据的话，在后台点进去手动加几条，或者用首页的「添加讲师 / 添加学生」按钮。

---

## 项目结构

```
.
├── .gitignore
├── requirements.txt
├── README.md
├── python - django -网站制作 步骤最终版.docx    ← 课程步骤文档
└── wy_site/                                    ← Django 项目根目录
    ├── manage.py
    ├── templates/                              ← 项目级模板
    │   ├── course.html                         ← 主页：三张表
    │   ├── teacher_add.html
    │   ├── teacher_update.html
    │   ├── student_add.html
    │   └── student_update.html
    ├── courses/                                ← 应用
    │   ├── models.py                           ← Teacher / Course / Student
    │   ├── views.py                            ← 7 个视图函数
    │   ├── urls.py                             ← 应用路由
    │   ├── admin.py                            ← 后台注册
    │   ├── migrations/
    │   │   ├── 0001_initial.py                 ← Teacher + Course
    │   │   └── 0002_student.py                 ← Student
    │   └── static/css/course.css               ← 页面样式
    └── wy_site/                                ← 项目配置
        ├── settings.py
        └── urls.py
```

---

## 数据模型

三个模型都指定了 `db_table`，并且都写了 `Meta.verbose_name`（所以后台显示中文）。

### Teacher · 讲师信息 → 表 `teacher`

| 字段 | 类型 | 说明 |
|---|---|---|
| `nickname` | CharField(30) | **主键**，昵称 |
| `introduction` | TextField | 简介，默认「这个老师很懒，木有签名的说~」 |
| `fans` | PositiveIntegerField | 粉丝数，默认 0 |
| `create_at` | DateTimeField | 创建时间，`auto_now_add` |
| `update_at` | DateTimeField | 更新时间，`auto_now` |

### Course · 课程信息 → 表 `courses`

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | CharField(100) | **主键**，课程名 |
| `teacher` | ForeignKey(Teacher) | 讲师，`on_delete=CASCADE` |
| `type` | SmallIntegerField | 课程类型：1 后端开发 / 2 数据挖掘 / 0 其他 |
| `price` | PositiveSmallIntegerField | 价格 |
| `volume` | BigIntegerField | 容量 |
| `online` | DateField | 上线时间 |
| `created_at` / `updated_at` | DateTimeField | 自动时间戳 |

### Student · 学生信息 → 表 `student`

| 字段 | 类型 | 说明 |
|---|---|---|
| `sno` | CharField(20) | **主键**，学号 |
| `name` | CharField(30) | 姓名 |
| `gender` | SmallIntegerField | 性别：1 男 / 0 女 |
| `age` | PositiveSmallIntegerField | 年龄，默认 18 |
| `email` | EmailField | 邮箱，可空 |
| `phone` | CharField(20) | 联系电话，可空 |
| `course` | ForeignKey(Course) | 所报课程，可空，`on_delete=SET_NULL` |
| `enroll_at` | DateField | 入学时间 |
| `introduction` | TextField | 个人简介 |
| `created_at` / `updated_at` | DateTimeField | 自动时间戳 |

> 模板里用 `{{ course.get_type_display }}`、`{{ student.get_gender_display }}`
> 把存进去的数字（`1`）自动显示成中文（「后端开发」「男」）。

---

## URL 路由

主路由 `wy_site/urls.py`：

| 路径 | 说明 |
|---|---|
| `admin/` | Django 后台 |
| `''` | 转发到应用路由 `courses.urls` |

应用路由 `courses/urls.py`（`app_name = 'courses'`）：

| 路径 | 视图 | 功能 |
|---|---|---|
| `` (空) | `course_list` | 主页，显示三张表 |
| `teacher/add/` | `teacher_add` | 添加讲师 |
| `teacher/update/<nickname>/` | `teacher_update` | 修改讲师 |
| `teacher/delete/<nickname>/` | `teacher_delete` | 删除讲师 |
| `student/add/` | `student_add` | 添加学生 |
| `student/update/<sno>/` | `student_update` | 修改学生 |
| `student/delete/<sno>/` | `student_delete` | 删除学生 |

模板里统一用 `{% url 'courses:xxx' %}` 反向解析，不写死路径。

---

## 开发中踩到的两个坑

这两个都是课程文档里特意留的「坑」，记录一下结论。

### 坑一：把「姓名」当主键，就改不了名

`Teacher.nickname` 和 `Course.title` 都是**主键**，而 `Course.teacher` 是指向讲师的**外键**。

一开始想支持「改讲师昵称」，试了三种写法全部失败：

| 尝试 | 结果 |
|---|---|
| `teacher.nickname = 新值; teacher.save()` | Django 发现主键变了，执行的是 **INSERT 而不是 UPDATE** —— 旧行原封不动留着，讲师**凭空多出一个** |
| 先 `delete()` 旧行再插入 | 触发 `on_delete=CASCADE`，**该讲师名下的课程被一起删光** |
| 先迁移外键再删旧行 | `IntegrityError (1452)`，因为新昵称在 `teacher` 表里还不存在，外键校验通不过 |

根因在数据库层：

```sql
courses_teacher_id_79a070ce_fk_teacher_nickname    UPDATE_RULE = NO ACTION
```

也就是说：**只要还有课程挂在这个昵称上，数据库就不允许修改它的主键值。**

所以最后的做法是遵循原设计 —— 正符合文档里那句「以姓名为修改标准，所以**姓名不能修改**」：
修改页把昵称设为 `readonly`，视图只更新简介和粉丝数。
另外加了一层防护：万一有人手工篡改表单里的昵称，程序只弹警告、**不落库**。

> 正规解法是加一个自增 `id` 当主键，把 `nickname` 降为 `unique` 普通字段。
> 但那要改表结构，会影响 `Course`、`Student` 的外键，所以这个作业里保留了原设计。

### 坑二：删除必须用 POST，不能用 GET

`<a href=".../delete/...">` 这种 GET 链接是删不掉的（会被 CSRF 中间件拦掉）。
正确写法是用按钮套一个 POST 表单：

```html
<form method="post" action="{% url 'courses:delete' t.nickname %}"
      onsubmit="return confirm('确定要删除吗？');">
    {% csrf_token %}
    <button type="submit" class="btn btn-danger">删除</button>
</form>
```

`{% csrf_token %}` 绝对不能漏，否则 POST 会返回 `403 Forbidden`。

---

## 已知问题与可改进点

**已知限制**

- **课程只能在后台增删改**，前台只做了展示（文档任务四~六要求的是讲师/学生的增删改）
- **一个学生只能报一门课**：`Student.course` 用的是 `ForeignKey`。
  如果想支持多选，要改成 `ManyToManyField`
- **删讲师会连带删掉他名下的所有课程**（`Course.teacher` 是 `CASCADE`），操作时注意
- 数据库密码目前**明文写在 `settings.py`** 里。本地练习没问题，
  但要放到公开仓库建议改成从环境变量读取：

  ```python
  import os
  'PASSWORD': os.environ.get('DB_PASSWORD', '111111'),
  ```

**可以继续做的方向**

- 给课程也补一套前台增删改
- 学生选课改成多对多，支持一门课多个学生
- 列表加搜索、筛选、分页
- 用 Django Form / ModelForm 代替手工取 `request.POST`，自动做字段校验
- 补单元测试（`courses/tests.py` 目前是空的）
