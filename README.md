# Vidya Prabodhini — Student Attendance Management System

A complete local demonstration for Vidya Prabodhini High School / Higher Secondary Section, Classes XI and XII. Python, Streamlit, Pandas, SQLite, Plotly, and OpenPyXL. No Node.js, cloud service, or paid API is required.

**All seeded students, teachers, guardians, phone numbers, and historical attendance are fictional.** Phone numbers use `0000000000`; teacher email addresses use `example.invalid`. The included logo is an original generic placeholder, not an institution asset.

## Install and run

Use Python **3.11 or newer**. Extract the ZIP, open a terminal in `vidya_attendance`, then:

```bash
python -m venv venv
```

Windows (Command Prompt):

```bat
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Windows (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

macOS / Linux:

```bash
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal (normally `http://localhost:8501`). If the `streamlit` command cannot be found, use `python -m streamlit run app.py`. No manual SQL setup is needed. An absent database is created and seeded automatically.

## Demo accounts

| Role | Username | Initial demo password | Example subject |
|---|---|---|---|
| Admin | admin | admin123 | All classes and reports |
| Teacher | teacher1 | teacher123 | Mathematics |
| Teacher | teacher2 | teacher123 | English |
| Teacher | teacher3 | teacher123 | Science subjects |
| Teacher | teacher4 | teacher123 | Commerce and Science subjects |
| Teacher | teacher5 | teacher123 | Commerce subjects |

These are **DEMO credentials**. Administrators can change their own password in Settings and reset teacher passwords in Teacher Master. Disable demo mode to hide the demo login information. Disabling demo mode does not remove fictional data or change passwords.

Initial seed credentials can be configured with environment variables `DEMO_ADMIN_USERNAME`, `DEMO_ADMIN_PASSWORD`, and `DEMO_TEACHER_PASSWORD`. Set them **before the first initialization** or before a confirmed demo reset. They do not overwrite existing account passwords.

## Five-minute management presentation

1. Login as `teacher1`.
2. Open **Take Attendance**, choose **2026–27 → XI → XI-A → Science → Mathematics**.
3. Choose today's date and **Period 3**, or another unrecorded period. Seeded records may already occupy a period; the application identifies this and offers View / Edit.
4. All students start Present. Switch off the first three students; the summary shows 27 Present, 3 Absent, 90%.
5. Save and review the success summary and absent students' names.
6. Open My Attendance History; select the new lecture and Edit Attendance. Change one status, enter a correction reason, and save. The correction retains original and updated statuses, user, timestamp, and reason.
7. Logout; login as admin. Open Today's Attendance and Dashboard to see the new lecture reflected in totals.
8. Open Defaulter Report to show fictional students below 75%. Choose the previous month for a fully populated demonstration if the current month has only a few recorded days.
9. Download the formatted Excel report, then demonstrate the monthly register and Student Search.

On Sundays or a configured holiday, the teacher's schedule can be empty. Teachers can still take an assigned subject on a non-holiday date from Take Attendance. This is a configurable weekly demo schedule, not a compulsory timetable enforcement system.

## Modules

**Admin navigation:** Dashboard; Take Attendance; Today's Attendance; Student Master; Teacher Master; Academic Master; Student Search; Attendance Reports; Defaulter Report; Attendance History; Excel Import; Excel Reports; Audit Log; Settings; Logout.

**Teacher navigation:** My Dashboard; Take Attendance; My Attendance History; Student Search; Reports; Logout. Teachers see their assigned classes and subjects. They can edit only lectures that they recorded and remain assigned to. Administrators can modify any lecture.

