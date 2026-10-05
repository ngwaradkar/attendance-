import sqlite3
from database.db import connection,audit
from utils.auth import require_admin,hash_password
from utils.validators import student_values

def save_student(user,data,student_id=None):
    require_admin(user); data=student_values(data)
    with connection() as conn:
        if conn.execute('SELECT 1 FROM students WHERE lower(gr_no)=lower(?) AND id!=?',(data['gr_no'],student_id or -1)).fetchone(): raise ValueError('GR number already exists.')
        for table,key in [('divisions','division_id'),('streams','stream_id'),('academic_years','year_id')]:
            if not conn.execute(f'SELECT 1 FROM {table} WHERE id=?',(data[key],)).fetchone(): raise ValueError('Invalid academic selection.')
        fields=list(data)
        try:
            if student_id:
                old=conn.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
                if not old: raise ValueError('Student no longer exists.')
                has_records=conn.execute('SELECT 1 FROM attendance_records WHERE student_id=?',(student_id,)).fetchone()
                if has_records and any(old[k]!=data[k] for k in ['year_id','division_id','stream_id']):
                    raise ValueError('A student with attendance history cannot be moved to another year/class/stream. Create a new annual enrollment with a distinct GR suffix to preserve history.')
                conn.execute('UPDATE students SET '+','.join(f'{f}=?' for f in fields)+' WHERE id=?',list(data.values())+[student_id])
                action='Student deactivated' if old['active'] and not data['active'] else 'Student edited'
            else:
                student_id=conn.execute('INSERT INTO students('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',list(data.values())).lastrowid
                action='Student created'
            audit(conn,user,action,f"Student {student_id}: {data['name']}")
        except sqlite3.IntegrityError as exc: raise ValueError('GR or roll number already exists in this class/year/stream.') from exc
    return student_id

def import_valid(user,rows):
    require_admin(user); successful=failed=duplicates=0
    with connection() as conn:
        for data in rows:
            try:
                values=student_values(data); fields=list(values)
                if conn.execute('SELECT 1 FROM students WHERE lower(gr_no)=lower(?)',(values['gr_no'],)).fetchone(): duplicates+=1; continue
                conn.execute('INSERT INTO students('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',list(values.values())); successful+=1
            except sqlite3.IntegrityError: duplicates+=1
            except (ValueError,TypeError): failed+=1
        audit(conn,user,'Student imported',f'Successful: {successful}; Failed: {failed}; Duplicates: {duplicates}')
    return successful,failed,duplicates

def save_teacher(user,name,username,password,email='',teacher_id=None,active=True):
    require_admin(user)
    if not name.strip() or not username.strip(): raise ValueError('Teacher name and username are required.')
    if (not teacher_id or password) and len(password)<8: raise ValueError('Use a password with at least eight characters.')
    with connection() as conn:
        try:
            if teacher_id:
                old=conn.execute('SELECT user_id FROM teachers WHERE id=?',(teacher_id,)).fetchone()
                if not old: raise ValueError('Teacher not found.')
                conn.execute('UPDATE teachers SET name=?,email=?,active=? WHERE id=?',(name.strip(),email.strip(),int(active),teacher_id))
                conn.execute('UPDATE users SET name=?,username=?,active=? WHERE id=?',(name.strip(),username.strip(),int(active),old['user_id']))
                if password: conn.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(password),old['user_id']))
            else:
                uid=conn.execute('INSERT INTO users(username,password_hash,role,name) VALUES(?,?,?,?)',(username.strip(),hash_password(password),'teacher',name.strip())).lastrowid
                teacher_id=conn.execute('INSERT INTO teachers(user_id,name,email) VALUES(?,?,?)',(uid,name.strip(),email.strip())).lastrowid
            audit(conn,user,'Teacher saved',f'Teacher {teacher_id}: {name}')
        except sqlite3.IntegrityError as exc: raise ValueError('That username is already in use.') from exc

def save_master(user,table,name,active=True,record_id=None,class_id=None):
    require_admin(user)
    if table not in ['academic_years','classes','divisions','streams','subjects']: raise ValueError('Invalid master.')
    if not name.strip() or len(name)>100: raise ValueError('Enter a name up to 100 characters.')
    with connection() as conn:
        try:
            if record_id:
                conn.execute(f'UPDATE {table} SET name=?,active=? WHERE id=?',(name.strip(),int(active),record_id))
            elif table=='divisions':
                conn.execute('INSERT INTO divisions(class_id,name,active) VALUES(?,?,?)',(class_id,name.strip(),int(active)))
            else: conn.execute(f'INSERT INTO {table}(name,active) VALUES(?,?)',(name.strip(),int(active)))
            audit(conn,user,'Academic master saved',f'{table}: {name}; active={active}')
        except sqlite3.IntegrityError as exc: raise ValueError('This master name already exists.') from exc
