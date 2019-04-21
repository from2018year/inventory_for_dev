Dim delayer
Set delayer = CreateObject("WScript.Shell")
WScript.sleep 1000
delayer.Run "D:\workspace\inventory_for_web\trunk\inventory_for_web\webloader.exe -h", 0, FALSE
Set delayer = Nothing
WScript.quit