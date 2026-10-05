"""Run from this folder: streamlit run app.py."""
import html
import logging
import os
import sqlite3
from pathlib import Path
import streamlit as st
from database.db import initialize,settings,ROOT,connection,audit
from utils.auth import login,current_user
from utils import ui
from views import dashboard,take_attendance,today_attendance,students,teachers,academic_master,student_search,reports,defaulters,attendance_history,import_students,audit_log
from views import settings as settings_page

st.set_page_config(page_title='Vidya Prabodhini | Digital Attendance',page_icon='🎓',layout='wide',initial_sidebar_state='expanded')
logging.basicConfig(level=logging.INFO)

ADMIN_PAGES={'🏠 Dashboard':dashboard,'✅ Take Attendance':take_attendance,"📅 Today's Attendance":today_attendance,'👨‍🎓 Student Master':students,'👨‍🏫 Teacher Master':teachers,'📚 Academic Master':academic_master,'🔍 Student Search':student_search,'📊 Attendance Reports':reports,'⚠️ Defaulter Report':defaulters,'📅 Attendance History':attendance_history,'📥 Excel Import':import_students,'📤 Excel Reports':reports,'📝 Audit Log':audit_log,'⚙️ Settings':settings_page}
TEACHER_PAGES={'🏠 My Dashboard':dashboard,'✅ Take Attendance':take_attendance,'📅 My Attendance History':attendance_history,'🔍 Student Search':student_search,'📊 Reports':reports}

def header(cfg, compact=False):
    if compact:
        st.markdown(f'''<div class="hero-compact"><div class="brand-group"><div class="eyebrow">DIGITAL ATTENDANCE PORTAL</div><div class="brand">{html.escape(cfg['institution_name'].upper())}</div><div class="subtitle">{html.escape(cfg['institution_subtitle'])}</div></div><div class="meta-chips"><span class="chip">📅 Academic Year {html.escape(cfg['academic_year'])}</span><span class="chip live">● System Live</span></div></div>''',unsafe_allow_html=True)
    else:
        st.markdown(f'''<div class="hero"><div class="eyebrow">DIGITAL ATTENDANCE PORTAL</div><div class="brand">{html.escape(cfg['institution_name'].upper())}</div><div class="subtitle">Student Attendance Management System</div><div class="subtitle">{html.escape(cfg['institution_subtitle'])}</div><span class="tag">Academic Year {html.escape(cfg['academic_year'])}</span></div>''',unsafe_allow_html=True)

def login_screen(cfg):
    left,right=st.columns([1.3,1],gap='large')
    with left:
        header(cfg)
        st.subheader('A simpler school day starts here.')
        st.write('Replace paper registers with a clear, reliable classroom attendance workflow.')
        ui.cards([('✅ Mark in Seconds','Fast','Start with everyone Present'),('📊 See the Picture','Clear','Class and subject insights'),('📥 Reports to Excel','Ready','Share a formatted register')])
    with right:
        logo=ROOT/cfg['logo_path']
        if logo.is_file(): st.image(str(logo),width=100)
        st.subheader('Welcome back')
        st.caption('Sign in to your attendance workspace')
        with st.form('login'):
            username=st.text_input('Username',max_chars=100)
            password=st.text_input('Password',type='password')
            if st.form_submit_button('Login',type='primary',width='stretch'):
                from time import monotonic
                blocked=st.session_state.get('login_blocked_until',0)
                if monotonic()<blocked: st.error('Too many attempts. Please wait a minute and try again.')
                else:
                    u=login(username,password)
                    if u:
                        st.session_state.user=u; st.session_state.login_attempts=0; st.rerun()
                    else:
                        attempts=st.session_state.get('login_attempts',0)+1; st.session_state.login_attempts=attempts
                        if attempts>=5: st.session_state.login_blocked_until=monotonic()+60; st.session_state.login_attempts=0
                        st.error('Invalid username or password, or account disabled.')
        st.caption('Demo Application – Higher Secondary Section')
        if cfg['demo_mode']=='1':
            with st.expander('Demo Login Information'):
                st.info('DEMO accounts only. Change these passwords and disable demo mode before using real data.')
                st.code(f"Admin: {os.environ.get('DEMO_ADMIN_USERNAME','admin')} / {os.environ.get('DEMO_ADMIN_PASSWORD','admin123')}\nTeachers: teacher1 to teacher5 / {os.environ.get('DEMO_TEACHER_PASSWORD','teacher123')}",language=None)
                st.caption('teacher1 teaches Mathematics. Credentials shown are initial demo values; changed passwords are not displayed.')

def main():
    initialize(); cfg=settings()
    st.markdown('<style>'+(ROOT/'styles/custom.css').read_text()+'</style>',unsafe_allow_html=True)
    if not st.session_state.get('user'):
        login_screen(cfg)
    else:
        if st.session_state.user.get('auth_epoch')!=cfg.get('auth_epoch'):
            st.session_state.clear(); st.rerun()
        epoch=st.session_state.user['auth_epoch']
        u=current_user(st.session_state.user['id'])
        if not u:
            st.session_state.clear(); st.rerun()
        u['auth_epoch']=epoch
        st.session_state.user=u
        pages=ADMIN_PAGES if u['role']=='admin' else TEACHER_PAGES
        if '_next_nav' in st.session_state:
            st.session_state.nav=st.session_state.pop('_next_nav')
        if st.session_state.get('nav') not in pages: st.session_state.nav=next(iter(pages))
        with st.sidebar:
            logo=ROOT/cfg['logo_path']
            if logo.is_file(): st.image(str(logo),width=68)
            st.markdown(f'''<div style="margin-top:0.25rem;margin-bottom:0.6rem;"><div style="font-weight:800;font-size:1.12rem;color:#0f172a;letter-spacing:-0.01em;">{html.escape(cfg['institution_name'])}</div><div style="font-size:0.7rem;letter-spacing:0.12em;font-weight:750;color:#2563eb;">DIGITAL ATTENDANCE PORTAL</div></div>''',unsafe_allow_html=True)
            initial = u['name'][:1].upper() if u.get('name') else 'U'
            role_badge = 'admin' if u['role'] == 'admin' else 'teacher'
            st.markdown(f'''<div class="user-profile-badge"><div class="user-avatar-circle">{initial}</div><div class="user-info-text"><span class="user-name-title">{html.escape(u['name'])}</span><span class="user-role-pill {role_badge}">{html.escape(u['role'].upper())}</span></div></div>''',unsafe_allow_html=True)
            page=st.radio('Workspace Navigation',list(pages),key='nav',label_visibility='collapsed')
            st.divider()
            if st.button('🚪 Logout',width='stretch'):
                with connection() as conn: audit(conn,u,'Logout','User signed out')
                st.session_state.clear(); st.rerun()
        header(cfg, compact=True); pages[page].render()
    if cfg['demo_mode']=='1':
        st.markdown('<div class="footer">Demo Version – Student information shown in this application is fictional and is provided for demonstration purposes only.</div>',unsafe_allow_html=True)
    else: st.markdown('<div class="footer">Digital Attendance Portal · Simple • Fast • Paperless</div>',unsafe_allow_html=True)

if __name__=='__main__':
    try: main()
    except (PermissionError,ValueError) as exc: st.error(str(exc))
    except sqlite3.Error:
        logging.exception('Database operation failed'); st.error('The database could not complete this request. Please retry. If the problem persists, ask your administrator to check the database.')
    except Exception:
        logging.exception('Unexpected application error'); st.error('This page could not be loaded. Please refresh or ask your administrator to check the application logs.')
