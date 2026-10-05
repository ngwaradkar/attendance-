import streamlit as st
import plotly.express as px
from utils import ui
from utils.calculations import students,student_report,aggregate

def render():
    ui.title('🔍 Student Attendance Profile','Search by student name, roll number, or GR number.')
    f=ui.filters('profile')
    roster=students(ui.user(),f['year_id'],f.get('division_id'),f.get('stream_id'),class_id=f.get('class_id'))
    search=st.text_input('Search student').strip()
    if search:
        roster=roster[roster.Student.str.contains(search,case=False,regex=False,na=False)|roster['GR No'].str.contains(search,case=False,regex=False,na=False)|(roster['Roll No'].astype(str)==search)]
    if roster.empty: st.info('No students found.'); return
    choices=roster.student_id.tolist(); labels={r.student_id:f'{r.Student} · {r._2}' for r in roster.itertuples()}
    sid=st.selectbox('Select student',choices,format_func=lambda v:labels[v])
    row=roster[roster.student_id==sid].iloc[0]
    st.subheader(row.Student); st.write(f"Roll {row['Roll No']} · GR {row['GR No']} · {row.Class}-{row.Division} · {row.Stream}")
    f['student_id']=sid; report=student_report(ui.user(),f)
    if report.empty: st.info('This student has no recorded lectures in this period.'); return
    value=report.iloc[0]; ui.cards([('Total Lectures',int(value.Lectures),'Recorded lectures only'),('Present',int(value.Present),'Lectures attended'),('Absent',int(value.Absent),'Marked absent'),('Attendance %',str(value['Attendance %'])+'%','Selected date range')])
    data=aggregate(ui.user(),f); data['Month']=data.Date.str[:7]
    monthly=data.groupby('Month',as_index=False)[['Present','Absent']].sum(); monthly['Attendance %']=100*monthly.Present/(monthly.Present+monthly.Absent)
    st.plotly_chart(px.line(monthly,x='Month',y='Attendance %',markers=True).update_layout(yaxis_range=[0,100]),width='stretch')
    st.subheader('Subject-wise Attendance'); subject=student_report(ui.user(),f,True); ui.table(subject); ui.download(subject,'Student Attendance Profile','student_profile_export',f"{f['start']} to {f['end']}")
