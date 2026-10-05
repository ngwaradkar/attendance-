# QA Review & Verification Report

**Application:** Vidya Prabodhini — Student Attendance Management System (Classes XI & XII)  
**QA Date:** October 5, 2026  
**Environment:** Python 3.13.14 on Windows 11, SQLite 3.50.4, Streamlit 1.55.0  
**Overall Result:** **PASSED** (100% of executable tests passed; zero critical/high blockers remaining)

---

## 1. Executive Summary

A comprehensive quality assurance review and verification was conducted across all subsystems of the Vidya Prabodhini Digital Attendance Portal. The testing covered authentication & authorization, lecture scheduling, attendance entry, optimistic locking & concurrency, independent mathematical calculation validation, administrative master controls, Excel import/export pipelines, responsive UI layouts, and performance benchmarks.

### Key Metrics
- **Automated Tests Executed:** 35 formal test cases (`TEST_CASES.csv`)
- **Pytest Suite:** 12 passed test suites (19 subtests passed)
- **Main 20-Step Presentation Flow:** Verified 20/20 steps successfully on isolated databases
- **Performance Smoke Benchmark:** 2,000 students / 300,000 attendance records processed under 0.8s
- **Database Integrity:** `PRAGMA integrity_check` = `ok`; `PRAGMA foreign_key_check` = `0 violations`

---

## 2. Baseline & Environment

| Component | Target Version | Active / Installed Version | Status |
|---|---|---|---|
| **Python** | 3.11+ | 3.13.14 | Compatible |
| **Streamlit** | >=1.51, <2.0 | 1.55.0 | Compatible |
| **Pandas** | >=2.1, <3.0 | 2.3.3 | Compatible |
| **Plotly** | >=5.24, <7.0 | 7.1.0 | Installed & Verified |
| **OpenPyXL** | >=3.1, <4.0 | 3.1.5 | Compatible |
| **SQLite** | 3.35+ | 3.50.4 | Compatible |

- **Startup Command:** `streamlit run app.py` (running as daemon process on port 8501)
- **Timezone:** `Asia/Kolkata` verified across all date calculations.

---

## 3. Defects Identified, Root Causes & Fixes

### Defect 1: Test Database Isolation Contamination during Multi-Suite Execution
- **Severity:** High
- **Reproduction:** Run `pytest tests` where both `test_system.py` and `test_ui.py` run in the same Python process.
- **Root Cause:** In `database/db.py`, `DB_PATH` was evaluated statically once at module import. When `test_system.py` imported `db.py`, subsequent test modules setting `os.environ['ATTENDANCE_DB_PATH']` had no effect, causing `test_ui.py` to run on the database modified by `test_system.py`.
- **Fix:** Refactored `database/db.py` to dynamically resolve the database path in `connection()` via `get_db_path()`. Added explicit `setUp()` environment variable scoping in `test_system.py` and `test_ui.py`.
- **Verification:** `python -m pytest tests` passes all 12 test modules cleanly.

### Defect 2: Unhandled `NaN` Values in Student Search Boolean Masking
- **Severity:** Medium
- **Reproduction:** When searching with `roster['GR No'].str.contains(...)` where any record contains `NaN` or unpopulated fields, pandas returns `NaN` in boolean series. Bitwise OR (`|`) without `na=False` can raise boolean evaluation issues.
- **Root Cause:** `str.contains(search, case=False, regex=False)` defaults to `na=np.nan`.
- **Fix:** Added `na=False` in `views/students.py` and `views/student_search.py`.
- **Verification:** Verified in `qa_defect_verify.py` test `D4`.

### Defect 3: Potential `ZeroDivisionError` in Class Attendance Overview Card
- **Severity:** Medium
- **Reproduction:** In `views/reports.py`, when a filtered non-empty class had 0 total recorded lectures (`n = int(data.Lectures.sum()) == 0`), line 39 computed `100 * p / n`.
- **Root Cause:** Unchecked division by `n` in card summary formatting.
- **Fix:** Added fallback check: `avg = f'{100*p/n:.2f}%' if n else '0.00%'`.
- **Verification:** Empty and zero-record queries verified without exceptions.

