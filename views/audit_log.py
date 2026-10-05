from datetime import timedelta
import streamlit as st
from database.db import query
from utils import ui
from utils.auth import require_admin
from utils.helpers import today

def render():
    require_admin(ui.user()); ui.title('📝 Audit Log','Login, attendance, student, and configuration activity.')
    dates=st.date_input('Log date range',(today()-timedelta(days=30),today()))
    if len(dates)!=2: return
    actions=query('SELECT DISTINCT action AS name FROM audit_logs ORDER BY action').name.tolist()
    action=st.selectbox('Action',['All']+actions)
    page=st.number_input('Page (200 entries per page)',1,value=1)
    sql='SELECT timestamp AS Timestamp,username AS Username,action AS Action,details AS Details FROM audit_logs WHERE substr(timestamp,1,10) BETWEEN ? AND ?'; params=[str(dates[0]),str(dates[1])]
    if action!='All': sql+=' AND action=?'; params.append(action)
    total=query('SELECT COUNT(*) AS n FROM ('+sql+')',params).iloc[0].n
    st.caption(f'{total} matching events')
    data=query(sql+' ORDER BY Timestamp DESC LIMIT 200 OFFSET ?',params+[(page-1)*200]); ui.table(data); ui.download(data,'Audit Log','audit_export',f'{dates[0]} to {dates[1]}')
