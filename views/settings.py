from pathlib import Path
import streamlit as st
from database.db import settings,query,connection,audit,ROOT
from database.seed_data import seed
from utils import ui
from utils.auth import require_admin,hash_password,verify_password

def render():
    u=ui.user(); require_admin(u); cfg=settings(); ui.title('⚙️ Settings & About','Institution identity, academic year, thresholds, and demo controls.')
    with st.form('settings_form'):
        name=st.text_input('Institution Name',cfg['institution_name'])
        subtitle=st.text_input('Institution Subtitle',cfg['institution_subtitle'])
        years=ui.master('academic_years'); current=next((int(r.id) for r in years.itertuples() if r.name==cfg['academic_year']),None)
        year=ui.select('Current Academic Year',years,'settings_year',default=current)
        good=st.number_input('Good attendance threshold (%)',0.0,100.0,float(cfg['good_threshold']))
        warning=st.number_input('Attendance Warning Threshold (%)',0.0,100.0,float(cfg['warning_threshold']))
        critical=st.number_input('Attendance Critical Threshold (%)',0.0,100.0,float(cfg['critical_threshold']))
        periods=st.number_input('Number of Periods',1,12,int(cfg['periods']))
        demo=st.checkbox('Enable demo mode (show demo account information)',value=cfg['demo_mode']=='1')
        logo=st.text_input('Logo path (relative to project folder)',cfg['logo_path'])
        if st.form_submit_button('Save Settings',type='primary'):
            if not name.strip() or not year: st.error('Institution name and academic year are required.')
            elif not 0<=critical<warning<=good<=100: st.error('Thresholds must follow Critical < Warning ≤ Good ≤ 100.')
            elif logo and (not (ROOT/logo).is_file() or (ROOT/logo).suffix.lower() not in ['.png','.jpg','.jpeg','.webp']): st.error('Use an existing PNG, JPG, or WebP logo file.')
            else:
                year_name=years.set_index('id').loc[year,'name']
                values={'institution_name':name.strip(),'institution_subtitle':subtitle.strip(),'academic_year':year_name,'warning_threshold':str(warning),'critical_threshold':str(critical),'good_threshold':str(good),'periods':str(periods),'demo_mode':'1' if demo else '0','logo_path':logo.strip()}
                with connection() as conn:
                    conn.executemany('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',values.items()); audit(conn,u,'Settings changed',str(values))
                st.rerun()
    st.info('Configure available classes, divisions, streams, subjects, and academic years in Academic Master. Disabling a master removes it from new attendance entry; past reports remain intact.')
    with st.expander('Change your administrator password'):
        with st.form('admin_password'):
            old=st.text_input('Current password',type='password'); new=st.text_input('New password',type='password'); repeat=st.text_input('Repeat new password',type='password')
            if st.form_submit_button('Update Password'):
                stored=query('SELECT password_hash FROM users WHERE id=?',(u['id'],)).iloc[0].password_hash
                if not verify_password(old,stored): st.error('Current password is incorrect.')
                elif len(new)<8 or new!=repeat: st.error('Use at least eight characters and matching confirmation.')
                else:
                    with connection() as conn:
                        conn.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new),u['id'])); audit(conn,u,'Password changed','Administrator password updated')
                    st.success('Password updated.')
    with st.expander('Reset Demo Database'):
        st.warning('This permanently removes all current records and restores fictional demo data. Back up your database before resetting.')
        confirmation=st.text_input('Type RESET DEMO to confirm')
        confirmed=st.checkbox('I understand all current attendance and master data will be removed.')
        if st.button('Reset Demo Database',disabled=cfg['demo_mode']!='1' or confirmation!='RESET DEMO' or not confirmed):
            # Delete in dependency order in one transaction; never unlink a live database.
            with connection() as conn:
                conn.execute('BEGIN IMMEDIATE')
                for table in ['attendance_changes','attendance_records','attendance_sessions','audit_logs','teacher_assignments','students','teachers','users','holidays','subjects','streams','divisions','classes','academic_years','settings']:
                    conn.execute(f'DELETE FROM {table}')
                seed(conn)
            ui.clear_master_cache(); st.session_state.clear(); st.rerun()
    st.subheader('Future Enhancements')
    st.write('QR attendance · RFID / ID cards · Biometric integration · Parent SMS and WhatsApp notifications · Student and parent portals · Timetable integration · Examination module · Leave management · Late-entry management · Cloud database · Automated attendance alerts · Student ID cards')
    st.caption('Future Enhancements only. No external or paid notification service is connected.')
    st.caption('Demo Version – Student information shown in this application is fictional and is provided for demonstration purposes only.')
