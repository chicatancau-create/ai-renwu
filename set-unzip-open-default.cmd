@echo off
chcp 936 >nul
setlocal
title 设置默认解压并打开
set "PS1=C:\Users\Admin\.dsh\tools\set-unzip-default-admin.ps1"

fltmc >nul 2>&1
if not errorlevel 1 goto :run
if /i "%DSH_ELEVATED%"=="1" goto :noadmin
set "DSH_ELEVATED=1"
echo 需要管理员权限，正在请求提权...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%~1' -Verb RunAs"
exit /b 0

:noadmin
echo(
echo 提权被取消或失败。请右键这个文件，选择“以管理员身份运行”。
pause
exit /b 1

:run
echo(
if /i "%~1"=="revert" goto :revert
echo 正在写入系统级文件关联（zip / 7z / tar / gz）...
echo 原来的设置会自动备份到 C:\Users\Admin\.dsh\tools\hklm-assoc-backup
echo(
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 goto :failed
echo(
echo 完成。现在双击 zip / 7z / tar / gz 就该走“解压并打开”了。
echo 如需还原，把本文件拖到命令行后面加 revert 运行：set-unzip-open-default.cmd revert
pause
exit /b 0

:revert
echo 正在还原系统级文件关联...
echo(
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Revert
if errorlevel 1 goto :failed
echo(
echo 已还原。
pause
exit /b 0

:failed
echo(
echo 执行失败，请把上面的输出发给我。
pause
exit /b 1
