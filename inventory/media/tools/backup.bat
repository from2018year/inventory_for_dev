@echo off
setlocal enabledelayedexpansion

set MEMBER=..\
set PATH=%PATH%;%MEMBER%\tools

echo ���Ա������ݣ����Ժ�...
mysqldump -uroot -pagile -P3308 inventory_v2 --default-character-set=utf8 > %MEMBER%\backup\rd
if %errorlevel% equ 0 (
echo ���ݳɹ���backupĿ¼
) else (
echo ��ԭ�������⣬����ϵ�ۿͲ���http://www.gicater.com
)
pause
exit
