@echo off
cd /d "%~dp0"
"C:\Users\Brian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "%~dp0server.py" >> "%~dp0server.out.log" 2>> "%~dp0server.err.log"
