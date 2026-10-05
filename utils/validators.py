import re
import zipfile
from io import BytesIO
import pandas as pd
from database.db import query

REQUIRED=['Roll No','GR No','Student Name','Class','Division','Stream','Parent Name','Mobile']

def text(value):
    if pd.isna(value): return ''
    if isinstance(value,float) and value.is_integer(): return str(int(value))
    return str(value).strip()

def mobile(value):
    value=text(value)
    if value and not re.fullmatch(r'[0-9+ ()-]{7,20}',value): raise ValueError('Mobile must contain 7–20 phone characters or be blank.')
    return value

def student_values(data):
    name=text(data.get('name')); gr=text(data.get('gr_no'))
    if any(data.get(k) is None for k in ['year_id','division_id','stream_id']):
        raise ValueError('Select an available academic year, class/division, and stream.')
    if not name or len(name)>150: raise ValueError('Student name is required (maximum 150 characters).')
    if not gr or len(gr)>50: raise ValueError('GR number is required (maximum 50 characters).')
    try:
        roll=int(data['roll_no'])
        if float(data['roll_no'])!=roll or roll<1: raise ValueError()
    except (ValueError,TypeError): raise ValueError('Roll number must be a positive whole number.')
    return {'roll_no':roll,'gr_no':gr,'name':name,'gender':text(data.get('gender','Not specified')),'division_id':int(data['division_id']),'stream_id':int(data['stream_id']),'year_id':int(data['year_id']),'parent_name':text(data.get('parent_name')),'parent_mobile':mobile(data.get('parent_mobile')),'student_mobile':mobile(data.get('student_mobile')),'active':int(data.get('active',1))}

def validate_upload(content,year_id):
    if len(content)>10*1024*1024: raise ValueError('Excel file exceeds the 10 MB upload limit.')
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            if sum(x.file_size for x in archive.infolist())>50*1024*1024: raise ValueError('Excel workbook expands beyond the safe size limit.')
        frame=pd.read_excel(BytesIO(content),engine='openpyxl',dtype=str,keep_default_na=False)
    except ValueError: raise
    except Exception as exc: raise ValueError('The uploaded file is not a readable .xlsx workbook.') from exc
    frame.columns=[str(c).strip() for c in frame.columns]
    header_row=0
    if 'Roll No' not in frame.columns and len(frame)>=5:
        # The app's branded exports place the real column header on Excel row 6.
        candidate=pd.read_excel(BytesIO(content),engine='openpyxl',header=5,dtype=str,keep_default_na=False)
        candidate.columns=[str(c).strip() for c in candidate.columns]
        if 'Roll No' in candidate.columns:
            frame=candidate; header_row=5
    frame=frame.rename(columns={'Student':'Student Name','Parent Mobile':'Mobile'})
    missing=[c for c in REQUIRED if c not in frame]
    if missing: raise ValueError('Uploaded Excel file is missing required columns: '+', '.join(missing))
    if len(frame)>10000: raise ValueError('Please import at most 10,000 students per workbook.')
    divisions=query('SELECT d.id,c.name AS class_name,d.name FROM divisions d JOIN classes c ON c.id=d.class_id WHERE d.active=1 AND c.active=1')
    div_map={(r.class_name.strip().upper(),r.name.strip().upper()):r.id for r in divisions.itertuples()}
    stream_map={r.name.lower():r.id for r in query('SELECT id,name FROM streams WHERE active=1').itertuples()}
    used_gr=set(query('SELECT gr_no FROM students').gr_no.str.casefold())
    used_roll=set(query('SELECT division_id,stream_id,roll_no FROM students WHERE year_id=?',(year_id,)).itertuples(index=False,name=None))
    valid=[]; result=[]
    for index,row in frame.iterrows():
        display={c:row[c] for c in REQUIRED}; status='Valid'; error=''
        try:
            gr=text(row['GR No']); cls=text(row['Class']).upper().replace('CLASS ',''); div=text(row['Division']).upper()
            if div.startswith(cls+'-'): div=div[len(cls)+1:]
            if gr.casefold() in used_gr:
                status='Duplicate'; raise ValueError('Duplicate GR number in database or workbook.')
            if (cls,div) not in div_map: raise ValueError('Class/division is not enabled in Academic Master.')
            stream=text(row['Stream']).lower()
            if stream not in stream_map: raise ValueError('Stream is not enabled in Academic Master.')
            data=student_values({'roll_no':row['Roll No'],'gr_no':gr,'name':row['Student Name'],'division_id':div_map[(cls,div)],'stream_id':stream_map[stream],'year_id':year_id,'parent_name':row['Parent Name'],'parent_mobile':row['Mobile'],'gender':row.get('Gender','Not specified'),'student_mobile':row.get('Student Mobile','')})
            roll_key=(data['division_id'],data['stream_id'],data['roll_no'])
            if roll_key in used_roll:
                status='Duplicate'; raise ValueError('Duplicate roll number in this year/division/stream.')
            valid.append(data); used_gr.add(gr.casefold()); used_roll.add(roll_key)
        except (ValueError,TypeError) as exc:
            if status!='Duplicate': status='Failed'
            error=str(exc)
        result.append({'Excel Row':index+2+header_row,**display,'Validation':status,'Details':error})
    return valid,pd.DataFrame(result)
