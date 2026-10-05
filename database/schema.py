SCHEMA = '''
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS academic_years(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS divisions(id INTEGER PRIMARY KEY,class_id INTEGER NOT NULL REFERENCES classes(id),name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(class_id,name));
CREATE TABLE IF NOT EXISTS streams(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','teacher')),name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),name TEXT NOT NULL,email TEXT DEFAULT '',active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,roll_no INTEGER NOT NULL CHECK(roll_no>0),gr_no TEXT UNIQUE NOT NULL,name TEXT NOT NULL,gender TEXT NOT NULL DEFAULT 'Not specified',division_id INTEGER NOT NULL REFERENCES divisions(id),stream_id INTEGER NOT NULL REFERENCES streams(id),year_id INTEGER NOT NULL REFERENCES academic_years(id),parent_name TEXT DEFAULT '',parent_mobile TEXT DEFAULT '',student_mobile TEXT DEFAULT '',active INTEGER NOT NULL DEFAULT 1,UNIQUE(year_id,division_id,stream_id,roll_no));
CREATE TABLE IF NOT EXISTS teacher_assignments(id INTEGER PRIMARY KEY,teacher_id INTEGER NOT NULL REFERENCES teachers(id),division_id INTEGER NOT NULL REFERENCES divisions(id),stream_id INTEGER NOT NULL REFERENCES streams(id),subject_id INTEGER NOT NULL REFERENCES subjects(id),year_id INTEGER NOT NULL REFERENCES academic_years(id),period INTEGER NOT NULL CHECK(period BETWEEN 1 AND 12),weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),active INTEGER NOT NULL DEFAULT 1,UNIQUE(teacher_id,division_id,stream_id,subject_id,year_id,period,weekday));
CREATE TABLE IF NOT EXISTS attendance_sessions(id INTEGER PRIMARY KEY,attendance_date TEXT NOT NULL,year_id INTEGER NOT NULL REFERENCES academic_years(id),division_id INTEGER NOT NULL REFERENCES divisions(id),stream_id INTEGER NOT NULL REFERENCES streams(id),subject_id INTEGER NOT NULL REFERENCES subjects(id),teacher_id INTEGER NOT NULL REFERENCES teachers(id),period INTEGER NOT NULL CHECK(period BETWEEN 1 AND 12),cancelled INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(attendance_date,year_id,division_id,stream_id,subject_id,period));
CREATE TABLE IF NOT EXISTS attendance_records(id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,student_id INTEGER NOT NULL REFERENCES students(id),status TEXT NOT NULL CHECK(status IN ('P','A')),remarks TEXT DEFAULT '',UNIQUE(session_id,student_id));
CREATE TABLE IF NOT EXISTS holidays(id INTEGER PRIMARY KEY,holiday_date TEXT UNIQUE NOT NULL,name TEXT NOT NULL,description TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS attendance_changes(id INTEGER PRIMARY KEY,record_id INTEGER NOT NULL REFERENCES attendance_records(id),original_status TEXT NOT NULL,updated_status TEXT NOT NULL,changed_by INTEGER NOT NULL REFERENCES users(id),changed_at TEXT NOT NULL,reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY,timestamp TEXT NOT NULL,user_id INTEGER REFERENCES users(id),username TEXT NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_sessions_scope ON attendance_sessions(year_id,division_id,stream_id,attendance_date,subject_id);
CREATE INDEX IF NOT EXISTS idx_sessions_teacher ON attendance_sessions(teacher_id,attendance_date);
CREATE INDEX IF NOT EXISTS idx_records_student ON attendance_records(student_id,session_id);
CREATE INDEX IF NOT EXISTS idx_students_scope ON students(year_id,division_id,stream_id,active);
CREATE INDEX IF NOT EXISTS idx_assignments_teacher ON teacher_assignments(teacher_id,year_id,active);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);
'''
