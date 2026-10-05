"""Optional 2,000-student / 300,000-record smoke test in a temporary database."""
import os
import sys
import tempfile
import time
from pathlib import Path
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_tmp=tempfile.TemporaryDirectory(); os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'performance.db')
from database.db import initialize,connection,query
from utils.auth import login
from utils.helpers import today,now
from utils.calculations import student_report,aggregate,history
initialize(); admin=login('admin','admin123')
start=time.perf_counter()
with connection() as conn:
    for table in ['attendance_changes','attendance_records','attendance_sessions','students']:
        conn.execute(f'DELETE FROM {table}')
    conn.executemany('INSERT INTO students(roll_no,gr_no,name,division_id,stream_id,year_id) VALUES(?,?,?,?,?,?)',[(i,f'STRESS-{i}',f'Demo Stress Learner {i}',1,1,1) for i in range(1,2001)])
    student_ids=[r[0] for r in conn.execute('SELECT id FROM students')]
    for offset in range(30):
        day=today()-timedelta(days=offset)
        for period in range(1,6):
            sid=conn.execute('INSERT INTO attendance_sessions(attendance_date,year_id,division_id,stream_id,subject_id,teacher_id,period,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(day.isoformat(),1,1,1,2,1,period,now(),now())).lastrowid
            conn.executemany('INSERT INTO attendance_records(session_id,student_id,status) VALUES(?,?,?)',[(sid,s,'A' if (s+offset+period)%5==0 else 'P') for s in student_ids])
print(f'Fixture: 2,000 students / 300,000 attendance records; build {time.perf_counter()-start:.2f}s')
for name,fn in [('Student report',lambda:student_report(admin,{'year_id':1})),('Daily trend',lambda:aggregate(admin,{'year_id':1})),('Lecture history',lambda:history(admin,{'year_id':1}))]:
    start=time.perf_counter(); data=fn(); print(f'{name}: {len(data)} rows in {time.perf_counter()-start:.3f}s')
    assert not data.empty
assert len(student_report(admin,{'year_id':1}))==2000
assert query('SELECT COUNT(*) AS n FROM attendance_records').iloc[0].n==300000
print('Performance smoke check passed. Single-machine smoke test; not a concurrent-user load test.')
