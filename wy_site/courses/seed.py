"""
演示用测试数据。

放在这里而不是直接写进数据库，好处是：
  · `python manage.py seed_data` 可以一键导入，重复执行也不会产生重复数据
  · 想改演示内容只要改这一个文件
  · 原生 SQL 脚本 `sql/seed_demo_data.sql` 里的数据也照着这里保持一致

字段顺序说明：
  COURSES['teacher'] 填讲师的 nickname（teacher 表主键）
  STUDENTS['course'] 填课程名（courses 表主键），填 None 表示暂不选课
"""

import datetime as dt

# ---------------------------------------------------------------- 讲师
TEACHERS = [
    {
        'nickname': '老王学堂',
        'introduction': '10 年后端老兵，专注 Python / Django 实战教学，讲课喜欢先画图再写代码。',
        'fans': 12800,
    },
    {
        'nickname': '数据行者',
        'introduction': '前大厂数据挖掘工程师，擅长用户画像、推荐系统与特征工程。',
        'fans': 9360,
    },
    {
        'nickname': '阿May',
        'introduction': '全栈开发者，Vue + Django 双修，业余时间喜欢写各种小工具。',
        'fans': 7420,
    },
    {
        'nickname': 'CodeLao张',
        'introduction': '算法竞赛教练，带过 200+ 名蓝桥杯获奖选手，主打「先把题读懂」。',
        'fans': 5210,
    },
    {
        'nickname': '小林老师',
        'introduction': '爬虫与数据分析讲师，讲课节奏慢，适合零基础同学入门。',
        'fans': 4680,
    },
    {
        'nickname': '晴天老师',
        'introduction': '前端美化达人，专注 UI 细节与交互动效，信奉「好看的东西才好用」。',
        'fans': 10240,
    },
]

# ---------------------------------------------------------------- 课程
# type: 1 后端开发 / 2 数据挖掘 / 0 其他
COURSES = [
    {
        'title': 'Django 从入门到上线',
        'teacher': '老王学堂',
        'type': 1,
        'price': 199,
        'volume': 500,
        'online': dt.date(2025, 9, 1),
    },
    {
        'title': 'Python 爬虫实战',
        'teacher': '小林老师',
        'type': 2,
        'price': 299,
        'volume': 300,
        'online': dt.date(2025, 10, 15),
    },
    {
        'title': 'MySQL 数据库原理与优化',
        'teacher': '老王学堂',
        'type': 1,
        'price': 259,
        'volume': 400,
        'online': dt.date(2025, 11, 20),
    },
    {
        'title': '数据分析与可视化',
        'teacher': '数据行者',
        'type': 2,
        'price': 359,
        'volume': 200,
        'online': dt.date(2026, 1, 8),
    },
    {
        'title': '算法与数据结构精讲',
        'teacher': 'CodeLao张',
        'type': 0,
        'price': 399,
        'volume': 150,
        'online': dt.date(2025, 12, 10),
    },
    {
        'title': '前端美化与交互设计',
        'teacher': '晴天老师',
        'type': 0,
        'price': 189,
        'volume': 260,
        'online': dt.date(2026, 3, 2),
    },
    {
        'title': 'Vue 3 企业级实战',
        'teacher': '阿May',
        'type': 0,
        'price': 329,
        'volume': 220,
        'online': dt.date(2026, 4, 18),
    },
    {
        'title': '推荐系统入门',
        'teacher': '数据行者',
        'type': 2,
        'price': 459,
        'volume': 120,
        'online': dt.date(2026, 6, 5),
    },
]

