@echo off

set lang=en
for /f %%i in ('chcp ^| find "936"') do set lang=cn

call :%lang%

if exist "..\Python26\python.exe" (
    ..\Python26\python.exe manage.py changepassword %us%
) else if exist "c:\program files\Python26\python.exe" (
    "c:\program files\Python26\python.exe" manage.py changepassword %us%
) else if exist "d:\program files\Python26\python.exe" (
    "d:\program files\Python26\python.exe" manage.py changepassword %us%
) else if exist "c:\Python26\python.exe" (
    "c:\Python26\python.exe" manage.py changepassword %us%
) else if exist "d:\Python26\python.exe" (
    "d:\Python26\python.exe" manage.py changepassword %us%
)
echo.
pause

goto :eof

:cn
set /p us=请输入您想修改密码的用户:
echo 环境检查中，请稍候...
goto :eof

:en
set /p us=Please enter you username to change password:
echo waiting...
goto :eof