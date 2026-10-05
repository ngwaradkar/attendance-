import os
import random
import secrets
from datetime import timedelta
from utils.auth import hash_password
from utils.helpers import today,now

DEFAULTS={'institution_name':'Vidya Prabodhini','institution_subtitle':'Higher Secondary Section – Class XI & XII','academic_year':'2026–27','warning_threshold':'75','critical_threshold':'60','good_threshold':'85','periods':'8','demo_mode':'1','logo_path':'assets/logo_placeholder.png'}

def seed(conn):
    rng=random.Random(2026)
    conn.executemany('INSERT INTO settings VALUES(?,?)',{**DEFAULTS,'auth_epoch':secrets.token_hex(16)}.items())
    conn.execute('INSERT INTO academic_years(name) VALUES(?)',('2026–27',))
    for name in ['XI','XII']:
        conn.execute('INSERT INTO classes(name) VALUES(?)',(name,))
    for class_id in [1,2]:
        for div in ['A','B']:
            conn.execute('INSERT INTO divisions(class_id,name) VALUES(?,?)',(class_id,div))
    for name in ['Science','Commerce','Arts']:
        conn.execute('INSERT INTO streams(name) VALUES(?)',(name,))
    subjects=['English','Mathematics','Physics','Chemistry','Biology','Accountancy','Economics','Business Studies','Computer Science','Information Technology']
    for name in subjects:
        conn.execute('INSERT INTO subjects(name) VALUES(?)',(name,))
    conn.execute('INSERT INTO users(username,password_hash,role,name) VALUES(?,?,?,?)',
                 (os.environ.get('DEMO_ADMIN_USERNAME','admin'),hash_password(os.environ.get('DEMO_ADMIN_PASSWORD','admin123')),'admin','Demo Administrator'))
    for i,name in enumerate(['Demo Teacher Meera','Demo Teacher Arjun','Demo Teacher Kavya','Demo Teacher Rohan','Demo Teacher Tara'],1):
        uid=conn.execute('INSERT INTO users(username,password_hash,role,name) VALUES(?,?,?,?)',(f'teacher{i}',hash_password(os.environ.get('DEMO_TEACHER_PASSWORD','teacher123')),'teacher',name)).lastrowid
        conn.execute('INSERT INTO teachers(user_id,name,email) VALUES(?,?,?)',(uid,name,f'teacher{i}@example.invalid'))
    # A divisions demonstrate Science; B divisions demonstrate Commerce.
    for division in range(1,5):
        stream=1 if division in [1,3] else 2
        for roll in range(1,31):
            name=f'Demo Learner {"XI" if division<3 else "XII"}-{"A" if division%2 else "B"} {roll:02d}'
            conn.execute('INSERT INTO students(roll_no,gr_no,name,gender,division_id,stream_id,year_id,parent_name,parent_mobile,student_mobile) VALUES(?,?,?,?,?,?,?,?,?,?)',
                         (roll,f'DEMO-{division}-{roll:03d}',name,'Female' if roll%2 else 'Male',division,stream,1,f'Demo Guardian {division}-{roll:02d}','0000000000','0000000000'))
    for division in range(1,5):
        stream=1 if division%2 else 2
        subject_list=[2,1,3,4,5,9] if stream==1 else [6,1,7,8,10,2]
        for weekday in range(6):
            for slot,subject in enumerate(subject_list[:4],1):
                period=((slot-1+2*(division-1))%8)+1
                teacher=1 if subject==2 else (2 if subject==1 else 3+(subject%3))
                conn.execute('INSERT INTO teacher_assignments(teacher_id,division_id,stream_id,subject_id,year_id,period,weekday) VALUES(?,?,?,?,?,?,?)',(teacher,division,stream,subject,1,period,weekday))
    start=today()-timedelta(days=59)
    timestamp=now()
    for offset in range(60):
        day=start+timedelta(days=offset)
        if day.weekday()==6:
            continue
        for assignment in conn.execute('SELECT * FROM teacher_assignments WHERE weekday=? AND subject_id IN (1,2,6)',(day.weekday(),)).fetchall():
            sid=conn.execute('INSERT INTO attendance_sessions(attendance_date,year_id,division_id,stream_id,subject_id,teacher_id,period,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                             (day.isoformat(),1,assignment['division_id'],assignment['stream_id'],assignment['subject_id'],assignment['teacher_id'],assignment['period'],timestamp,timestamp)).lastrowid
            for student in conn.execute('SELECT id,roll_no FROM students WHERE division_id=?',(assignment['division_id'],)).fetchall():
                probability=0.62 if student['roll_no']<=5 else 0.80+0.018*(student['roll_no']%10)
                conn.execute('INSERT INTO attendance_records(session_id,student_id,status) VALUES(?,?,?)',(sid,student['id'],'P' if rng.random()<probability else 'A'))
    conn.execute('INSERT INTO audit_logs(timestamp,user_id,username,action,details) VALUES(?,?,?,?,?)',(timestamp,1,os.environ.get('DEMO_ADMIN_USERNAME','admin'),'Demo initialized','120 fictional students; 5 teachers; 60 calendar days of fictional lecture history.'))
