import hashlib
import pandas as pd
import streamlit as st
from utils import ui
from utils.auth import require_admin
from utils.validators import REQUIRED,validate_upload
from utils.admin import import_valid

def render():
    require_admin(ui.user()); ui.title('📥 Import Students','Validate an Excel workbook, review every row, then confirm the import.')
    st.code(' | '.join(REQUIRED),language=None)
    st.caption('Roll No must be a positive integer. Class and division must exist in Academic Master. GR numbers must be unique. Format mobile columns as Text to retain leading zeroes. Optional: Gender and Student Mobile.')
    template=pd.DataFrame([{'Roll No':31,'GR No':'DEMO-NEW-031','Student Name':'Demo New Learner','Class':'XI','Division':'A','Stream':'Science','Parent Name':'Demo Guardian','Mobile':'0000000000'}])
    ui.download(template,'Student Import Template','template_export')
    year=ui.select('Academic Year',ui.master('academic_years'),'import_year')
    file=st.file_uploader('Upload student workbook (.xlsx)',type=['xlsx'])
    if not file or not year: return
    content=file.getvalue(); token=hashlib.sha256(content+str(year).encode()).hexdigest()
    if st.session_state.get('last_import')==token:
        st.info('This workbook has already been processed in this session. Change the file to import new rows.'); return
    try: valid,preview=validate_upload(content,year)
    except ValueError as exc: st.error(str(exc)); return
    st.subheader('Validation Preview'); ui.table(preview)
    counts=preview.Validation.value_counts() if not preview.empty else {}
    bad=int(counts.get('Failed',0)); dup=int(counts.get('Duplicate',0))
    ui.cards([('Valid Rows',len(valid),'Ready to import'),('Failed',bad,'Fix invalid rows'),('Duplicates',dup,'Skipped')])
    ui.download(preview,'Import Validation Results','validation_export')
    confirm=st.checkbox(f'I confirm importing {len(valid)} valid student rows. Invalid and duplicate rows will be skipped.',key='confirm_'+token)
    if st.button('Import Valid Rows',type='primary',disabled=not confirm or not valid):
        success,failed,duplicates=import_valid(ui.user(),valid)
        st.session_state.last_import=token
        st.success(f'Successful: {success} · Failed: {failed+bad} · Duplicates: {duplicates+dup}')
