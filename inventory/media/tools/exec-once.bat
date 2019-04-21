@echo off
echo 尝试清除服务端缓存...

mysql -uroot -pagile -P3308 inventory_v2 -e "delete from django_session"

echo 清除完成，请关闭所有浏览器后重新登录

pause