- **Dashboard:** six KPI cards, 60-day attendance trend, class bar chart, present/absent donut, subject chart, defaulters, teacher activity, and Quick Demo walkthrough.
- **Take Attendance:** assignment-aware class / division / stream / subject selection, date, period, automatic teacher, mobile-friendly Present toggles, mark-all controls, reset, save, duplicate detection, and audited corrections.
- **Today's Attendance:** class monitor with configurable Good / Attention / Low statuses, no-record indicators, absent students with guardian contact fields, copyable summaries, and Excel exports.
- **Student Master:** add, edit, deactivate, filter, and export students. Deactivation retains attendance history.
- **Teacher Master:** create / edit / deactivate accounts; assign subjects and weekly lecture slots; enable / disable assignments.
- **Academic Master:** configurable classes, divisions, streams, subjects, years, and holidays. No source change is needed to add a division or stream.
- **Student Search:** name / roll / GR search, lecture KPIs, monthly trend, subject breakdown, and Excel download.
- **Reports:** date-range class and subject reports, summary cards, and a monthly attendance matrix. Excel Reports opens the same export-ready reporting workspace.
- **History:** lecture-level history, roster detail, teacher filter for administrators, edit action, cancellation / restoration with reason, correction history, and export.
- **Audit Log:** administrator-only, date/action filters and pagination for logins, saves, corrections, imports, student actions, and master changes.
- **Settings:** institution identity, year, thresholds, periods, demo mode, logo, administrator password, confirmed demo reset, and future enhancement list.

## Attendance calculations and interpretation

```text
Attendance % = Present lecture records / Total recorded lecture records × 100
```

Holidays and cancelled sessions are excluded by the reporting queries. No lecture, no saved student record, or a student enrolling later never automatically becomes an absence. Only explicit `P` / `A` records contribute to percentages. Students without records are omitted from defaulter calculations; the monthly register shows `-` and a blank percentage for unknown attendance.

Daily dashboard totals and the monitor count **student-lecture records**, not distinct students or daily attendance. A student present in two periods contributes two Present records. Enrolled student totals are shown separately in the monitor. The class report's Average Attendance is weighted by recorded lectures; Total Lectures counts distinct sessions.

A monthly cell displays `P`, `A`, or `-`. Multiple lectures on a day appear as `P/A/P` in period order, so no lecture is silently collapsed. The Present / Absent totals count every recorded lecture.

A lecture's unique key is **date + academic year + division (which determines class) + stream + subject + period**. Stream forms part of the key because distinct student streams may attend different lectures in the same division. Concurrent duplicate saves are prevented with a database unique constraint and an immediate transaction. The roster must exactly match active students on creation. When editing, the historical roster is preserved even if students have since been deactivated.

## Excel student import

Open **Excel Import**, download the template, select the academic year, then upload `.xlsx`. The downloaded branded template is accepted directly: the importer recognizes its column header on Excel row 6. Plain workbooks with their header on row 1 are also accepted. Student Master exports are recognized through equivalent column-name mappings.

Required columns:

```text
Roll No | GR No | Student Name | Class | Division | Stream | Parent Name | Mobile
```

Example:

```text
31 | DEMO-NEW-031 | Demo New Learner | XI | A | Science | Demo Guardian | 0000000000
```

Optional: `Gender`, `Student Mobile`. Mobile columns should be formatted as Text. Blank phone values are allowed. Use valid configured classes, divisions, and enabled streams. A division may be `A` or `XI-A` with Class `XI`.

The preview identifies missing columns, invalid roll numbers, invalid class/stream references, malformed phone values, duplicate GR numbers, and duplicate roll numbers in the same year/division/stream. Duplicate checks cover both the workbook and the database. Confirm explicitly before valid rows are inserted. The final summary shows Successful / Failed / Duplicates, and the validation report can be downloaded. Invalid rows are skipped; no existing student is silently updated. Limit: 10 MB compressed, 50 MB expanded, and 10,000 rows per upload.

## Excel exports

OpenPyXL generates institution/report headings, year and date range, generated timestamp, navy headers, alternating row fills, borders, readable widths, frozen headings, autofilters, percentage formats, configurable low-attendance highlighting, and landscape print setup. Uploaded text that resembles a formula is escaped before export.

Downloads: Student Master; Daily Attendance; Absent Students; Monthly Attendance Matrix; Defaulter Report; Subject-wise Attendance; Class Attendance; Student Profile; Attendance History; Audit Log; Import Template and Validation Results.

## Database, backup, and reset

Default location: `data/attendance.db`, relative to the application, independent of the shell's working directory. `ATTENDANCE_DB_PATH` can override the location. Foreign keys, WAL mode, a busy timeout, parameterized values, scoped SQL aggregation, and indexes support multiple readers and large attendance tables.

The database holds users, teachers, students, classes, divisions, streams, subjects, teacher assignments, sessions, records, years, holidays, settings, audit logs, and per-record corrections. Seed data includes 120 students (30 in each division), five teachers, multiple subjects, and 60 calendar days of fictional history, excluding Sundays. Science is demonstrated in A divisions; Commerce in B divisions. Arts is enabled and ready for new students / assignments. Some fictional students deliberately have low attendance.

