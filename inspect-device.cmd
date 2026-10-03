@echo off
setlocal
pushd "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\inspect-ctz.ps1" %*
set "CTZ_RESULT=%ERRORLEVEL%"
echo.
echo Exit code: %CTZ_RESULT%
pause
popd
exit /b %CTZ_RESULT%
