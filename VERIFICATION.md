# Verification record

Verified 4 October 2026 on Python 3.12. The project targets Python 3.11+.

## Checks passed

- All Python files compile successfully.
- Five database/service integration tests pass.
- Seven Streamlit UI tests pass, including all 14 administrator routes and all five teacher routes.
- Actual login from the login form opens the teacher workspace.
- A 30-student teacher roster starts Present, three students can be marked Absent, and saving reports 27 Present / 3 Absent / 90%.
- Saving the same lecture again is rejected.
- Reopening and correcting the lecture stores original status, updated status, user, timestamp, and reason; stale concurrent revisions are rejected.
- History's Edit Attendance button navigates to the editor.
- The teacher dashboard's lecture shortcut opens the assigned roster; this is checked on a configured working weekday because the verification date is Sunday.
- Teacher pages reject administrator navigation and report only assigned subjects.
- Holidays, cancelled lectures, and dates with no records are excluded from attendance calculations.
- Class-only filters restrict results to the selected class.
- Plain and branded Excel workbooks are validated; missing columns, duplicates, and invalid rows are handled.
- OpenPyXL exports reopen successfully, freeze headings, and escape formula-like text.
- Class / subject / monthly report variants and all academic master variants render successfully.
- A real Streamlit process starts and returns HTTP 200 from both its health endpoint (`ok`) and entry page.
- The packaged fictional SQLite database passes `PRAGMA integrity_check` and has zero foreign-key violations.

## Larger-data smoke test

A separate temporary database was populated with 2,000 students and 300,000 attendance records. On this execution machine:

| Query | Returned rows | Time |
|---|---:|---:|
| Student attendance report | 2,000 | 0.151 seconds |
| Daily trend | 30 | 0.088 seconds |
| Lecture history | 150 | 0.139 seconds |

Fixture insertion took approximately 0.65 seconds. These measurements are a single-machine SQL smoke test, not a concurrent-user load benchmark or a guarantee on another computer.

## Reproduce

From the project folder:

```bash
python -m compileall -q .
python tests/test_system.py
python tests/test_ui.py
python tests/performance_smoke.py
streamlit run app.py
```

All automated tests use disposable temporary databases; they do not modify the included fictional demonstration database. AppTest prints harmless missing-ScriptRunContext warnings when test setup runs outside a live Streamlit session.

The interface uses responsive Streamlit layouts, custom CSS, and full-width student toggles. Physical phone/tablet browser testing and a concurrent multi-user load test were not performed. No deployment was made and no real student data or notification service was used.