For a consistent backup, stop Streamlit and copy `attendance.db` along with any remaining `-wal` / `-shm` files, or use SQLite's backup API while running. Do not place a live database in a folder where synchronization software may modify it while the server is running.

**Reset:** as admin, open Settings → Reset Demo Database, enable demo mode if disabled, type `RESET DEMO`, tick the destructive-action confirmation, and press Reset. All current data is removed in one transaction and replaced by fictional seed data; everyone must login again. This is disabled outside demo mode.

Academic Year is chosen in Settings. Add more years in Academic Master. Sessions retain their year and old years remain reportable. Enrollment fields are fixed once a student has attendance history; to enroll the same student in a new year, create a new annual enrollment with a distinct GR suffix (for example `GR123-2027`). This maintains historical class membership. It is a lightweight demo enrollment model rather than a separate permanent-person/enrollment module.

## Logo and appearance

The original generic placeholder is `assets/logo_placeholder.png`. Put an authorized logo in `assets/`, then set its relative path in Settings (PNG, JPG, or WebP). Settings controls institution name and subtitle. Custom navy/blue styling is in `styles/custom.css`; theme configuration is in `.streamlit/config.toml`.

The attendance editor uses one full-width toggle per student rather than a wide editable grid. Columns stack on smaller screens; report tables retain horizontal scrolling. No fonts or images are hotlinked.

## Project layout

```text
vidya_attendance/
  app.py
  requirements.txt
  README.md
  VERIFICATION.md
  database/       db.py, schema.py, seed_data.py
  views/          modular admin and teacher screens
  utils/          auth, calculations, validators, admin services, UI, Excel helpers
  styles/         custom.css
  assets/         logo_placeholder.png
  data/           attendance.db (automatically initialized)
  tests/          test_system.py, test_ui.py
  .streamlit/     config.toml
```

`views/` is deliberately used instead of Streamlit's special `pages/` directory. All navigation runs through the authenticated entry point, which revalidates the active user and role on each rerun.

## Verification

```bash
python -m compileall -q .
python tests/test_system.py
python tests/test_ui.py
```

Tests use disposable databases and do not modify the demo database. The integration suite checks password verification, seed counts, saving, duplicates, teacher scope, corrections, stale updates, cancellation, holidays, missing records, imports, and Excel output. The UI suite exercises login, every role-specific page, a 30-student save/correction, report variants, academic master variants, and teacher navigation guards. See `VERIFICATION.md` for recorded results.

## Streamlit Community Cloud — optional demo deployment

The application works locally without any cloud service. To publish an optional fictional-data demonstration:

1. Put this project in a GitHub repository. Keep `requirements.txt` and `.streamlit/config.toml` with `app.py`; the supplied `.gitignore` excludes the database and secrets.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) and choose Create app.
3. Choose repository, branch, and `app.py` (or `vidya_attendance/app.py` if the project is nested).
4. In Advanced settings choose an available Python 3.11+ runtime, then deploy. The seed database is initialized when the application starts.
5. Use only fictional data for this hosted demo. Local file persistence is not guaranteed on Community Cloud; records may disappear on restarts/rebuilds. Use the local SQLite setup for a durable demonstration and back it up.

Official documentation: [Deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [Local storage persistence](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data), [App testing](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).

## Security and operational scope

Passwords are salted PBKDF2-SHA256 hashes, never stored as plain text. Accounts and teacher assignments are checked by services, not just hidden menu entries. SQL values are parameterized. Session-level failed-login throttling prevents rapid accidental retries but is not a distributed brute-force defense. Only admins can reset the demo or modify masters; corrections retain a dedicated per-student trace.

This is a locally runnable, fictional-data demo. Production use should add organization-specific approval/retention policies, stronger authentication, server-side distributed rate limits, encrypted backups, and a persistent hosting setup. Turning off demo mode does not remove demo users or convert the app into a production identity system.

Future enhancements are labelled only: QR / RFID / biometric attendance, parent notifications, student / parent portals, timetable integration, exams, leave, late entry, cloud database, automated alerts, and ID cards. No messages are automatically sent.
