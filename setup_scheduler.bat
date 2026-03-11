@echo off
REM ============================================
REM GEM Protocol — Windows Task Scheduler 등록
REM 관리자 권한으로 실행하세요
REM ============================================

set VENV_PYTHON=C:\Code_Dev\33_2029\.venv\Scripts\python.exe
set SCRIPT=C:\Code_Dev\33_2029\run_engines.py
set WORKDIR=C:\Code_Dev\33_2029

echo [1/2] 5분 주기 작업 등록 (Engine 1 + 2)...
schtasks /Create /TN "GEM_Protocol_Fast" ^
    /TR "%VENV_PYTHON% %SCRIPT% --group fast" ^
    /SC MINUTE /MO 5 ^
    /F

echo [2/2] 1시간 주기 작업 등록 (Engine 3)...
schtasks /Create /TN "GEM_Protocol_Slow" ^
    /TR "%VENV_PYTHON% %SCRIPT% --group slow" ^
    /SC HOURLY /MO 1 ^
    /F

echo.
echo === 등록 완료 ===
echo  - GEM_Protocol_Fast : 5분마다 Engine 1+2 실행
echo  - GEM_Protocol_Slow : 1시간마다 Engine 3 실행
echo.
echo 삭제하려면:
echo   schtasks /Delete /TN "GEM_Protocol_Fast" /F
echo   schtasks /Delete /TN "GEM_Protocol_Slow" /F
echo.
pause
