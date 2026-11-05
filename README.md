# wy_site · Django 课程信息管理网站

一个用 Django 写的课程信息管理小网站，作为「Python + Django 网站制作」课程作业。

网站把**讲师**、**课程**、**学生**三类信息集中展示在一页上，并且每一类都支持**添加、修改、删除**，
后台还接了 Django 自带的管理系统，可以可视化维护数据。

---

## 目录

- [界面预览](#界面预览)
- [布局设计](#布局设计)
- [功能一览](#功能一览)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [演示数据](#演示数据)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [URL 路由](#url-路由)
- [开发中踩到的三个坑](#开发中踩到的三个坑)
- [已知问题与可改进点](#已知问题与可改进点)

---

## 界面预览

采用「左侧固定导航 + 右侧工作区」的后台式布局。下面是主页：

![主页](docs/preview/home-desktop.png)

顶部是概览区（统计卡 + 课程类型分布 + 讲师粉丝榜），下面接三张数据表：

![完整页面](docs/preview/home-fullpage.png)

窄屏（平板 768px / 手机 500px）：侧边栏自动收成顶部两行，统计卡折行，表格在卡片内横向滚动。

<img src="docs/preview/home-tablet.png" alt="平板" width="58%"> <img src="docs/preview/home-mobile.png" alt="手机" width="38%">

表单页：添加学生 / 修改讲师。

<img src="docs/preview/student-add.png" alt="添加学生" width="49%"> <img src="docs/preview/teacher-update.png" alt="修改讲师" width="49%">

---

## 布局设计

```
┌───────────────┬──────────────────────────────────────────────┐
│  侧边栏 248px  │  顶栏 .topbar（标题 + 副标题 + 操作按钮）        │
│               ├──────────────────────────────────────────────┤
│  数据概览      │  概览 .overview                              │
│  讲师信息  6   │    ├─ 统计卡 ×3（讲师 / 课程 / 学生）           │
│  课程信息  8   │    └─ 图表 ×2（类型分布 / 粉丝榜）              │
│  学生信息  12  │                                              │
│               │  数据区（三块 .card，各带搜索框）                │
│  添加讲师      │    ├─ #teachers  讲师表                       │
│  添加学生      │    ├─ #courses   课程表                       │
│               │    └─ #students  学生表                       │
│  后台管理      │  页脚                                        │
└───────────────┴──────────────────────────────────────────────┘
```

几个关键点：

- **侧边栏是粘性的**（`position: sticky; height: 100vh`），滚动时一直停在左边；
  点「讲师信息 / 课程信息 / 学生信息」会跳到对应区块（URL 带 `#teachers` 这类锚点），
  滚动时还会自动高亮当前所在区块（`course.js` 里的 `initScrollSpy`）。
- **侧边栏计数**由上下文处理器 [`courses/context_processors.py`](wy_site/courses/context_processors.py)
  统一注入，所以 5 个页面上的「6 / 8 / 12」永远和数据库一致，不用每个视图手动传。
- **统计卡用 `auto-fit` 自适应**：宽屏三列并排，窄屏自动折成两列 / 一列，不需要写一堆断点。
- **超宽屏**（>1700px）下内容限制在 1400px 以内，靠 `.topbar, .content` 上同一个
  `padding: max(28px, calc((100% - 1400px) / 2 + 28px))` 实现，顶栏和内容永远左对齐。
- **低于 900px** 侧边栏切换成「品牌 + 导航条」两行的顶部栏，导航条可横向滑动，
  顶栏同时取消吸顶，避免两层 sticky 打架。

---

## 功能一览

| 模块 | 显示 | 添加 | 修改 | 删除 | 后台管理 |
|---|:---:|:---:|:---:|:---:|:---:|
| 讲师 Teacher | ✅ | ✅ | ✅ | ✅ | ✅ |
| 课程 Course | ✅ | — | — | — | ✅ |
| 学生 Student | ✅ | ✅ | ✅ | ✅ | ✅ |

其他细节：

- **概览区**：三张统计卡（含粉丝合计、平均价格、选课比例）+ 课程类型分布条 + 讲师粉丝 Top 5
- 三张表各自一个区块，自带搜索框，输入即筛选（纯前端，不刷新页面）
- 表格横向溢出时，**操作列固定在右侧**并加渐隐遮罩，按钮永远不会被裁掉
- 姓名首字自动生成彩色头像，课程类型 / 性别 / 价格都有彩色徽章
- 下拉框里直接选课程，学生与课程自动建立关联
- 增删改完成后回到主页，顶部弹出一条中文提示（Django messages 框架），6 秒后自动淡出
- 删除按钮带二次确认，防止误点
- 后台显示中文模型名：**讲师信息 / 课程信息 / 学生信息**
- 所有 5 个页面共用 `base.html` + 同一套 `course.css`，风格统一
- **零外部依赖**：不再引 Bootstrap CDN，断网也能正常显示

---

## 技术栈

| 项 | 版本 / 说明 |
|---|---|
| Python | 3.11 |
| Django | 5.2.18 |
| 数据库 | MySQL 8.0（字符集 `utf8mb4`） |
| 数据库驱动 | mysqlclient 2.3.0 |
| 前端 | 原生 HTML / CSS / JS，无第三方库；`course.css` 是一套自包含的设计系统 |

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

### 3. 配置数据库连接

数据库密码**不在仓库里**。`settings.py` 会从环境变量读取，读不到就用默认值
（`root` / 空密码 / `127.0.0.1:3306` / 库名 `course`）。

推荐做法是把模板复制一份，填上自己的密码：

```bash
cd wy_site/wy_site
copy local_settings.example.py local_settings.py      # macOS/Linux 用 cp
```

然后编辑 `wy_site/wy_site/local_settings.py`：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'course',
        'USER': 'root',
        'PASSWORD': '你的 MySQL 密码',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

`local_settings.py` 已被 `.gitignore` 忽略，不会出现在提交里；
`settings.py` 最后一行会在存在时自动导入它。

> 也可以不建这个文件，改用环境变量：
> `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`，
> 以及 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS`。

### 4. 建表并创建管理员

```bash
cd wy_site
python manage.py migrate
python manage.py createsuperuser
```

### 5. 写入测试数据

```bash
python manage.py seed_data
```

一次写入 **6 位讲师、8 门课程、12 名学生**，并且按「讲师 → 课程 → 学生」的顺序建立好外键关系。

命令是幂等的：**可以重复执行**，已存在的记录（按主键判断）会跳过，不会写重复数据。

想清空重来（会二次确认）：

```bash
python manage.py seed_data --reset
```

不想跑 Django 命令也行，项目里还放了一份等价的原生 SQL：

```bash
mysql -u root -p --default-character-set=utf8mb4 course < sql/seed_demo_data.sql
```

### 6. 启动

```bash
python manage.py runserver
```

| 地址 | 说明 |
|---|---|
| http://127.0.0.1:8000/ | 网站首页 |
| http://127.0.0.1:8000/admin/ | 后台管理（用刚创建的超级用户登录） |

---

## 项目结构

```
.
├── .gitignore
├── requirements.txt
├── README.md
├── setup.ps1                                   ← 环境初始化脚本
├── python - django -网站制作 步骤最终版.docx    ← 课程步骤文档
└── wy_site/                                    ← Django 项目根目录
    ├── manage.py
    ├── sql/
    │   └── seed_demo_data.sql                  ← 原生 SQL 版测试数据
    ├── templates/                              ← 项目级模板
    │   ├── base.html                           ← 公共骨架：导航 / 提示条 / 页脚
    │   ├── course.html                         ← 主页：三张表
    │   ├── teacher_add.html
    │   ├── teacher_update.html
    │   ├── student_add.html
    │   └── student_update.html
    ├── courses/                                ← 应用
    │   ├── models.py                           ← Teacher / Course / Student
    │   ├── views.py                            ← 7 个视图函数 + 概览统计
    │   ├── urls.py                             ← 应用路由
    │   ├── admin.py                            ← 后台注册
    │   ├── context_processors.py               ← 侧边栏计数
    │   ├── seed.py                             ← 测试数据定义
    │   ├── management/commands/seed_data.py    ← python manage.py seed_data
    │   ├── templatetags/course_extras.py       ← 千分位等小过滤器
    │   ├── migrations/
    │   │   ├── 0001_initial.py                 ← Teacher + Course
    │   │   └── 0002_student.py                 ← Student
    │   └── static/
    │       ├── css/course.css                  ← 页面样式（设计系统）
    │       ├── js/course.js                    ← 表格搜索 / 二次确认等交互
    │       └── favicon.svg                     ← 标签页图标
    └── wy_site/                                ← 项目配置
        ├── settings.py                         ← 公共配置（密码走环境变量）
        ├── local_settings.example.py           ← 本地私有配置模板
        └── urls.py
```

---

## 演示数据

`python manage.py seed_data` 会写入下面这批数据，都是虚构的，用来把页面填满、方便看效果。

| 数据类型 | 数量 | 说明 |
|---|---|---|
| 讲师 `teacher` | 6 | 老王学堂、数据行者、阿May、CodeLao张、小林老师、晴天老师 |
| 课程 `courses` | 8 | 覆盖三种课程类型：后端开发 / 数据挖掘 / 其他 |
| 学生 `student` | 12 | 其中 **2025003 马腾** 故意没选课，用来展示「未选课」状态 |

数据定义都在 [`wy_site/courses/seed.py`](wy_site/courses/seed.py)，想加人直接改这个文件再执行一次命令即可。

> 两个注意点：
> 1. `courses.teacher_id` 指向 `teacher.nickname`，`student.course_id` 指向 `courses.title`，
>    所以脚本里必须**先写讲师、再写课程、最后写学生**，否则外键校验通不过。
> 2. 时间字段是 `auto_now_add` / `auto_now`，数据库层没有默认值，
>    原生 SQL 版里显式写了 `NOW(6)`，否则严格模式下会报「字段没有默认值」。

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

## 开发中踩到的三个坑

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
<form method="post" action="{% url 'courses:teacher_delete' t.nickname %}"
      data-confirm="确定要删除讲师「{{ t.nickname }}」吗？">
    {% csrf_token %}
    <button type="submit" class="btn btn-danger">删除</button>
</form>
```

`{% csrf_token %}` 绝对不能漏，否则 POST 会返回 `403 Forbidden`。

确认弹窗没有写成 `onsubmit="return confirm('...')"`，原因见下一个坑。

### 坑三：内联事件里拼用户输入，一个引号就废

一开始图省事，二次确认直接写在标签上：

```html
onsubmit="return confirm('确定要删除讲师「{{ t.nickname }}」吗？');"
```

昵称、姓名都是用户自己填的。只要有人叫 `O'Brien`，Django 会把它转义成
`O&#x27;Brien`，浏览器解析属性时又还原成 `O'Brien`，于是最终交给 JS 的是：

```js
return confirm('确定要删除讲师「O'Brien」吗？');   // ← 字符串被提前截断，整段语法错误
```

后果是那一行的「删除」按钮**点了没反应**（或者绕过确认直接提交），
而且只在特定名字上出现，很难复现。

正确做法是把文案放进 `data-*` 属性（属性值无论含什么引号、尖括号都是安全的），
由 JS 统一读取后再 `confirm()`：

```html
<form method="post" data-confirm="确定要删除讲师「{{ t.nickname }}」吗？">
```

```js
form.addEventListener('submit', function (event) {
    if (!window.confirm(form.getAttribute('data-confirm'))) {
        event.preventDefault();   // 取消就拦住这次提交
    }
});
```

顺手还能在确认通过后把按钮 `disabled`，防止手抖连点造成重复提交。

> 排查方式：用无头浏览器执行
> `[...document.querySelectorAll('[onsubmit]')].filter(f => typeof f.onsubmit !== 'function').length`，
> 返回非 0 就说明有内联处理器编译失败了。

---

## 已知问题与可改进点

**已知限制**

- **课程只能在后台增删改**，前台只做了展示（文档任务四~六要求的是讲师/学生的增删改）
- **一个学生只能报一门课**：`Student.course` 用的是 `ForeignKey`。
  如果想支持多选，要改成 `ManyToManyField`
- **删讲师会连带删掉他名下的所有课程**（`Course.teacher` 是 `CASCADE`），操作时注意
- **侧边栏占掉 248px**，所以 1000~1200px 这类窗口下三张表都会横向滚动。
  操作列已固定在右侧，按钮点得到，但看完整一行要横向拖动；
  更彻底的做法是把这个宽度区间的侧边栏收成「图标导航条」
- ~~数据库密码明文写在 `settings.py`~~：已改成从环境变量读，
  真实密码放进 `wy_site/wy_site/local_settings.py`（不进 Git），仓库里只留 `local_settings.example.py` 模板。
  注意历史提交里还留有旧密码，如果在意需要重写历史（`git filter-repo` / BFG）

**可以继续做的方向**

- 给课程也补一套前台增删改
- 学生选课改成多对多，支持一门课多个学生
- ~~列表加搜索~~：表格搜索已经做了，但是**纯前端**，只过滤当前页已加载的数据；
  数据量一大就得改成后端查询 + 分页（`Paginator`）
- 用 Django Form / ModelForm 代替手工取 `request.POST`，自动做字段校验
- 补单元测试（`courses/tests.py` 目前是空的）
