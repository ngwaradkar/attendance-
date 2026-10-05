import sqlite3
import streamlit as st
from database.db import query,connection,audit
from utils import ui
from utils.auth import require_admin
from utils.admin import save_master
from utils.helpers import today

def render():
    u=ui.user(); require_admin(u); ui.title('📚 Academic Master','Classes, divisions, streams, subjects, academic years, and holidays are configurable.')
    selected=st.selectbox('Master',['Classes','Divisions','Streams','Subjects','Academic Years','Holidays'])
    if selected=='Holidays': holidays(u); return
    table={'Classes':'classes','Divisions':'divisions','Streams':'streams','Subjects':'subjects','Academic Years':'academic_years'}[selected]
    data=query(f'SELECT * FROM {table} ORDER BY id'); ui.table(data)
    mode=st.radio('Action',['Create','Edit'],horizontal=True,key='master_mode_'+table)
    rid=None; old=None
    if mode=='Edit' and not data.empty:
        rid=st.selectbox('Record',data.id.tolist(),format_func=lambda v:str(data.set_index('id').loc[v,'name']),key='master_record_'+table)
        old=data[data.id==rid].iloc[0]
    with st.form('master_form_'+table+str(rid)):
        name=st.text_input('Name',value=old['name'] if old is not None else '')
        active=st.checkbox('Enabled',value=bool(old.active) if old is not None else True)
        cls=None
        if table=='divisions': cls=ui.select('Class',ui.master('classes'),'master_div_class',default=int(old.class_id) if old is not None else None)
        if st.form_submit_button('Save Master',type='primary'):
            try:
                if table=='divisions' and cls is None: raise ValueError('Create an enabled class first.')
                if table=='academic_years' and rid:
                    from database.db import settings
                    if settings()['academic_year']==old['name'] and (not active or name.strip()!=old['name']): raise ValueError('Change the current academic year in Settings before renaming or disabling it.')
                save_master(u,table,name,active,rid,cls); ui.clear_master_cache(); st.rerun()
            except ValueError as exc: st.error(str(exc))
    if table=='divisions': st.caption('To place a division under a different class, create a new division. Existing history retains its original class.')

def holidays(u):
    data=query('SELECT holiday_date AS Date,name AS Holiday,description AS Description FROM holidays ORDER BY holiday_date'); ui.table(data)
    st.caption('Holiday dates are excluded from attendance calculations, including any previously saved lectures. Attendance entry is blocked on these dates.')
    with st.form('holiday_form'):
        day=st.date_input('Holiday Date',today()); name=st.text_input('Holiday Name'); description=st.text_area('Description')
        if st.form_submit_button('Save Holiday'):
            if not name.strip(): st.error('Enter a holiday name.')
            else:
                with connection() as conn:
                    conn.execute('INSERT INTO holidays(holiday_date,name,description) VALUES(?,?,?) ON CONFLICT(holiday_date) DO UPDATE SET name=excluded.name,description=excluded.description',(day.isoformat(),name.strip(),description.strip())); audit(conn,u,'Holiday saved',f'{day}: {name}')
                st.rerun()
    if not data.empty:
        remove=st.selectbox('Remove holiday',data.Date.tolist())
        if st.button('Remove selected holiday'):
            with connection() as conn:
                conn.execute('DELETE FROM holidays WHERE holiday_date=?',(remove,)); audit(conn,u,'Holiday removed',remove)
            st.rerun()
