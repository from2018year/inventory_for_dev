@echo off
setlocal enabledelayedexpansion

set MEMBER=..\
set PATH=%PATH%;%MEMBER%\tools

:redo
echo �����г����ı����ļ�
set /A index=0
for /F "tokens=*" %%i in ('dir %MEMBER%\backup /B') do (
	set /A index=index+1
	echo [!index!] %%i
)
set /p x=��������ʹ�õ��ļ�����1:
echo %x%
set /A index=0
for /F "tokens=*" %%i in ('dir %MEMBER%\backup /B') do (
	set /A index=index+1
	if !index! equ !x! (
		set FILE=%%i
		echo ��ѡ����ʹ���ļ�!FILE!
		call :recover %%i
	)
)

echo û���ҵ���������ļ�
goto :redo
goto:eof

:recover
echo ����ʹ��%FILE%��ԭ�����Ժ�...
mysql -uroot -pagile -P3308 -Dinventory_v2 --default-character-set=utf8 < %MEMBER%\backup\%FILE%
if %errorlevel% equ 0 (
echo ��ԭ�ɹ�
) else (
echo ��ԭ�������⣬����ϵ�ۿͲ���http://www.gicater.com
)
pause
exit
goto :eof