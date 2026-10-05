"""Database-backed reporting and authorization. Missing records never imply absence."""
from database.db import query,one,connection,audit,settings
from utils.helpers import now,today
from utils.auth import require_admin

STUDENT_JOIN=''' FROM students s JOIN divisions d ON d.id=s.division_id JOIN classes c ON c.id=d.class_id JOIN streams t ON t.id=s.stream_id JOIN academic_years y ON y.id=s.year_id '''
RECORD_JOIN=''' FROM attendance_records r JOIN attendance_sessions a ON a.id=r.session_id JOIN students s ON s.id=r.student_id JOIN divisions d ON d.id=a.division_id JOIN classes c ON c.id=d.class_id JOIN streams t ON t.id=a.stream_id JOIN subjects b ON b.id=a.subject_id JOIN teachers th ON th.id=a.teacher_id '''
VALID="a.cancelled=0 AND NOT EXISTS(SELECT 1 FROM holidays h WHERE h.holiday_date=a.attendance_date)"

def assignment_scope(user,alias='a'):
    if user['role']=='admin':
        return '1=1',[]
    return f'''EXISTS(SELECT 1 FROM teacher_assignments ta WHERE ta.teacher_id=? AND ta.active=1 AND ta.year_id={alias}.year_id AND ta.division_id={alias}.division_id AND ta.stream_id={alias}.stream_id AND ta.subject_id={alias}.subject_id)''',[user['teacher_id']]

def clauses(user,filters=None):
    scope,args=assignment_scope(user)
    where=[VALID,scope]
    for key,value in (filters or {}).items():
        if value is None or value=='':
            continue
        if key in ['year_id','division_id','stream_id','subject_id','teacher_id']:
            where.append(f'a.{key}=?'); args.append(int(value))
        elif key=='class_id':
            where.append('d.class_id=?'); args.append(int(value))
        elif key=='start':
            where.append('a.attendance_date>=?'); args.append(str(value))
        elif key=='end':
            where.append('a.attendance_date<=?'); args.append(str(value))
        elif key=='student_id':
            where.append('s.id=?'); args.append(int(value))
    return ' AND '.join(where),args

def students(user,year_id=None,division_id=None,stream_id=None,active_only=False,class_id=None):
    where=['1=1']; args=[]
    if user['role']=='teacher':
        where.append('EXISTS(SELECT 1 FROM teacher_assignments ta WHERE ta.teacher_id=? AND ta.active=1 AND ta.year_id=s.year_id AND ta.division_id=s.division_id AND ta.stream_id=s.stream_id)'); args.append(user['teacher_id'])
    for key,value in [('year_id',year_id),('division_id',division_id),('stream_id',stream_id)]:
        if value:
            where.append(f's.{key}=?'); args.append(int(value))
    if class_id: where.append('d.class_id=?'); args.append(int(class_id))
    if active_only: where.append('s.active=1')
    return query('''SELECT s.id AS student_id,s.roll_no AS "Roll No",s.gr_no AS "GR No",s.name AS Student,s.gender AS Gender,c.name AS Class,d.name AS Division,t.name AS Stream,y.name AS "Academic Year",s.parent_name AS "Parent Name",s.parent_mobile AS "Parent Mobile",s.student_mobile AS "Student Mobile",s.active AS Active,s.division_id,s.stream_id,s.year_id '''+STUDENT_JOIN+' WHERE '+' AND '.join(where)+' ORDER BY c.name,d.name,s.roll_no',args)

def student_report(user,filters=None,by_subject=False):
    where,args=clauses(user,filters)
    subject=',b.name AS Subject' if by_subject else ''
    group=',a.subject_id' if by_subject else ''
    return query('''SELECT s.id AS student_id,s.roll_no AS "Roll No",s.name AS Student,c.name AS Class,d.name AS Division,t.name AS Stream'''+subject+''',COUNT(*) AS Lectures,SUM(r.status='P') AS Present,SUM(r.status='A') AS Absent,ROUND(100.0*SUM(r.status='P')/COUNT(*),2) AS "Attendance %" '''+RECORD_JOIN+' WHERE '+where+' GROUP BY s.id,a.division_id,a.stream_id'+group+' ORDER BY c.name,d.name,s.roll_no',args)