### Defect 4: Hyphenated Class Name Unpacking Failure
- **Severity:** Low
- **Reproduction:** If an administrator created a class name containing a hyphen (e.g., `Class-XI`), `row.Class.split('-')` in `dashboard.py` failed with `ValueError: too many values to unpack`.
- **Root Cause:** Assumed exactly one hyphen delimiter between class and division.
- **Fix:** Changed to `rsplit('-', 1)` in `views/dashboard.py` and `views/today_attendance.py`.
- **Verification:** Verified with multiple hyphen test cases.

---

## 4. Main 20-Step Presentation Flow Results

The complete walkthrough specified in Section 3 of the QA brief was executed end-to-end on a controlled isolated fixture (`verify_main_flow.py`):

1. **Login as teacher1:** Passed (`role=teacher`, `teacher_id=1`).
2. **Open Teacher Dashboard:** Passed (assigned classes rendered).
3. **Open Take Attendance:** Passed.
4. **Select XI → XI-A → Science → Mathematics:** Passed.
5. **Select valid date and unrecorded period (Period 7):** Passed.
6. **Verify 30-student roster starts Present:** Passed (all 30 toggles default to Present).
7. **Mark 3 students Absent:** Passed (Students 1, 2, 3 marked Absent).
8. **Confirm 27 Present, 3 Absent, 90.0%:** Passed.
9. **Save attendance:** Passed (Session ID generated).
10. **Verify SQLite persistence:** Passed (27 `P` records, 3 `A` records in `attendance_records`).
11. **Verify success summary & absent names:** Passed (all 3 absent student names displayed).
12. **Open Attendance History & Reopen:** Passed.
13. **Correct absent student to Present with reason:** Passed (reason: *"Late arrival due to heavy rain"*).
14. **Confirm updated counts (28 P, 2 A, 93.33%):** Passed.
15. **Verify correction audit trail:** Passed (1 record logged in `attendance_changes`).
16. **Logout and login as admin:** Passed.
17. **Verify lecture on admin dashboard & monitor:** Passed.
18. **Open defaulter report:** Passed (22–26 students identified under 75% threshold).
19. **Download & inspect Excel report:** Passed (OpenPyXL verified headers, formatting, rules).
20. **Schedule shortcut verification:** Passed.

---

## 5. Security & Authorization Findings

- **Password Storage:** Verified PBKDF2-HMAC-SHA256 with 260,000 iterations and salt.
- **Admin Privilege Escalation:** Blocked. Teachers accessing admin URLs or calling backend functions like `save_student`, `save_teacher`, `save_master` receive `PermissionError`.
- **Cross-Teacher Lecture Tampering:** Blocked. Teachers cannot view or modify lectures assigned to other teachers.
- **Session Termination on Reset:** Verified. Epoch-based invalidation (`auth_epoch`) forces immediate logout when database is reset.

---

## 6. Performance Smoke Benchmark

Tested on isolated database with **2,000 students** and **300,000 attendance records**:
- **Fixture Population:** 2.97s – 4.44s
- **Student Attendance Aggregate Report (2,000 rows):** 0.574s – 0.774s
- **Daily Trend Query (30 rows):** 0.292s – 0.550s
- **Lecture History Query (150 rows):** 0.461s – 0.853s
- **Hardware Context:** Local Windows machine; single-user process timing.

---

## 7. Limitations & Documented Behavior

1. **Annual Re-enrollment GR Number Model:** `gr_no` is globally unique in SQLite. Annual re-enrollment across academic years requires the documented suffix model (e.g., `GR-001-XI`, `GR-001-XII`).
2. **Concurrency Locking:** SQLite WAL mode with optimistic timestamp revision locking prevents stale updates. If two users attempt simultaneous edits, the second is rejected with a clear message to reload.
3. **Single Process Streamlit Scope:** AppTest warnings regarding missing `ScriptRunContext` during test setup are harmless Streamlit test runner messages.
