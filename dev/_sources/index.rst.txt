.. pymycqu documentation master file, created by
   sphinx-quickstart on Tue Nov 30 12:43:54 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

开始
====

安装
----

.. code-block:: shell

   pip install mycqu

考表
----

获取考表的例子，主要使用了 :py:func:`mycqu.exam.Exam.fetch` 方法从
https://my.cqu.edu.cn 上获取考试数据并生成 :py:class:`mycqu.exam.Exam` 对象：

.. code-block:: python

   from mycqu import Exam
   from datetime import date
   exams = Exam.fetch("201xxxxx") # 获取学号 201xxxxx 的本学期考表，返回 Exam 对象的列表
   today = date.today()
   print("之后的考试：")
   for exam in exams:
      if exam.date >= today:
         print(f'科目：{exam.course.name}, 教室：{exam.room}, '
               f'时间: {exam.date.strftime("%Y-%m-%d")} {exam.start_time.strftime("%H:%M")}')

输出样例：

.. code-block::

   之后的考试：
   科目：图像处理中的数学方法, 教室：d1242, 时间: 2021-12-06 14:25

课表
----

与考表不同的是，获取课表等数据需要先进行登录：

* 如果同一帐号连续尝试三次使用错误密码登录，
  那么再次登录时还需要输入二维码，此时 :py:func:`mycqu.auth.login` 会抛出
  :py:class:`mycqu.auth.NeedCaptcha` 异常，捕获它之后可以获取验证图片，输入验证码后继续登录

* 在统一身份认证号登录后还需要给 my.cqu.edu.cn 进行授权认证，使用 :py:func:`mycqu.mycqu.access_mycqu`

.. code-block:: python

   from mycqu import login, NeedCaptcha, access_mycqu
   from requests import Session

   session = Session()
   try:
      login(session, "统一身份认证号", "统一身份认证密码") # 需要登陆
   except NeedCaptcha as e: # 需要输入验证码的情况
      with open("captcha.jpg", "wb") as file:
         file.write(e.image)
      print("输入 captcha.jpg 处的验证码并回车: ", end="")
      e.after_captcha(input())
   access_mycqu(session)

之后就可以拿 ``session`` 去获取课表了，下面的代码用  :py:func:`mycqu.course.CourseTimetable.fetch`
获取了整个学期的课表，并从中筛选出第九周的课表

.. code-block:: python

   from mycqu import CourseTimetable
   timetables = CourseTimetable.fetch(session, "201xxxxx")  # 获取学号 201xxxxx 的本学期课表
   week = 9
   print(f"第 {week} 周的课")
   weekdays = ["一", "二", "三", "四", "五", "六", "日"]
   for timetable in timetables:
      for start, end in timetable.weeks:
         if start <= week <= end:
               break
      else:
         continue
      if timetable.day_time:
         print(f"科目：{timetable.course.name}, 教室：{timetable.classroom}, "
               f"周{weekdays[timetable.day_time.weekday]} {timetable.day_time.period[0]}~{timetable.day_time.period[1]} 节课")
      elif timetable.whole_week:
         print(f"科目：{timetable.course.name}, 地点: {timetable.classroom}, 全周时间")
      else:
         print(f"科目：{timetable.course.name}, 无明确时间")

输出样例：

.. code-block::

   第 9 周的课
   科目：偏微分方程, 教室：d1339, 周三 3~4 节课
   科目：偏微分方程, 教室：d1339, 周一 1~2 节课
   科目：复变函数, 教室：d1335, 周四 3~4 节课
   科目：复变函数, 教室：d1335, 周二 6~7 节课
   科目：运筹学, 教室：d1337, 周二 1~2 节课
   科目：运筹学, 教室：dyc410, 周五 1~2 节课
   科目：图像处理中的数学方法, 教室：d1329, 周三 6~7 节课
   科目：图像处理中的数学方法, 教室：d1329, 周一 6~7 节课
   科目：数据结构, 教室：d1339, 周二 10~11 节课
   科目：数据结构, 教室：d1142, 周一 3~4 节课
   科目：数据结构, 教室：数学实验中心, 周四 6~9 节课
   科目：java程序设计, 教室：d1518, 周三 1~2 节课
   科目：java程序设计, 教室：d1518, 周五 3~4 节课

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

API 文档
========

.. autosummary::
   :toctree: _stubs
   :recursive:

   mycqu
   mycqu.auth
   mycqu.card
   mycqu.course
   mycqu.exam
   mycqu.exception
   mycqu.library
   mycqu.mycqu
   mycqu.score
   mycqu.user