def aggregate(user,filters=None,dimension='date'):
    mapping={'date':('a.attendance_date','Date'),'class':("c.name||'-'||d.name",'Class'),'subject':('b.name','Subject'),'teacher':('th.name','Teacher')}
    expr,label=mapping[dimension]
    where,args=clauses(user,filters)
    return query(f'''SELECT {expr} AS "{label}",COUNT(*) AS "Lecture Records",SUM(r.status='P') AS Present,SUM(r.status='A') AS Absent,ROUND(100.0*SUM(r.status='P')/COUNT(*),2) AS "Attendance %" '''+RECORD_JOIN+' WHERE '+where+f' GROUP BY {expr} ORDER BY {expr}',args)

def history(user,filters=None,own_only=False,include_cancelled=False):
    where,args=clauses(user,filters)
    if include_cancelled: where=where.replace(VALID,'1=1')
    if own_only and user['role']=='teacher':
        where+=' AND a.teacher_id=?'; args.append(user['teacher_id'])
    return query('''SELECT a.id AS session_id,a.attendance_date AS Date,a.period AS Period,c.name||'-'||d.name AS Class,t.name AS Stream,b.name AS Subject,th.name AS Teacher,COUNT(r.id) AS Total,SUM(r.status='P') AS Present,SUM(r.status='A') AS Absent,ROUND(100.0*SUM(r.status='P')/NULLIF(COUNT(r.id),0),2) AS "Attendance %",a.cancelled AS Cancelled '''+RECORD_JOIN+' WHERE '+where+' GROUP BY a.id ORDER BY a.attendance_date DESC,a.period,c.name,d.name',args)

def can_edit(user,session,conn=None):
    if user['role']=='admin': return True
    if session['teacher_id']!=user['teacher_id']: return False
    sql='''SELECT 1 FROM teacher_assignments WHERE teacher_id=? AND year_id=? AND division_id=? AND stream_id=? AND subject_id=? AND active=1'''
    params=(user['teacher_id'],session['year_id'],session['division_id'],session['stream_id'],session['subject_id'])
    return bool(conn.execute(sql,params).fetchone()) if conn else bool(one(sql,params))

def existing_session(key):
    return one('SELECT * FROM attendance_sessions WHERE attendance_date=? AND year_id=? AND division_id=? AND stream_id=? AND subject_id=? AND period=?',tuple(key[k] for k in ['attendance_date','year_id','division_id','stream_id','subject_id','period']))

def session_records(user,session_id):
    session=one('SELECT * FROM attendance_sessions WHERE id=?',(session_id,))
    if not session: raise ValueError('Attendance record no longer exists.')
    where,args=assignment_scope(user)
    allowed=one('SELECT a.id FROM attendance_sessions a WHERE a.id=? AND '+where,[session_id]+args)
    if not allowed: raise PermissionError('You cannot access this lecture.')
    return query('''SELECT r.student_id,s.roll_no AS "Roll No",s.name AS Student,r.status AS Status FROM attendance_records r JOIN students s ON s.id=r.student_id WHERE session_id=? ORDER BY s.roll_no''',(session_id,))

