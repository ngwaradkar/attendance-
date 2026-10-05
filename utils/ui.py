import html
import streamlit as st
from database.db import query,settings
from utils.helpers import today
from utils.excel_export import excel_bytes

def user(): return st.session_state.user

def title(name,description=''):
    st.title(name)
    if description: st.caption(description)

def cards(items):
    columns=st.columns(min(len(items),3))
    for i,(label,value,detail) in enumerate(items):
        with columns[i%len(columns)]:
            accent=f'kpi-accent-{i%4}'
            st.markdown(f'<div class="kpi {accent}"><div class="kpi-label">{html.escape(str(label))}</div><div class="kpi-value">{html.escape(str(value))}</div><div class="kpi-detail">{html.escape(str(detail))}</div></div>',unsafe_allow_html=True)

def table(df):
    visible=df.drop(columns=[c for c in ['student_id','division_id','stream_id','year_id','session_id'] if c in df],errors='ignore')
    if visible.empty: st.info('No attendance records match these filters. Missing records are not counted as absences.')
    else:
        if 'Attendance %' in visible:
            st.dataframe(visible.style.map(lambda v:'background-color: #fee2e2; color:#991b1b' if v<float(settings()['warning_threshold']) else '',subset=['Attendance %']),hide_index=True,width='stretch')
        else: st.dataframe(visible,hide_index=True,width='stretch')

def download(df,title,key,date_range='All available records',year=None):
    cfg=settings()
    st.download_button('📥 Download '+title+' – Excel',excel_bytes(df,title,cfg['institution_name'],year or cfg['academic_year'],date_range,threshold=float(cfg['warning_threshold'])),file_name=title.lower().replace(' ','_')+'.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=key)

@st.cache_data(ttl=300)
def master(table_name):
    allowed={'academic_years','classes','streams','subjects','teachers'}
    if table_name not in allowed: raise ValueError('Unknown master')
    return query(f'SELECT id,name FROM {table_name} WHERE active=1 ORDER BY id')

def clear_master_cache(): master.clear()

def select(label,frame,key,all_option=False,default=None):
    if frame.empty:
        st.warning(f'No {label.lower()} available.'); return None
    choices=frame['id'].astype(int).tolist(); labels=dict(zip(choices,frame['name']))
    if all_option: choices=[None]+choices; labels[None]='All'
    index=choices.index(default) if default in choices else 0
    return st.selectbox(label,choices,format_func=lambda v:labels[v],index=index,key=key)

def scope_options(u):
    sql='''SELECT DISTINCT ta.year_id,ta.division_id,ta.stream_id,ta.subject_id,c.id AS class_id,c.name AS class_name,d.name AS division_name,t.name AS stream_name,b.name AS subject_name FROM teacher_assignments ta JOIN divisions d ON d.id=ta.division_id JOIN classes c ON c.id=d.class_id JOIN streams t ON t.id=ta.stream_id JOIN subjects b ON b.id=ta.subject_id JOIN academic_years y ON y.id=ta.year_id WHERE ta.active=1 AND d.active=1 AND c.active=1 AND t.active=1 AND b.active=1 AND y.active=1'''
    if u['role']=='teacher': return query(sql+' AND ta.teacher_id=?',(u['teacher_id'],))
    return query('''SELECT y.id AS year_id,d.id AS division_id,t.id AS stream_id,b.id AS subject_id,c.id AS class_id,c.name AS class_name,d.name AS division_name,t.name AS stream_name,b.name AS subject_name FROM divisions d JOIN classes c ON c.id=d.class_id CROSS JOIN streams t CROSS JOIN subjects b CROSS JOIN academic_years y WHERE d.active=1 AND c.active=1 AND t.active=1 AND b.active=1 AND y.active=1''')

def filters(prefix,dates=True,all_option=True,month=False):
    u=user(); opts=scope_options(u); cfg=settings(); result={}
    years=master('academic_years'); default=next((r.id for r in years.itertuples() if r.name==cfg['academic_year']),None)
    c=st.columns(3)
    with c[0]: result['year_id']=select('Academic Year',years,prefix+'_year',default=default)
    scoped=opts[opts.year_id==result['year_id']] if not opts.empty else opts
    with c[1]:
        names=sorted(scoped.class_name.unique()) if not scoped.empty else []
        cls=st.selectbox('Class',(['All'] if all_option else [])+names,key=prefix+'_class') if names else None
    if cls and cls!='All':
        scoped=scoped[scoped.class_name==cls]
        result['class_id']=int(scoped.class_id.iloc[0]) if not scoped.empty else None
    divs=scoped[['division_id','division_name','class_name']].drop_duplicates() if not scoped.empty else None
    with c[2]:
        if divs is not None:
            df=divs.assign(name=divs.class_name+'-'+divs.division_name).rename(columns={'division_id':'id'})
            result['division_id']=select('Division',df,prefix+'_div',all_option)
        else: result['division_id']=None
    if result['division_id']: scoped=scoped[scoped.division_id==result['division_id']]
    c=st.columns(3)
    with c[0]: result['stream_id']=select('Stream',scoped[['stream_id','stream_name']].drop_duplicates().rename(columns={'stream_id':'id','stream_name':'name'}),prefix+'_stream',all_option) if not scoped.empty else None
    if result['stream_id']: scoped=scoped[scoped.stream_id==result['stream_id']]
    with c[1]: result['subject_id']=select('Subject',scoped[['subject_id','subject_name']].drop_duplicates().rename(columns={'subject_id':'id','subject_name':'name'}),prefix+'_subject',all_option) if not scoped.empty else None
    if dates:
        with c[2]:
            if month:
                day=st.date_input('Month (choose any day)',today(),key=prefix+'_month')
                from utils.helpers import month_bounds
                result['start'],result['end']=month_bounds(day)
            else:
                from datetime import timedelta
                period=st.date_input('Date range',(today()-timedelta(days=30),today()),key=prefix+'_range')
                if len(period)==2: result['start'],result['end']=period
                else: st.info('Select an end date.'); st.stop()
    return result

def go(page):
    st.session_state['_next_nav']=page; st.rerun()
