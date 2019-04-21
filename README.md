#How to install
1, requirement: Python 2.7 (virtualenv recommend)
2, git clone https://github.com/from2018year/inventory_for_dev.git any_local_dir_you_want
3, run "pip install -r requirements.txt" to install the requirements
4, import init sql init.sql to database inventory_dev 
5, copy "inventory/settings.sample.py" to "inventory/settings.py", and modify "DATABASE" segment to connet your mysql
6, run "python manage.py runserver" to check if has errors, if everything goes well, you can start code  
