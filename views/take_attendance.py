import streamlit as st
from database.db import query,one,settings
from utils import ui
from utils.helpers import today,percent
from utils.calculations import students,existing_session,session_records,can_edit,save_attendance

def attendance_editor(roster,key,session=None):
    u=ui.user(); prefix='roster_'+str(key)
    if session and not can_edit(u,session):
        st.info('You can view this lecture. Only its recording teacher or an administrator may correct it.'); ui.table(roster); return
    if session:
        st.warning('Attendance has already been recorded for this lecture.')
        mode=st.radio('Existing attendance',['View Existing Attendance','Edit Attendance'],horizontal=True,key=prefix+'_mode')
        if mode.startswith('View'):
            ui.table(roster); return
        if session['cancelled']:
            st.warning('This lecture is cancelled. Restore it from Attendance History before editing.'); return
    original={int(r.student_id):r.Status if hasattr(r,'Status') else 'P' for r in roster.itertuples()}
    revision=session['updated_at'] if session else 'new'
    if st.session_state.get(prefix+'_revision')!=revision:
        for sid,status in original.items(): st.session_state[f'{prefix}_{sid}']=status=='P'
        st.session_state[prefix+'_revision']=revision
    buttons=st.columns(3)
    for col,label,value in zip(buttons,['✅ Mark All Present','❌ Mark All Absent','🔄 Reset'],[True,False,None]):
        if col.button(label,key=prefix+label,width='stretch'):
            for sid,status in original.items(): st.session_state[f'{prefix}_{sid}']=(status=='P') if value is None else value
    statuses={}
    st.caption('All students start Present. Switch off only the absent students. The saved roster stays fixed when correcting a lecture.')
    with st.container(border=True):
        for row in roster.itertuples():
            sid=int(row.student_id)
            # One full-width control per student remains usable on phones and tablets.
            present=st.toggle(f'{getattr(row,"_2",sid):02d} · {row.Student}',key=f'{prefix}_{sid}',value=original[sid]=='P')
            statuses[sid]='P' if present else 'A'
    p=sum(x=='P' for x in statuses.values()); a=len(statuses)-p
    ui.cards([('Present',p,'Ready to save'),('Absent',a,'Review before saving'),('Attendance',f'{percent(p,len(statuses))}%','This lecture')])
    reason=st.text_input('Reason for correction',key=prefix+'_reason') if session else ''
    if st.button('💾 Save Attendance',type='primary',key=prefix+'_save',width='stretch'):
        try:
            sid=save_attendance(u,key,statuses,editing=bool(session),expected_updated=revision if session else None,reason=reason)
            names=roster.loc[roster.student_id.isin([s for s,v in statuses.items() if v=='A']),'Student'].tolist()
            info=one('''SELECT c.name||'-'||d.name AS class_name,b.name AS subject FROM attendance_sessions a JOIN divisions d ON d.id=a.division_id JOIN classes c ON c.id=d.class_id JOIN subjects b ON b.id=a.subject_id WHERE a.id=?''',(sid,))
            st.session_state['saved_summary']={'Class':info['class_name'],'Subject':info['subject'],'Date':str(key['attendance_date']),'Period':key['period'],'Total Students':len(statuses),'Present':p,'Absent':a,'Attendance':f'{percent(p,len(statuses))}%','Absent Students':', '.join(names) or 'None'}
            st.rerun()
        except (ValueError,PermissionError) as exc: st.error(str(exc))

def render():
    ui.title('✅ Mark Attendance','Select the lecture, mark absent students, and save. Simple • Fast • Paperless')
    if 'saved_summary' in st.session_state:
        st.success('✅ Attendance Saved Successfully')
        st.write(st.session_state.pop('saved_summary'))
    target=st.session_state.pop('open_session',None)
    if target: st.session_state['editing_session']=target
    if st.session_state.get('editing_session'):
        session=one('SELECT * FROM attendance_sessions WHERE id=?',(st.session_state.editing_session,))
        if st.button('← Select another lecture'):
            st.session_state.pop('editing_session',None); st.rerun()
        if session:
            st.subheader(f"Lecture {session['id']} · {session['attendance_date']} · Period {session['period']}")
            attendance_editor(session_records(ui.user(),session['id']),session,session)
        return
    f=ui.filters('take',dates=False,all_option=False)
    col=st.columns(3)
    with col[0]: date=st.date_input('Date',today(),max_value=today(),key='take_date')
    with col[1]: period=st.selectbox('Period',range(1,int(settings()['periods'])+1),key='take_period')
    with col[2]:
        if ui.user()['role']=='admin': teacher=ui.select('Teacher',ui.master('teachers'),'take_teacher')
        else:
            teacher=ui.user()['teacher_id']; st.text_input('Teacher',ui.user()['name'],disabled=True)
    if any(not f.get(x) for x in ['year_id','division_id','stream_id','subject_id']) or not teacher:
        st.info('Please select an available class, division, stream, subject, and teacher.'); return
    if one('SELECT id FROM holidays WHERE holiday_date=?',(date.isoformat(),)):
        st.warning('This date is a holiday. Attendance is disabled.'); return
    key={**f,'attendance_date':date.isoformat(),'period':period,'teacher_id':teacher}
    session=existing_session(key)
    roster=session_records(ui.user(),session['id']) if session else students(ui.user(),f['year_id'],f['division_id'],f['stream_id'],True)[['student_id','Roll No','Student']]
    if roster.empty: st.info('No active students found for this class and stream.'); return
    attendance_editor(roster,key,session)
