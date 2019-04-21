# -*- coding: utf-8 -*- 
from django.db import connection
from inventory.common import datedelta, fetch_key
from django.http import HttpResponse, HttpResponseRedirect
from inventory.VERSION import SITE_MARK
from django.core.urlresolvers import reverse
import traceback
import hashlib
import time,datetime
from django.utils import translation

class KeyAuthenticationMiddleware(object):
    def process_request(self, request):
        
        if SITE_MARK=="online":
            return None
            now=datetime.datetime.now()
            if request.session.get('expired_date',now)<now:
                return HttpResponseRedirect(reverse('org_import_auth',args=[request.session.get('org').pk]))
        else:
            try:
                if not (request.path=="/register/" or request.path=="/depot/register/" or request.session.has_key('zhuce')):
                    
                    request.session['sites']=2
                    cursor=connection.cursor()
                    try:
                        cursor.execute("select key_str,aes_decrypt(install_date,'salt') from macros_key_hj")
                        row=cursor.fetchone()
                    
                        key=row[0]
                    except:
                        return HttpResponseRedirect('/register/')
                        #return HttpResponseRedirect('/register/')
                    _date=time.strptime(row[1],'%Y-%m-%d')
                    
                    _date=datetime.datetime(*_date[:6])
                    now=datetime.datetime.now()
                    
                    if not key and (datedelta(_date,1,3)<now or _date>now):
                        return HttpResponseRedirect('/register/?invalid_install_date=%s'%(_date>now))
                    elif not key:
                        request.META['date']=datedelta(_date,1,3) 
                        request.META['zhuce']=True  
                    elif key:
                        #验证key的合法性
                        key,ind,res,_date,sites=fetch_key()
                        
                        request.session['sites']=sites
                        request.META['date']=_date 
                        
                        if datedelta(now,30,1)>_date:
                            request.META['zhuce']=True
                            
                        if datedelta(now,30,1)<_date:
                            request.session['zhuce']=1
                        if res:
                            return HttpResponseRedirect('/register/')
                        
            except:
                print traceback.print_exc() 
                return HttpResponseRedirect('/register/')
        return None