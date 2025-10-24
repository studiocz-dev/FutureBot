@echo off
REM Stop FutureBot - Kills all Python processes
REM WARNING: This will stop ALL Python processes on your system

echo ============================================================
echo FutureBot - Stop Script
echo ============================================================
echo.

REM Check if any Python processes are running
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Python processes found:
    echo.
    tasklist /FI "IMAGENAME eq python.exe"
    echo.
    echo WARNING: This will kill ALL Python processes!
    echo Press Ctrl+C to cancel, or
    pause
    echo.
    echo Stopping Python processes...
    taskkill /F /IM python.exe
    echo.
    echo Done!
) else (
    echo No Python processes are currently running.
)

echo.
echo ============================================================
pause
