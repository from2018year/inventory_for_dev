# -*- coding: utf-8 -*- 
import os,sys
#from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
#from django.utils.translation import ugettext as _
BASE=os.path.dirname(os.path.abspath(__file__))
EXE_DIR=os.path.join(BASE,'media/tools/').replace('\\','/')
TMP_DIR=os.path.join(BASE,'media/tmp/').replace('\\','/')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

#emial config
EMAIL_HOST = 'smtp.126.com'  
EMAIL_PORT = '25'  
EMAIL_HOST_USER = 'gicater_msg@163.com'   
EMAIL_HOST_PASSWORD = 'abc1234567890'  
EMAIL_USE_TLS = True 
MESSAGE_DB_USER="root"
MESSAGE_DB_PWD="agile"
MESSAGE_DB_PORT=3308

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'inventory_v2',                      # Or path to database file if using sqlite3.
        'USER': 'gk_center',                      # Not used with sqlite3.
        'PASSWORD': 'gk_center_2014',                  # Not used with sqlite3.
        'HOST': 'rm-2ze54xqzm9jtg3r4t.mysql.rds.aliyuncs.com',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '3306',                      # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {
            'connect_timeout': 10,
            'init_command': 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED'
        }
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'zh-cn'
LANGUAGES = (
    ('zh-cn','简体中文'),
    ('zh-tw','繁體中文'),
    ('en','English'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(BASE,'media/').replace('\\','/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = 'static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE,'static').replace('\\','/'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

LOCALE_PATHS = (
    os.path.join(BASE,'../locale/').replace('\\','/'),
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'pb(wfj&amp;v9@(l=$zb!!#^z$ka=$sq*ilrv)&amp;y-qcut_)g1&amp;cqe3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'inventory.context_processors.render_settings_options',
    'inventory.uperms.context_processors.auth_org_perm'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'inventory.middleware.KeyAuthenticationMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

DEBUG_TOOLBAR_PANELS = (
             'debug_toolbar.panels.version.VersionDebugPanel',
             'debug_toolbar.panels.timer.TimerDebugPanel',
             'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
             'debug_toolbar.panels.headers.HeaderDebugPanel',
             'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
             'debug_toolbar.panels.template.TemplateDebugPanel',
             'debug_toolbar.panels.sql.SQLDebugPanel',
             'debug_toolbar.panels.signals.SignalDebugPanel',
             'debug_toolbar.panels.logger.LoggingPanel'
)

INTERNAL_IPS = ('127.0.0.11',)

ROOT_URLCONF = 'inventory.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'inventory.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'endless_pagination',
    'mptt', 
    #'debug_toolbar',
    'depot',
    'cost',
    'caiwu'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '(%(levelname)s[%(asctime)s] %(pathname)s[%(lineno)s]) %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
         'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'logfile':{
                'level':'DEBUG',
                'class':'logging.FileHandler',
                'formatter': 'verbose',
                'filename':"%strace.log"%os.path.join(BASE,'../').replace('\\','/'),
                
         },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'depot':{
            'level':'DEBUG',
            'handlers':['console'],
        },
        'cost':{
            'level':'DEBUG',
            'handlers':['console'],
        },
        'inventory.settings':{
            'level':'DEBUG',
            'handlers':['console','logfile'],
            'propagate': True,
        },
        '*':{
            'level':'DEBUG',
            'handlers':['console'],
        },
    }
}


'''
' STYLE 有以下三个可选值， gicater inventory_en inventory,分别表示 聚客 OEM中英文 和oem
' 其中还有member_en时保留上面语言选择中的en其余版本注释掉 
'''
STYLE='agile'
#gicater 聚客版  agile:中文版  inventory_en 英文版
ugettext = lambda s: s
if STYLE=="gicater":
    CREDIT_TEXT=ugettext('库存软件')
    CREDIT_HREF="http://www.gicater.com"
elif STYLE=="agile":
    CREDIT_TEXT=ugettext('库存软件')
    CREDIT_HREF=""
else:
    CREDIT_TEXT=u''
    CREDIT_HREF=""

ENDLESS_PAGINATION_PREVIOUS_LABEL=_(u'上页')
ENDLESS_PAGINATION_NEXT_LABEL=_(u'下页')

import logging
logger = logging.getLogger('inventory.settings')
hdlr = logging.FileHandler("%strace.log"%os.path.join(BASE,'../').replace('\\','/'))
formatter = logging.Formatter('(%(levelname)s[%(asctime)s] %(pathname)s[%(lineno)s]) %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

from threading import Timer

import time
EVERY_TIME=60*60
def add_task():
    from django.core.cache import cache
    from extra import execCycle
    from extra import execOnce
    i=0
    while True:
        work_queue=cache.get('work_queue',[])
        if not i:
            work_queue.append(execOnce)
        work_queue.append(execCycle)
        cache.set('work_queue',work_queue)
        time.sleep(EVERY_TIME)
        i=i+1
        
def do_task():
    from django.core.cache import cache
    while True:
        work_queue=cache.get('work_queue',[])
        cache.set('work_queue',[])
        if work_queue:
            for func in work_queue:
                if isinstance(func,(tuple,list)):
                    func[0](*func[1:])
                else:
                    func()
        
        time.sleep(2)

 
#apache下直接启动，runserver下只在fork之后启动

'''
    每隔指定的时间，将任务添加到cache队列
    查看缓存队列中是否有任务，有任务就执行
'''
from inventory.VERSION import SITE_MARK
if SITE_MARK != 'online':
    
    if len(sys.argv)==1:
        t = Timer(10, add_task)
        t.daemon = True  
        t.start()
        
        worker=Timer(15, do_task)
        worker.daemon = True  
        worker.start()
        
    else:
        if os.environ.get("RUN_MAIN",False) and sys.argv[1]=="runserver":
            t = Timer(10, add_task)
            t.daemon = True  
            t.start()
            
            worker=Timer(15, do_task)
            worker.daemon = True  
            worker.start()


DEFAUT_URL=AGENT_URL="http://stock.sandypos.com/"
ENGLISH_URL="http://182.92.104.138/"

OSSI_URL="http://comment.gicater.net/"
CENTER_URL="http://www.sandypos.com"

BROKER_URL = 'redis://127.0.0.1:6379/2'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/3'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
