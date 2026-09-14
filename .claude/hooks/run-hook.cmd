@echo off
REM Run a Bash hook without losing its exit code or expanding ! in paths.
setlocal DisableDelayedExpansion
set "HOOK=%~1"
if not defined HOOK exit /b 2

set "BASH_EXE="
if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles%\Git\usr\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\usr\bin\bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if defined BASH_EXE goto run

REM System32 bash.exe launches WSL and cannot read Windows hook paths.
for /f "delims=" %%B in ('where bash 2^>nul') do if not defined BASH_EXE if /i not "%%B"=="%SystemRoot%\System32\bash.exe" if /i not "%%B"=="%LOCALAPPDATA%\Microsoft\WindowsApps\bash.exe" set "BASH_EXE=%%B"
if not defined BASH_EXE (
  echo run-hook.cmd: Git Bash not found 1>&2
  exit /b 1
)

:run
"%BASH_EXE%" "%HOOK%"
exit /b %ERRORLEVEL%
