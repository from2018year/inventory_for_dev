@echo off
setlocal enabledelayedexpansion

set MEMBER=..\
set PATH=%PATH%;%MEMBER%\tools

:redo
echo 正在列出您的备份文件
set /A index=0
for /F "tokens=*" %%i in ('dir %MEMBER%\backup /B') do (
	set /A index=index+1
	echo [!index!] %%i
)
set /p x=输入您想使用的文件，如1:
echo %x%
set /A index=0
for /F "tokens=*" %%i in ('dir %MEMBER%\backup /B') do (
	set /A index=index+1
	if !index! equ !x! (
		set FILE=%%i
		echo 您选择了使用文件!FILE!
		call :recover %%i
	)
)

echo 没有找到您输入的文件
goto :redo
goto:eof

:recover
echo 正在使用%FILE%还原，请稍后...
mysql -uroot -pagile -P3308 -Dinventory_v2 --default-character-set=utf8 < %MEMBER%\backup\%FILE%
if %errorlevel% equ 0 (
echo 还原成功
) else (
echo 还原遇到问题，请联系聚客餐饮http://www.gicater.com
)
pause
exit
goto :eof