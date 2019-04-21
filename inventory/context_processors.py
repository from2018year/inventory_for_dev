# -*- coding: utf-8 -*- 
from django.db import connection
from inventory.common import datedelta
from inventory.settings import STYLE, INSTALLED_APPS,\
    CREDIT_TEXT, CREDIT_HREF
from inventory.VERSION import VERSION,SITE_MARK,SIMPLE
import time,datetime
from django.core.urlresolvers import resolve
from django.utils import translation
from django.conf import settings

def render_settings_options(request):
    """
    Returns context variables writed in settings.py
    """


    
    comment_prifix=None
    try:
        comment_prifix=resolve(request.path_info).url_name.split('.')[-1]
    except:
        pass

    return {
        'STYLE':request.session.has_key('org') and request.session['org'].style or STYLE,
        'ONLINE':'',
        'VERSION':VERSION,
        'CREDIT_TEXT':CREDIT_TEXT,
        'CREDIT_HREF':CREDIT_HREF,
        'SITE_MARK':SITE_MARK,
        'SIMPLE':SIMPLE,

        'comment_prifix':comment_prifix,
        'OSSI_URL':getattr(settings, 'OSSI_URL', '')
    }
    
    