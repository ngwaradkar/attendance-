import calendar
import pandas as pd
import streamlit as st
from database.db import settings
from utils import ui
from utils.calculations import student_report,monthly_records,history,students

def monthly_matrix(u,f):
    records=monthly_records(u,f)
    roster=students(u,f['year_id'],f.get('division_id'),f.get('stream_id'),True)[['student_id','Roll No','Student']]
    # Retain historical students even if they have since been deactivated.
    if not records.empty:
        roster=pd.concat([roster,records[['student_id','Roll No','Student']]]).drop_duplicates('student_id').sort_values('Roll No')
    result=roster.copy()
    for day in range(1,calendar.monthrange(f['start'].year,f['start'].month)[1]+1):
        date=f['start'].replace(day=day).isoformat()
        sub=records[records.Date==date] if not records.empty else records
        values=sub.groupby('student_id').Status.apply(lambda x:'/'.join(x)) if not sub.empty else pd.Series(dtype=str)
        result[str(day)]=result.student_id.map(values).fillna('-')
    report=student_report(u,f)[['student_id','Present','Absent','Attendance %']]
    result=result.merge(report,on='student_id',how='left')
    for col in ['Present','Absent']: result[col]=result[col].fillna(0).astype(int)
    # Unknown percentage is blank, rather than falsely reporting 0%.
    return result

def render():
    ui.title('📊 Attendance Reports','Lecture-based percentages · Holidays, cancelled lectures, and missing records are excluded.')
    kind=st.radio('Report type',['Class Attendance','Subject-wise Attendance','Monthly Attendance Matrix'],horizontal=True)
    f=ui.filters('report_'+kind,month=kind.startswith('Monthly'))
    if kind=='Monthly Attendance Matrix':
        st.caption('P = Present, A = Absent, – = no record. When a subject has multiple lectures on one day, P/A values appear in period order; totals count every lecture.')
        if not f.get('division_id'): st.info('Select a division for the monthly register.'); return
        data=monthly_matrix(ui.user(),f)
    else:
        data=student_report(ui.user(),f,kind=='Subject-wise Attendance')
        if not data.empty and kind=='Class Attendance':
            p=int(data.Present.sum()); n=int(data.Lectures.sum()); threshold=float(settings()['warning_threshold'])
            lectures=len(history(ui.user(),f))
            avg=f'{100*p/n:.2f}%' if n else '0.00%'
            ui.cards([('Total Lectures',lectures,'Distinct recorded sessions'),('Average Attendance',avg,'Weighted by lecture records'),('Highest Attendance',f"{data['Attendance %'].max():.2f}%",'Student percentage'),('Lowest Attendance',f"{data['Attendance %'].min():.2f}%",'Student percentage'),('Below Threshold',int((data['Attendance %']<threshold).sum()),f'Below {threshold}%')])
    ui.table(data)
    year=ui.master('academic_years').set_index('id').loc[f['year_id'],'name']
    ui.download(data,kind,'report_export',f"{f['start']} to {f['end']}",year)
