@echo off
setlocal enabledelayedexpansion

set MEMBER=..\
set PATH=%PATH%;%MEMBER%\tools

echo 尝试备份数据，请稍后...
mysqldump -uroot -pagile -P3308 inventory_v2 --default-character-set=utf8 > %MEMBER%\backup\rd
if %errorlevel% equ 0 (
echo 备份成功到backup目录
) else (
echo 还原遇到问题，请联系聚客餐饮http://www.gicater.com
)
pause
exit
