from datetime import timedelta
import streamlit as st
import plotly.express as px
from database.db import query,settings,one
from utils import ui
from utils.helpers import today,percent
from utils.calculations import students,student_report,aggregate,history

def render():
    u=ui.user(); cfg=settings(); day=today(); years=ui.master('academic_years')
    year=int(years.loc[years.name==cfg['academic_year'],'id'].iloc[0])
    scope={'year_id':year}; daily={**scope,'start':day,'end':day}
    ui.title('Welcome to the '+cfg['institution_name']+' Digital Attendance Portal','Simple • Fast • Paperless · Transforming classroom attendance from paper registers to digital records.')
    if u['role']=='teacher':
        teacher_dashboard(u,year); return
    counts=aggregate(u,daily); p=int(counts.Present.sum()); a=int(counts.Absent.sum())
    report=student_report(u,scope); low=report[report['Attendance %']<float(cfg['warning_threshold'])]
    hist=history(u,daily)
    ui.cards([('👨‍🎓 Total Students',len(students(u,year,active_only=True)),'Active in this academic year'),('✅ Present Today',p,'Present lecture records'),('❌ Absent Today',a,'Absent lecture records'),("📊 Today's Attendance",f'{percent(p,p+a)}%' if p+a else 'No records','Based on recorded lectures'),('⚠️ Below '+cfg['warning_threshold']+'%',len(low),'Students with recorded attendance'),('👨‍🏫 Active Teachers Today',hist.Teacher.nunique(),'Teachers who recorded attendance')])
    st.caption('Daily KPIs count student-lecture records. A student attending several periods contributes once per period. Defaulter totals use all recorded lectures in the selected academic year.')
    trend=aggregate(u,{**scope,'start':day-timedelta(days=59),'end':day})
    c=st.columns(2)
    with c[0]:
        st.subheader('Daily Attendance Trend')
        if not trend.empty: st.plotly_chart(px.line(trend,x='Date',y='Attendance %',markers=True,color_discrete_sequence=['#2563eb']).update_layout(yaxis_range=[0,100]),width='stretch')
    with c[1]:
        st.subheader('Class-wise Attendance')
        data=aggregate(u,scope,'class')
        if not data.empty: st.plotly_chart(px.bar(data,x='Class',y='Attendance %',color='Class').update_layout(yaxis_range=[0,100],showlegend=False),width='stretch')
    c=st.columns(2)
    with c[0]:
        st.subheader('Present vs Absent · Today')
        if p+a: st.plotly_chart(px.pie(names=['Present','Absent'],values=[p,a],hole=.7,color_discrete_sequence=['#2563eb','#f97316']),width='stretch')
        else: st.info('No lectures recorded today.')
    with c[1]:
        st.subheader('Subject-wise Attendance')
        data=aggregate(u,scope,'subject')
        if not data.empty: st.plotly_chart(px.bar(data,x='Attendance %',y='Subject',orientation='h').update_layout(xaxis_range=[0,100]),width='stretch')
    st.subheader('⚠️ Low Attendance Students'); ui.table(low)
    st.subheader('Teacher-wise Attendance Activity'); activity=hist.groupby('Teacher',as_index=False).agg(Lectures=('session_id','count'),Students=('Total','sum')) if not hist.empty else hist
    ui.table(activity)
    if cfg['demo_mode']=='1':
        with st.expander('🎬 Quick Demo · Presentation Walkthrough',expanded=True):
            st.markdown('1. Login as **teacher1**.\n2. Select **XI-A → Science → Mathematics**.\n3. Select **Period 3** (a fresh lecture).\n4. Switch off three students.\n5. Save attendance and review the summary.\n6. Login as admin and open Today’s Attendance.\n7. Open Defaulter Report.\n8. Download the Excel report.')

def teacher_dashboard(u,year):
    day=today(); ui.title('Welcome, '+u['name'],'Your assigned lectures and classroom attendance at a glance.')
    schedule=query('''SELECT ta.id,c.name||'-'||d.name AS Class,t.name AS Stream,b.name AS Subject,ta.period AS Period,ta.division_id,ta.stream_id,ta.subject_id FROM teacher_assignments ta JOIN divisions d ON d.id=ta.division_id JOIN classes c ON c.id=d.class_id JOIN streams t ON t.id=ta.stream_id JOIN subjects b ON b.id=ta.subject_id WHERE ta.teacher_id=? AND ta.year_id=? AND ta.weekday=? AND ta.active=1 AND d.active=1 AND c.active=1 AND t.active=1 AND b.active=1 ORDER BY ta.period,c.name,d.name''',(u['teacher_id'],year,day.weekday()))
    holiday=one('SELECT name FROM holidays WHERE holiday_date=?',(day.isoformat(),))
    if holiday: st.info('Holiday: '+holiday['name']); schedule=schedule.iloc[:0]
    sessions=query('SELECT * FROM attendance_sessions WHERE teacher_id=? AND year_id=? AND attendance_date=? AND cancelled=0',(u['teacher_id'],year,day.isoformat()))
    done=0; states=[]; ids=[]
    for row in schedule.itertuples():
        found=sessions[(sessions.division_id==row.division_id)&(sessions.stream_id==row.stream_id)&(sessions.subject_id==row.subject_id)&(sessions.period==row.Period)]
        sid=int(found.iloc[0].id) if not found.empty else None
        done+=bool(sid); states.append('✅ Completed' if sid else '⏳ Pending'); ids.append(sid)
    schedule['Attendance']=states
    ui.cards([("Today's Classes",len(schedule),'Scheduled lectures today'),('Attendance Completed',done,'Scheduled lectures recorded'),('Attendance Pending',len(schedule)-done,'Ready for your class'),('Students in Assigned Classes',len(students(u,year,active_only=True)),'Active students')])
    st.subheader("Today's Schedule")
    if schedule.empty: st.info('No scheduled lectures today. You can take an assigned subject through Take Attendance.')
    for i,row in enumerate(schedule.itertuples()):
        with st.container(border=True):
            st.write(f'**Period {row.Period} · {row.Class} · {row.Subject}**'); st.caption(row.Stream+' · '+row.Attendance)
            if st.button('Open lecture',key=f'open_schedule_{row.id}'):
                if ids[i]: st.session_state.open_session=ids[i]
                else:
                    class_name,division=row.Class.rsplit('-', 1) if '-' in row.Class else (row.Class,'')
                    st.session_state.update(take_year=year,take_class=class_name,take_div=int(row.division_id),take_stream=int(row.stream_id),take_subject=int(row.subject_id),take_date=day,take_period=int(row.Period))
                ui.go('✅ Take Attendance')
    recent=history(u,{'year_id':year,'start':day-timedelta(days=14),'end':day},own_only=True)
    st.subheader('Recent Attendance'); ui.table(recent)
