"""Integration checks on a disposable database; never touches the demo database."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_tmp=tempfile.TemporaryDirectory()
os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'test.db')
from database.db import initialize,query,one,connection
from utils.auth import login
from utils.calculations import *
from utils.validators import validate_upload
from utils.admin import import_valid
from utils.excel_export import excel_bytes
from openpyxl import load_workbook
from utils.helpers import today
import pandas as pd

class SystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'test.db')
        initialize(); cls.admin=login('admin','admin123'); cls.teacher=login('teacher1','teacher123')
    def setUp(self):
        os.environ['ATTENDANCE_DB_PATH']=str(Path(_tmp.name)/'test.db')
    def test_01_seed(self):
        self.assertEqual(int(query('SELECT COUNT(*) AS n FROM students').iloc[0].n),120)
        self.assertEqual(int(query('SELECT COUNT(*) AS n FROM teachers').iloc[0].n),5)
        self.assertGreater(int(query('SELECT COUNT(*) AS n FROM attendance_records').iloc[0].n),10000)
        self.assertIsNone(login('admin','incorrect'))
        self.assertNotIn('password_hash',self.admin)
    def test_02_attendance_correction(self):
        key={'attendance_date':today().isoformat(),'year_id':1,'division_id':1,'stream_id':1,'subject_id':2,'teacher_id':1,'period':8}
        roster=students(self.teacher,1,1,1,True); statuses={int(s):'P' for s in roster.student_id}; ids=list(statuses)
        for sid in ids[:3]: statuses[sid]='A'
        session_id=save_attendance(self.teacher,key,statuses)
        self.assertEqual(one("SELECT COUNT(*) AS n FROM attendance_records WHERE session_id=? AND status='A'",(session_id,))['n'],3)
        with self.assertRaises(ValueError): save_attendance(self.teacher,key,statuses)
        teacher2=login('teacher2','teacher123')
        with self.assertRaises(PermissionError): save_attendance(teacher2,key,statuses,True,'bad','Test')
        session=existing_session(key); statuses[ids[0]]='P'
        save_attendance(self.teacher,key,statuses,True,session['updated_at'],'Demo correction')
        self.assertEqual(one('SELECT COUNT(*) AS n FROM attendance_changes')['n'],1)
        with self.assertRaises(ValueError): save_attendance(self.teacher,key,statuses,True,session['updated_at'],'Stale edit')
        report=student_report(self.teacher,{'year_id':1,'start':today(),'end':today(),'subject_id':2})
        self.assertFalse(report.empty)
        cancel_session(self.teacher,session_id,True,'Cancelled for testing')
        self.assertNotIn(session_id,history(self.teacher,{'start':today(),'end':today()}).session_id.tolist())
        cancel_session(self.teacher,session_id,False,'Restore')
    def test_03_holiday_missing(self):
        before=student_report(self.admin,{'year_id':1,'start':today(),'end':today()})
        with connection() as conn: conn.execute('INSERT INTO holidays(holiday_date,name) VALUES(?,?)',(today().isoformat(),'Test Holiday'))
        self.assertTrue(student_report(self.admin,{'start':today(),'end':today()}).empty)
        with connection() as conn: conn.execute('DELETE FROM holidays WHERE holiday_date=?',(today().isoformat(),))
        self.assertFalse(before.empty)
        self.assertTrue(student_report(self.admin,{'start':'2000-01-01','end':'2000-01-02'}).empty)
    def test_04_import_export(self):
        frame=pd.DataFrame([{'Roll No':99,'GR No':'TEST-NEW','Student Name':'Demo Import','Class':'XI','Division':'A','Stream':'Science','Parent Name':'Demo Parent','Mobile':'0000000000'}, {'Roll No':98,'GR No':'DEMO-1-001','Student Name':'Duplicate','Class':'XI','Division':'A','Stream':'Science','Parent Name':'Demo','Mobile':''}])
        raw=BytesIO();frame.to_excel(raw,index=False)
        valid,preview=validate_upload(raw.getvalue(),1); self.assertEqual(len(valid),1); self.assertEqual((preview.Validation=='Duplicate').sum(),1)
        self.assertEqual(import_valid(self.admin,valid),(1,0,0))
        branded=excel_bytes(frame,'Student Import Template')
        branded_valid,branded_preview=validate_upload(branded,1)
        self.assertEqual(len(branded_valid),0)
        self.assertEqual((branded_preview.Validation=='Duplicate').sum(),2)
        invalid=BytesIO();pd.DataFrame({'Bad':['x']}).to_excel(invalid,index=False)
        with self.assertRaisesRegex(ValueError,'missing required columns'): validate_upload(invalid.getvalue(),1)
        exported=excel_bytes(pd.DataFrame({'Student':['=HYPERLINK("x")'],'Attendance %':[70]}),'Test')
        wb=load_workbook(BytesIO(exported)); self.assertEqual(wb.active['A7'].data_type,'s'); self.assertEqual(wb.active.freeze_panes,'C7')
    def test_05_scope(self):
        class_report=student_report(self.admin,{'year_id':1,'class_id':1})
        self.assertEqual(set(class_report.Class),{'XI'})
        teacher2=login('teacher2','teacher123')
        own=student_report(teacher2,{'year_id':1},True)
        self.assertEqual(set(own.Subject),{'English'})
        with self.assertRaises(PermissionError):
            from utils.auth import require_admin
            require_admin(self.teacher)

if __name__=='__main__': unittest.main(verbosity=2)