# ---------------------------------------------------------------- 学生
STUDENTS = [
    {
        'sno': '2024001',
        'name': '张小明',
        'gender': 1,
        'age': 19,
        'email': 'zhangxiaoming@example.com',
        'phone': '13800138001',
        'course': 'Django 从入门到上线',
        'enroll_at': dt.date(2024, 9, 1),
        'introduction': '喜欢后端，正在啃 Django 的 ORM。',
    },
    {
        'sno': '2024002',
        'name': '李思思',
        'gender': 0,
        'age': 20,
        'email': 'lisisi@example.com',
        'phone': '13800138002',
        'course': '数据分析与可视化',
        'enroll_at': dt.date(2024, 9, 1),
        'introduction': '统计学专业，对数据可视化特别感兴趣。',
    },
    {
        'sno': '2024003',
        'name': '王浩然',
        'gender': 1,
        'age': 21,
        'email': 'wanghaoran@example.com',
        'phone': '13800138003',
        'course': 'MySQL 数据库原理与优化',
        'enroll_at': dt.date(2024, 9, 2),
        'introduction': '想彻底搞懂索引和执行计划。',
    },
    {
        'sno': '2024004',
        'name': '陈雨欣',
        'gender': 0,
        'age': 19,
        'email': 'chenyuxin@example.com',
        'phone': '13800138004',
        'course': 'Python 爬虫实战',
        'enroll_at': dt.date(2024, 9, 2),
        'introduction': '写过一点小爬虫，希望系统学一遍。',
    },
    {
        'sno': '2024005',
        'name': '刘子豪',
        'gender': 1,
        'age': 22,
        'email': 'liuzihao@example.com',
        'phone': '13800138005',
        'course': '算法与数据结构精讲',
        'enroll_at': dt.date(2024, 9, 3),
        'introduction': '准备明年春招，每天刷两道题。',
    },
    {
        'sno': '2024006',
        'name': '赵敏',
        'gender': 0,
        'age': 20,
        'email': 'zhaomin@example.com',
        'phone': '13800138006',
        'course': '前端美化与交互设计',
        'enroll_at': dt.date(2024, 9, 3),
        'introduction': '喜欢把页面做得好看看的。',
    },
    {
        'sno': '2024007',
        'name': '周杰',
        'gender': 1,
        'age': 20,
        'email': 'zhoujie@example.com',
        'phone': '13800138007',
        'course': 'Vue 3 企业级实战',
        'enroll_at': dt.date(2024, 9, 4),
        'introduction': '会一点 Vue 2，想升级到 Vue 3 的组合式写法。',
    },
    {
        'sno': '2024008',
        'name': '吴倩',
        'gender': 0,
        'age': 21,
        'email': 'wuqian@example.com',
        'phone': '13800138008',
        'course': '推荐系统入门',
        'enroll_at': dt.date(2024, 9, 5),
        'introduction': '对推荐算法好奇很久了。',
    },
    {
        'sno': '2025001',
        'name': '郑凯',
        'gender': 1,
        'age': 18,
        'email': 'zhengkai@example.com',
        'phone': '13800138009',
        'course': 'Django 从入门到上线',
        'enroll_at': dt.date(2025, 9, 1),
        'introduction': '大一新生，刚接触 Web 开发。',
    },
    {
        'sno': '2025002',
        'name': '孙悦',
        'gender': 0,
        'age': 19,
        'email': 'sunyue@example.com',
        'phone': '13800138010',
        'course': '数据分析与可视化',
        'enroll_at': dt.date(2025, 9, 1),
        'introduction': '想在社团里做数据报表。',
    },
    {
        'sno': '2025003',
        'name': '马腾',
        'gender': 1,
        'age': 20,
        'email': 'mateng@example.com',
        'phone': '13800138011',
        'course': None,  # 故意留一个「未选课」的同学，用来展示空状态
        'enroll_at': dt.date(2025, 9, 2),
        'introduction': '还在纠结选哪门课。',
    },
    {
        'sno': '2025004',
        'name': '何静',
        'gender': 0,
        'age': 19,
        'email': 'hejing@example.com',
        'phone': '13800138012',
        'course': 'Python 爬虫实战',
        'enroll_at': dt.date(2025, 9, 3),
        'introduction': '想爬点公开数据做课程论文。',
    },
]