def save_attendance(user,key,statuses,editing=False,expected_updated=None,reason=''):
    if not statuses or any(v not in ['P','A'] for v in statuses.values()):
        raise ValueError('Select Present or Absent for every student.')
    day=str(key['attendance_date'])
    if day>today().isoformat(): raise ValueError('Attendance cannot be recorded for a future date.')
    timestamp=now()
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM holidays WHERE holiday_date=?',(day,)).fetchone():
            raise ValueError('This date is a holiday. No lecture attendance can be saved.')
        if not 1<=int(key['period'])<=int(settings()['periods']): raise ValueError('Invalid period.')
        if user['role']=='teacher':
            teacher_id=user['teacher_id']
            permitted=conn.execute('SELECT 1 FROM teacher_assignments WHERE teacher_id=? AND year_id=? AND division_id=? AND stream_id=? AND subject_id=? AND active=1',(teacher_id,key['year_id'],key['division_id'],key['stream_id'],key['subject_id'])).fetchone()
            if not permitted: raise PermissionError('This class and subject are not assigned to you.')
        else:
            teacher_id=int(key['teacher_id'])
        if not conn.execute('SELECT 1 FROM teachers WHERE id=? AND active=1',(teacher_id,)).fetchone(): raise ValueError('Select an active teacher.')
        values=tuple(key[k] for k in ['attendance_date','year_id','division_id','stream_id','subject_id','period'])
        session=conn.execute('SELECT * FROM attendance_sessions WHERE attendance_date=? AND year_id=? AND division_id=? AND stream_id=? AND subject_id=? AND period=?',values).fetchone()
        if session and not editing: raise ValueError('Attendance has already been recorded for this lecture. Open Edit Attendance.')
        if editing and not session: raise ValueError('The lecture no longer exists. Reload attendance.')
        if session:
            if not can_edit(user,dict(session),conn): raise PermissionError('Only the recording teacher or an administrator may correct this lecture.')
            if session['cancelled']: raise ValueError('This lecture is cancelled. Restore it from history first.')
            if expected_updated!=session['updated_at']: raise ValueError('Another user changed this lecture. Reload before editing.')
            if not reason.strip(): raise ValueError('Enter a reason for the correction.')
            records={r['student_id']:r for r in conn.execute('SELECT * FROM attendance_records WHERE session_id=?',(session['id'],))}
            if set(statuses)!=set(records): raise ValueError('The saved roster changed. Reload attendance.')
            sid=session['id']; changes=0
            for student,status in statuses.items():
                record=records[student]
                if record['status']!=status:
                    conn.execute('INSERT INTO attendance_changes(record_id,original_status,updated_status,changed_by,changed_at,reason) VALUES(?,?,?,?,?,?)',(record['id'],record['status'],status,user['id'],timestamp,reason.strip()))
                    conn.execute('UPDATE attendance_records SET status=? WHERE id=?',(status,record['id'])); changes+=1
            # Microseconds make the optimistic revision distinct even for rapid edits.
            from datetime import datetime
            revision=datetime.now().isoformat(timespec='microseconds')
            conn.execute('UPDATE attendance_sessions SET updated_at=? WHERE id=?',(revision,sid))
            audit(conn,user,'Attendance edited',f'Session {sid}; {changes} changes; reason: {reason.strip()}')
        else:
            roster={r[0] for r in conn.execute('SELECT id FROM students WHERE year_id=? AND division_id=? AND stream_id=? AND active=1',(key['year_id'],key['division_id'],key['stream_id']))}
            if set(statuses)!=roster: raise ValueError('Student roster changed. Reload the student list.')
            sid=conn.execute('INSERT INTO attendance_sessions(attendance_date,year_id,division_id,stream_id,subject_id,teacher_id,period,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(day,key['year_id'],key['division_id'],key['stream_id'],key['subject_id'],teacher_id,key['period'],timestamp,timestamp)).lastrowid
            conn.executemany('INSERT INTO attendance_records(session_id,student_id,status) VALUES(?,?,?)',[(sid,s,status) for s,status in statuses.items()])
            audit(conn,user,'Attendance created',f'Session {sid}; {len(statuses)} students; {sum(v=="A" for v in statuses.values())} absent')
        return sid

def cancel_session(user,session_id,cancelled,reason):
    if not reason.strip(): raise ValueError('Enter a reason.')
    with connection() as conn:
        session=conn.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
        if not session or not can_edit(user,dict(session),conn): raise PermissionError('You cannot change this lecture.')
        conn.execute('UPDATE attendance_sessions SET cancelled=?,updated_at=? WHERE id=?',(int(cancelled),now(),session_id))
        audit(conn,user,'Lecture cancelled' if cancelled else 'Lecture restored',f'Session {session_id}: {reason}')

def daily_absent(user,filters):
    where,args=clauses(user,filters)
    return query('''SELECT DISTINCT s.roll_no AS "Roll No",s.name AS Student,c.name AS Class,d.name AS Division,s.parent_name AS "Parent Name",s.parent_mobile AS "Parent Mobile" '''+RECORD_JOIN+' WHERE '+where+" AND r.status='A' ORDER BY c.name,d.name,s.roll_no",args)

def monthly_records(user,filters):
    where,args=clauses(user,filters)
    return query('''SELECT s.id AS student_id,s.roll_no AS "Roll No",s.name AS Student,a.attendance_date AS Date,a.period AS Period,r.status AS Status '''+RECORD_JOIN+' WHERE '+where+' ORDER BY s.roll_no,a.attendance_date,a.period',args)
