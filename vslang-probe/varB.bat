@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set VSLANG=1033
cl /c /nologo "G:\AIrenwu\vslang-probe\bad.cpp" > "G:\AIrenwu\vslang-probe\logB.txt" 2>&1
