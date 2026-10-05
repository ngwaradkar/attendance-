import streamlit as st
from database.db import query
from utils import ui
from utils.auth import require_admin
from utils.calculations import students
from utils.admin import save_student

def render():
    u=ui.user(); require_admin(u); ui.title('👨‍🎓 Student Master','Create, update, or deactivate student enrollments. Historical attendance stays available.')
    f=ui.filters('students',dates=False); roster=students(u,f['year_id'],f.get('division_id'),f.get('stream_id'),class_id=f.get('class_id'))
    search=st.text_input('Filter student master')
    if search: roster=roster[roster.Student.str.contains(search,case=False,regex=False,na=False)|roster['GR No'].str.contains(search,case=False,regex=False,na=False)]
    ui.table(roster); ui.download(roster,'Student Master','student_master_export')
    mode=st.radio('Manage student',['Add Student','Edit Student'],horizontal=True)
    old=None; sid=None
    if mode=='Edit Student':
        if roster.empty: return
        labels={r.student_id:r.Student for r in roster.itertuples()}
        sid=st.selectbox('Student to edit',list(labels),format_func=lambda v:labels[v]); old=roster[roster.student_id==sid].iloc[0]
    suffix=str(sid or 'new')
    with st.form('student_form_'+suffix):
        c=st.columns(2)
        with c[0]:
            name=st.text_input('Student Name',value=old.Student if old is not None else '')
            roll=st.number_input('Roll Number',min_value=1,value=int(old['Roll No']) if old is not None else 31,step=1)
            gr=st.text_input('GR Number',value=old['GR No'] if old is not None else '')
            genders=['Not specified','Female','Male','Other']; gender=st.selectbox('Gender',genders,index=genders.index(old.Gender) if old is not None and old.Gender in genders else 0)
            years=ui.master('academic_years'); year=ui.select('Academic Year',years,'student_year_'+suffix,default=int(old.year_id) if old is not None else f['year_id'])
            divs=query("SELECT d.id,c.name||'-'||d.name AS name FROM divisions d JOIN classes c ON c.id=d.class_id WHERE d.active=1 AND c.active=1")
            div=ui.select('Class / Division',divs,'student_div_'+suffix,default=int(old.division_id) if old is not None else f.get('division_id'))
        with c[1]:
            stream=ui.select('Stream',ui.master('streams'),'student_stream_'+suffix,default=int(old.stream_id) if old is not None else f.get('stream_id'))
            parent=st.text_input('Parent/Guardian Name',value=old['Parent Name'] if old is not None else '')
            pm=st.text_input('Parent Mobile Number',value=old['Parent Mobile'] if old is not None else '')
            sm=st.text_input('Student Mobile Number',value=old['Student Mobile'] if old is not None else '')
            active=st.checkbox('Active',value=bool(old.Active) if old is not None else True)
        if st.form_submit_button('Save Student',type='primary'):
            try:
                save_student(u,dict(name=name,roll_no=roll,gr_no=gr,gender=gender,division_id=div,stream_id=stream,year_id=year,parent_name=parent,parent_mobile=pm,student_mobile=sm,active=active),sid)
                st.success('Student saved successfully.'); st.rerun()
            except (ValueError,TypeError) as exc: st.error(str(exc))
