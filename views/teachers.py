import sqlite3
import streamlit as st
from database.db import query,connection,audit
from utils import ui
from utils.auth import require_admin
from utils.admin import save_teacher

def render():
    u=ui.user(); require_admin(u); ui.title('👨‍🏫 Teacher Master','Manage teacher accounts and assign classes, subjects, and weekly lecture slots.')
    teachers=query('SELECT t.id,t.name AS Name,u.username AS Username,t.email AS Email,t.active AS Active FROM teachers t JOIN users u ON u.id=t.user_id ORDER BY t.id')
    ui.table(teachers)
    mode=st.radio('Account',['Add Teacher','Edit Teacher'],horizontal=True); old=None; tid=None
    if mode=='Edit Teacher' and not teachers.empty:
        tid=st.selectbox('Teacher account',teachers.id.tolist(),format_func=lambda v:teachers.set_index('id').loc[v,'Name'])
        old=teachers[teachers.id==tid].iloc[0]
    with st.form('teacher_form_'+str(tid)):
        name=st.text_input('Teacher name',value=old.Name if old is not None else '')
        username=st.text_input('Username',value=old.Username if old is not None else '')
        password=st.text_input('Password (leave blank to keep existing)' if tid else 'Password',type='password')
        email=st.text_input('Email',value=old.Email if old is not None else '')
        active=st.checkbox('Teacher active',value=bool(old.Active) if old is not None else True)
        if st.form_submit_button('Save Teacher',type='primary'):
            try: save_teacher(u,name,username,password,email,tid,active); ui.clear_master_cache(); st.rerun()
            except ValueError as exc: st.error(str(exc))
    st.subheader('Teacher Assignments & Demo Schedule')
    assignments=query('''SELECT ta.id,th.name AS Teacher,c.name||'-'||d.name AS Class,t.name AS Stream,b.name AS Subject,y.name AS "Academic Year",ta.period AS Period,ta.weekday AS Weekday,ta.active AS Active FROM teacher_assignments ta JOIN teachers th ON th.id=ta.teacher_id JOIN divisions d ON d.id=ta.division_id JOIN classes c ON c.id=d.class_id JOIN streams t ON t.id=ta.stream_id JOIN subjects b ON b.id=ta.subject_id JOIN academic_years y ON y.id=ta.year_id ORDER BY th.name,ta.weekday,ta.period''')
    ui.table(assignments)
    with st.expander('Add assignment / scheduled lecture'):
        with st.form('assignment_form'):
            teacher=ui.select('Teacher',ui.master('teachers'),'assign_teacher')
            year=ui.select('Academic Year',ui.master('academic_years'),'assign_year')
            div=ui.select('Class / Division',query("SELECT d.id,c.name||'-'||d.name AS name FROM divisions d JOIN classes c ON c.id=d.class_id WHERE d.active=1 AND c.active=1"),'assign_div')
            stream=ui.select('Stream',ui.master('streams'),'assign_stream')
            subject=ui.select('Subject',ui.master('subjects'),'assign_subject')
            weekday=st.selectbox('Weekday',range(7),format_func=lambda v:['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][v])
            from database.db import settings
            period=st.number_input('Period',1,int(settings()['periods']),1)
            if st.form_submit_button('Add Assignment'):
                if None in [teacher,year,div,stream,subject]: st.error('Complete every academic selection.')
                else:
                    try:
                        with connection() as conn:
                            conn.execute('INSERT INTO teacher_assignments(teacher_id,year_id,division_id,stream_id,subject_id,weekday,period) VALUES(?,?,?,?,?,?,?)',(teacher,year,div,stream,subject,weekday,period)); audit(conn,u,'Teacher assigned',f'Teacher {teacher}; division {div}; subject {subject}; day {weekday}; period {period}')
                        st.rerun()
                    except sqlite3.IntegrityError: st.error('This assignment already exists.')
    if not assignments.empty:
        aid=st.selectbox('Assignment ID to enable/disable',assignments.id.tolist())
        active=bool(assignments[assignments.id==aid].iloc[0].Active)
        if st.button('Disable Assignment' if active else 'Enable Assignment'):
            with connection() as conn:
                conn.execute('UPDATE teacher_assignments SET active=? WHERE id=?',(int(not active),aid)); audit(conn,u,'Assignment status changed',f'{aid}; active={not active}')
            st.rerun()
