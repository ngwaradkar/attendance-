import streamlit as st
from database.db import settings
from utils import ui
from utils.helpers import today
from utils.calculations import aggregate,daily_absent,students

def render():
    ui.title("📅 Today's Attendance Monitor",'Management view of recorded lectures and absent students.')
    f=ui.filters('today',dates=False)
    day=st.date_input('Attendance date',today(),max_value=today())
    f.update(start=day,end=day)
    cfg=settings(); data=aggregate(ui.user(),f,'class')
    enrolled=students(ui.user(),f['year_id'],f.get('division_id'),f.get('stream_id'),True,f.get('class_id'))
    if not enrolled.empty:
        enrolled=enrolled.assign(Class=enrolled.Class+'-'+enrolled.Division).groupby('Class',as_index=False).agg(Enrolled=('student_id','count'))
        data=enrolled.merge(data,on='Class',how='outer')
        for col in ['Lecture Records','Present','Absent']: data[col]=data[col].fillna(0).astype(int)
    if not data.empty:
        data=data.rename(columns={'Lecture Records':'Total'})
        data['Status']=data['Attendance %'].apply(lambda v:'⚪ No Record' if v!=v else ('🟢 Good' if v>=float(cfg['good_threshold']) else ('🟠 Attention' if v>=float(cfg['warning_threshold']) else '🔴 Low')))
        data['Division']=data.Class.str.rsplit('-',n=1).str[-1]; data['Class']=data.Class.str.rsplit('-',n=1).str[0]
    st.caption('Total, Present, and Absent count student-lecture records, aggregated across the selected periods. Unrecorded classes do not imply zero attendance.')
    ui.table(data); ui.download(data,'Daily Attendance','daily_export',str(day))
    st.subheader("Today's Absent Students")
    absent=daily_absent(ui.user(),f); ui.table(absent); ui.download(absent,'Absent Students','absent_export',str(day))
    if not absent.empty:
        summaries=[]
        for (cls,div),group in absent.groupby(['Class','Division']):
            summaries.append(f"Absent students in {cls}-{div} on {day.strftime('%d-%b-%Y')}: {', '.join(group.Student)}.")
        st.text_area('Copyable summary','\n\n'.join(summaries),height=150)
    st.button('Parent Notification Integration – Future Enhancement',disabled=True)
