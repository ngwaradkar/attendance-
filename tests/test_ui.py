import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_tmp=tempfile.TemporaryDirectory(); os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'ui.db')
from streamlit.testing.v1 import AppTest
from database.db import initialize
from utils.auth import login
from utils.helpers import today
APP=str(Path(__file__).resolve().parents[1]/'app.py')
ADMIN=['🏠 Dashboard','✅ Take Attendance',"📅 Today's Attendance",'👨‍🎓 Student Master','👨‍🏫 Teacher Master','📚 Academic Master','🔍 Student Search','📊 Attendance Reports','⚠️ Defaulter Report','📅 Attendance History','📥 Excel Import','📤 Excel Reports','📝 Audit Log','⚙️ Settings']
TEACHER=['🏠 My Dashboard','✅ Take Attendance','📅 My Attendance History','🔍 Student Search','📊 Reports']

class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'ui.db')
        initialize()
    def setUp(self):
        os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'ui.db')
    def assert_healthy(self,at):
        self.assertFalse(at.exception,[e.message for e in at.exception])
        self.assertFalse(at.error,[e.value for e in at.error])
    def open(self,role,page):
        at=AppTest.from_file(APP,default_timeout=30)
        at.session_state['user']=login(role,'admin123' if role=='admin' else 'teacher123')
        at.session_state['nav']=page
        at.run(); self.assert_healthy(at); return at
    def test_01_login(self):
        at=AppTest.from_file(APP,default_timeout=30).run(); self.assert_healthy(at)
        at.text_input[0].set_value('teacher1'); at.text_input[1].set_value('teacher123'); at.button[0].click().run(); self.assert_healthy(at)
        self.assertEqual(at.session_state.user['role'],'teacher')
    def test_02_admin_navigation(self):
        for page in ADMIN:
            with self.subTest(page=page): self.open('admin',page)
    def test_03_teacher_navigation(self):
        for page in TEACHER:
            with self.subTest(page=page): self.open('teacher1',page)
    def test_04_presentation(self):
        at=self.open('teacher1','✅ Take Attendance')
        at.selectbox(key='take_period').set_value(7).run(); self.assert_healthy(at)
        self.assertEqual(len(at.toggle),30)
        for toggle in at.toggle[:3]: toggle.set_value(False)
        next(b for b in at.button if b.label=='💾 Save Attendance').click().run(); self.assert_healthy(at)
        self.assertTrue(any('Attendance Saved Successfully' in s.value for s in at.success))
        self.assertEqual(next(r for r in at.radio if r.label=='Existing attendance').value,'View Existing Attendance')
        next(r for r in at.radio if r.label=='Existing attendance').set_value('Edit Attendance').run(); self.assert_healthy(at)
        at.toggle[0].set_value(True)
        next(t for t in at.text_input if t.label=='Reason for correction').set_value('Demo correction UI')
        next(b for b in at.button if b.label=='💾 Save Attendance').click().run(); self.assert_healthy(at)
        # Refresh dashboard and defaulter pages after the write.
        self.open('admin',"📅 Today's Attendance");self.open('admin','⚠️ Defaulter Report')
        history_at=self.open('teacher1','📅 My Attendance History')
        next(b for b in history_at.button if b.label=='✏️ Edit Attendance').click().run()
        self.assert_healthy(history_at)
        self.assertEqual(history_at.session_state.nav,'✅ Take Attendance')
    def test_05_reports_masters(self):
        at=self.open('admin','📊 Attendance Reports')
        for report in ['Subject-wise Attendance','Monthly Attendance Matrix']:
            next(r for r in at.radio if r.label=='Report type').set_value(report).run(); self.assert_healthy(at)
            if report.startswith('Monthly'):
                at.selectbox(key='report_'+report+'_div').set_value(1).run(); self.assert_healthy(at)
                self.assertGreater(len(at.dataframe),0)
        at=self.open('admin','📚 Academic Master')
        for name in ['Divisions','Streams','Subjects','Academic Years','Holidays']:
            at.selectbox[0].set_value(name).run(); self.assert_healthy(at)
    def test_06_pending_schedule_shortcut(self):
        from unittest.mock import patch
        from datetime import timedelta
        from views import dashboard
        day=today()
        while day.weekday()==6: day-=timedelta(days=1)
        with patch.object(dashboard,'today',return_value=day):
            at=self.open('teacher3','🏠 My Dashboard')
            next(b for b in at.button if b.label=='Open lecture').click().run()
            self.assert_healthy(at)
            self.assertEqual(at.session_state.nav,'✅ Take Attendance')
            self.assertEqual(len(at.toggle),30)
    def test_07_teacher_admin_guard(self):
        at=self.open('teacher1','👨‍🎓 Student Master')
        self.assertEqual(at.session_state.nav,'🏠 My Dashboard')

if __name__=='__main__': unittest.main(verbosity=2)
