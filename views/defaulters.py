import streamlit as st
from database.db import settings
from utils import ui
from utils.calculations import student_report

def render():
    ui.title('⚠️ Attendance Defaulters','Identify students who need attendance support.')
    f=ui.filters('defaulter',month=True)
    threshold=st.number_input('Attendance threshold (%)',0.0,100.0,float(settings()['warning_threshold']),step=1.0)
    data=student_report(ui.user(),f)
    if not data.empty:
        data=data[data['Attendance %']<threshold].copy()
        critical=float(settings()['critical_threshold'])
        data['Indicator']=data['Attendance %'].apply(lambda v:'🔴 Below '+str(critical)+'%' if v<critical else '🟠 Below threshold')
    ui.table(data); ui.download(data,'Defaulter Report','defaulters_export',f"{f['start']} to {f['end']}")
