# -*- coding: utf-8 -*- 
from django.views.decorators.csrf import csrf_exempt
import time
from gicater.utils.encrypt import valid_half_encrypt
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.contrib.auth.models import User,Permission
from django.contrib.auth import authenticate,login as auth_login
from django.utils.translation import ugettext as _
import datetime
import traceback
from django.core.urlresolvers import reverse
from depot.models import Organization, OrgProfile, OrgsMembers, MacrosKeyWeb,\
    Warehouse, Supplier, Customer, ConDepartment, Category
from inventory.common import create_ma_web, fetch_key_web, datedelta
from django.db import transaction
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from depot.views.base import sync_auth_key

@csrf_exempt
@transaction.autocommit
def user_center_sync_org(request):
    
    
    pass
    
def center_auto_login_to_manage(request):
    '''
    ' 自动登录请求
    '''
    pass
    
def center_auto_login(request):
    '''
    ' 自动登录请求
    '''
    pass
             

        
        
def clean_org(guid):
    org=Organization.objects.get(org_guid=guid)

    MacrosKeyWeb.objects.filter(org=org).delete()
    OrgsMembers.objects.filter(org=org).delete()
    
    Warehouse.objects.filter(org=org).delete()
    
    org.delete()
    
    
'''
' 修改餐厅用户名
'''
@csrf_exempt
def change_username(request):
    if request.method=="GET":
        return render_to_response("api2_change_username.html",{},context_instance=RequestContext(request))
    
    try:
        guid=request.GET.get('guid','')
        org_id=request.POST['org_id']
        old_username=request.POST['old_username']
        new_username=request.POST['new_username']
        _check=request.GET.get('check','0')
        
        check=True
        if _check=='0':
            check=False
            
        try:
            if not guid:
                raise
            org=Organization.objects.get(org_guid=guid)
        except:
            org=Organization.objects.get(pk=org_id)
            
        #检查原始的名称
        queryset=OrgsMembers.objects.filter(org=org,user__username=old_username)  
        if not queryset.exists():
            return  HttpResponse(simplejson.dumps({'errno':2,'error':u'旧用户名不匹配'}),mimetype='application/json')  
        
           
        queryset=OrgsMembers.objects.filter(user__username=new_username)  
        if queryset.exists():
            return  HttpResponse(simplejson.dumps({'errno':2,'error':u'新用户名已存在'}),mimetype='application/json') 
        
        if not check:
            user=User.objects.get(username=old_username)
            user.username=new_username
            user.save()
            
        return  HttpResponse(simplejson.dumps({'errno':0,'error':u'修改成功'}),mimetype='application/json') 
        
    except Exception,e:
        print traceback.print_exc()
        return  HttpResponse(simplejson.dumps({'errno':1,'error':e.message}),mimetype='application/json') 
    
    
    
'''
' 获取注册时间
'''
@csrf_exempt
def org_get_reg(request):
    if request.method=="GET":
        return render_to_response("api2_org_get_reg.html",{},context_instance=RequestContext(request))
    
    try:
        guid=request.GET.get('guid','')
        org_id=request.POST['org_id']
            
        try:
            if not guid:
                raise
            org=Organization.objects.get(org_guid=guid)
        except:
            org=Organization.objects.get(pk=org_id)
        
        
        keys=MacrosKeyWeb.objects.filter(org=org).order_by('-id')
        
        ret={'errno':0,'description':None,'expired_date':None}
        if keys.exists():
            key=keys[0]
            res,_date,sites=fetch_key_web(key)
            ret['expired_date']=_date.strftime('%Y-%m-%d')

            
        return  HttpResponse(simplejson.dumps(ret),mimetype='application/json') 
    except Exception,e:
        print traceback.print_exc()
        return  HttpResponse(simplejson.dumps({'errno':1,'description':e.message}),mimetype='application/json') 
    
'''
' 设置注册时间
'''
@csrf_exempt
def org_set_reg(request):
    pass