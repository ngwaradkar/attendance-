import streamlit as st
from database.db import query,one
from utils import ui
from utils.calculations import history,session_records,can_edit,cancel_session

def render():
    ui.title('📅 Attendance History','View lecture rosters, make corrections, or cancel a lecture with an audit trail.')
    f=ui.filters('history'); u=ui.user()
    if u['role']=='admin': f['teacher_id']=ui.select('Teacher',ui.master('teachers'),'hist_teacher',True)
    data=history(u,f,own_only=u['role']=='teacher',include_cancelled=True)
    selected_rows=[]
    if data.empty:
        ui.table(data)
    else:
        event=st.dataframe(data.drop(columns=['session_id']),hide_index=True,width='stretch',on_select='rerun',selection_mode='single-row',key='history_grid')
        selected_rows=event.selection.rows
        st.caption('Click a lecture row to open its roster, or use the lecture selector below.')
    ui.download(data,'Attendance History','history_export',f"{f['start']} to {f['end']}")
    if data.empty: return
    lookup={r.session_id:f'{r.Date} · {r.Class} · {r.Subject} · Period {r.Period}' for r in data.itertuples()}
    if selected_rows and selected_rows[0]<len(data):
        sid=int(data.iloc[selected_rows[0]].session_id)
        st.write('**Selected lecture:** '+lookup[sid])
    else:
        sid=st.selectbox('Open lecture',list(lookup),format_func=lambda v:lookup[v])
    roster=session_records(u,sid); ui.table(roster)
    session=one('SELECT * FROM attendance_sessions WHERE id=?',(sid,))
    if can_edit(u,session):
        if st.button('✏️ Edit Attendance',disabled=bool(session['cancelled'])):
            st.session_state.open_session=sid; ui.go('✅ Take Attendance')
        with st.expander('Cancel / restore lecture'):
            st.caption('Cancelled lectures remain in history and are excluded from all attendance calculations.')
            reason=st.text_input('Reason',key='cancel_reason')
            if st.button('Restore lecture' if session['cancelled'] else 'Cancel lecture'):
                try: cancel_session(u,sid,not session['cancelled'],reason); st.rerun()
                except (ValueError,PermissionError) as exc: st.error(str(exc))
    changes=query('''SELECT ch.changed_at AS Timestamp,s.name AS Student,ch.original_status AS Original,ch.updated_status AS Updated,u.username AS "Changed By",ch.reason AS Reason FROM attendance_changes ch JOIN attendance_records r ON r.id=ch.record_id JOIN students s ON s.id=r.student_id JOIN users u ON u.id=ch.changed_by WHERE r.session_id=? ORDER BY ch.id DESC''',(sid,))
    if not changes.empty:
        st.subheader('Correction audit trail'); ui.table(changes)
