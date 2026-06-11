Specimen Routing MVP - Today Test

How to run
1. Double-click RUN_TODAY_TEST.bat.
2. A black server window will open. Keep it open during testing.
3. The browser will open automatically.
4. Use this address if you need to open it manually:
   http://127.0.0.1:8000/dashboard

Important pages
- Upload worklist: http://127.0.0.1:8000/upload
- Scan specimen: http://127.0.0.1:8000/scan
- Department subdivision: http://127.0.0.1:8000/micro
  The subdivision list is grouped by department/subcategory and prints 30 items per page.
  Excel export is available from the button on the subdivision page.
- Find specimen: http://127.0.0.1:8000/find

How to stop
- Close the black server window, or press Ctrl+C in that window.

Notes
- PostgreSQL must be running.
- This launcher uses the current .env database setting.
- If the page does not open immediately, wait 2-3 seconds and refresh.
