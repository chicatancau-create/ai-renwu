@echo off
chcp 936 >nul
setlocal EnableExtensions

rem ---------- 定位 worker：先在自身目录找，再找任务目录 03_工具脚本 ----------
set "WORKER=%~dp0system_cleanup_worker.ps1"
if not exist "%WORKER%" set "WORKER=%~dp003_工具脚本\system_cleanup_worker.ps1"

title 系统目录一键清理（Windows Logs / 更新缓存 / SysReset）

rem ---------- 判管理员：只用 fltmc（net session 依赖 LanmanServer，会把管理员误判成非管理员）----------
fltmc >nul 2>&1
if not errorlevel 1 goto :menu

rem ---------- 需要提权：带"已提权过一次"护栏，防死循环 ----------
if defined _SYS_CLEANUP_ELEVATED goto :elevate_failed
set "_SYS_CLEANUP_ELEVATED=1"
echo(
echo   正在请求管理员权限，请在 UAC 弹窗里点"是"...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b 0

:elevate_failed
echo(
echo   [失败] 已请求过一次提权，仍不是管理员。请手动右键本文件 - 以管理员身份运行。
echo(
pause
exit /b 1

:menu
cd /d "%~dp0"
echo ============================================================
echo   系统目录一键清理（需要管理员，当前已是管理员）
echo ------------------------------------------------------------
echo   将处理：
echo     1^) C:\Windows\Logs       只删 .log/.etl/.txt/.cab/.old
echo                               保留 .evtx/.json/.xml 与目录结构
echo     2^) SoftwareDistribution\Download  Windows 更新缓存（先停 wuauserv，删完恢复）
echo     3^) C:\$SysReset          重置/恢复残留
echo     4^) C:\Windows\MEMORY.DMP 蓝屏转储（存在才处理）
echo ============================================================
echo(
if not exist "%WORKER%" (
  echo   [错误] 找不到 worker 脚本：
  echo          %WORKER%
  pause
  exit /b 1
)
echo   请选择操作：
echo     [1] 仅盘点，不删除（安全，先看能省多少）
echo     [2] 执行清理
echo     [3] 取消
echo(
choice /c 123 /n /m "   输入 1/2/3 后回车: "
rem choice 的 errorlevel 语义是"大于等于 N"：取消档数字最大，必须最先判
if errorlevel 3 goto :cancel
if errorlevel 2 goto :apply
if errorlevel 1 goto :dryrun

:cancel
echo(
echo   已取消，什么都没动。
pause
exit /b 0

:dryrun
echo(
powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKER%" -DryRun
echo(
pause
exit /b 0

:apply
echo(
echo   即将执行删除。按 Ctrl+C 或直接关窗口可中止。
echo(
powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKER%"
echo(
pause
exit /b 0
