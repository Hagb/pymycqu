# pymycqu

这个库对重庆大学 <http://my.cqu.edu.cn> 和统一身份认证的部分 web api 进行了封装，同时整理了相关数据模型。

Work in progress... 欢迎反馈和补充

感谢 <https://github.com/CQULHW/CQUQueryGrade> 项目提供了 <http://my.cqu.edu.cn> 的登陆方式。

## 安装

```bash
pip install .
```

## 例子

获取考表
```python
from mycqu.exam import Exam
from datetime import date
exams = Exam.fetch("201xxxxx") # 获取学号 201xxxxx 的本学期考表，返回 Exam 对象的列表
today = date.today()
print("之后的考试：")
for exam in exams:
    if exam.date >= today:
        print(f'科目：{exam.course.name}, 教室：{exam.room}, '
              f'时间: {exam.date.strftime("%Y-%m-%d")} {exam.start_time.strftime("%H:%M")}')
```
输出（样例）：
```
之后的考试：
科目：图像处理中的数学方法, 教室：D1242, 时间: 2021-12-06 14:25
```

获取课表（需要登陆）
```python
from mycqu.auth import login, NeedCaptcha
from mycqu.mycqu import access_mycqu
from mycqu.course import CourseTimetable
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

```
输出（样例）
```
第 9 周的课
科目：偏微分方程, 教室：D1339, 周三 3~4 节课
科目：偏微分方程, 教室：D1339, 周一 1~2 节课
科目：复变函数, 教室：D1335, 周四 3~4 节课
科目：复变函数, 教室：D1335, 周二 6~7 节课
科目：运筹学, 教室：D1337, 周二 1~2 节课
科目：运筹学, 教室：DYC410, 周五 1~2 节课
科目：图像处理中的数学方法, 教室：D1329, 周三 6~7 节课
科目：图像处理中的数学方法, 教室：D1329, 周一 6~7 节课
科目：数据结构, 教室：D1339, 周二 10~11 节课
科目：数据结构, 教室：D1142, 周一 3~4 节课
科目：数据结构, 教室：数学实验中心, 周四 6~9 节课
科目：Java程序设计, 教室：D1518, 周三 1~2 节课
科目：Java程序设计, 教室：D1518, 周五 3~4 节课
```

## 许可

AGPL 3.0
