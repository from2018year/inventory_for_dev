# -*- coding: utf-8 -*-
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q,Sum,F
from dateutil import rrule
from depot.models import Organization, Goods, MacrosKeyWeb, Announce, Invoice,\
    InvoiceDetail, OrgProfile
from inventory.common import *
from inventory.VERSION import SITE_MARK,SIMPLE
import logging
import traceback
from django.conf import settings
from django.utils.translation import check_for_language
from django.utils import translation

log=logging.getLogger(__name__)

def register(request):
    template_var={}
    try:
        template_var['cpuid']=readcpuid()
        if request.method=="POST":
            template_var['ma']=ma=request.POST.get('ma','')
           
            res,date,sites=check_ma(ma)
            if res:
                template_var['msg']="<span style='color:red'>%s%s<span>"%(_(u'注册码校验错误，错误号'),res)
            else:
                update_key(ma)
                template_var['msg']=u"%s%s，%s%s<br/>%s<a href='/'>%s</a>"%(_(u'您已注册成功,许可期限为'),(("%s"%date)[:10]),_(u'允许授权为'),sites,_(u'请返回登陆页面重新登录使用系统'),_(u'返回登录页'))
        
        key,ind,res,_date,sites=fetch_key()
        template_var['ma']=key
        
        if not key:
            template_var['res']=_(u'您的试用期限已到')
        else:
            if res==0:
                template_var['res']=u'%s%s,%s'%(_(u'您的到期时间为'),(("%s"%_date)[:10]),_(u'如需重新注册'))
            elif res==3:
                template_var['res']=u'%s%s'%(_(u'您的软件已过期,的到期时间为'),(("%s"%_date)[:10]))
            else:
                template_var['res']=_(u'注册码不正确')
        
        return render_to_response("register.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()
        return HttpResponse(u'<div style="text-align:center"><div style="display:block;width:600px;margin:200px auto;padding:20px;background:#eee;border: 3px solid rgb(188, 204, 238);">%s</div></div>'%(_(u'您的注册系统受到破坏，请联系软件供应商')))


'''
    验证一下org的注册码并同步到过期时间
'''
def sync_auth_key(org):
    keys=MacrosKeyWeb.objects.filter(org=org)
    if not keys.exists():
        #没有key的时候，自动生成3月的免费使用期
        MacrosKeyWeb.objects.create(org=org,key_str=create_ma_web(org))
        keys=MacrosKeyWeb.objects.filter(org=org)
    
    key=keys[0]
    res,_date,sites=fetch_key_web(key)
    
    if not res:
        org.expiry_date=_date
        org.save()
        
    return res,_date,sites

from functools import wraps
def require_pos_config(view):
    @wraps(view)
    def wrapper(request,org_id,*args,**kwargs):
        now=datetime.datetime.now()
        if SITE_MARK=='online':
            if not request.session.has_key('expired_date'):
                try:
                    _date=sync_auth_key(Organization.objects.get(pk=org_id))[1]
                except:
                    _date=sync_auth_key(Organization.objects.get(slug=org_id))[1]
                if not _date:
                    return HttpResponseRedirect(reverse('org_auth_web',args=[org_id]))
                request.session['expired_date']=_date
            elif request.session['expired_date']<now:
                return HttpResponseRedirect(reverse('org_auth_web',args=[org_id]))
        
        return view(request,org_id,*args,**kwargs)
    return wrapper

def login(request,slug):
    template_var={}
    lang_code = request.REQUEST.get('language', None) or request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME,None)
    if not lang_code:
        if request.META['HTTP_HOST'][0].isdigit():
            lang_code="en"
        else:
            lang_code="zh-cn"
    if lang_code and check_for_language(lang_code):
        translation.activate(lang_code)
        
        if hasattr(request, 'session'):
            request.session['django_language'] = lang_code
     
    if SITE_MARK=="online" and slug:
        try:
            org=Organization.objects.select_related().get(slug=slug)
            template_var['org']=org
            request.session['org']=org
            request.session['style']=org.style=='other' and org.slug or org.style
        except:
            print traceback.print_exc()
    if request.method=="POST":
        username=request.POST['user_session_login']
        password=request.POST['user_session_password']
        template_var['username']=username
        
        #验证码
        user=authenticate(username=username,password=password)
        
        if user and user.is_active:
            auth_login(request,user)
            
            
            om_orgs=user.om_orgs.all()
            if SITE_MARK=="online" and om_orgs.count():
                org=om_orgs[0].org
                res,_date,sites=sync_auth_key(org)
                if res:
      
                    request.session['org']=org
                    return HttpResponseRedirect(reverse('org_auth_web',args=[org.pk]))
                
                request.session['sites']=sites
                request.session['expired_date']=_date
                
            #转向到加载资源页面
            #return HttpResponseRedirect(reverse('load_resources'))
            #如果有多个店或者可以看到多个店转向店面选择
            if request.REQUEST.get('next',False):
                return HttpResponseRedirect(request.REQUEST.get('next'))
            om_orgs=user.om_orgs.all()
            
            if om_orgs.count()>1:
                #有多家店
                #debug_info(u'多家店')
                return HttpResponseRedirect(reverse('select_orgs'))
            elif om_orgs.count()==1:
                if  om_orgs[0].org.children.exists() and user.is_org_superuser(om_orgs[0].org):
                    #仅有一家，但是有分店
                    #debug_info(u'多家分店')
                    return HttpResponseRedirect(reverse('select_orgs'))
                else:
                    #debug_info(u'一家分店有管理权限')
                    request.session['org_id']=om_orgs[0].org_id
                    request.session['org']=om_orgs[0].org
                    
                    if SIMPLE=="simple":
                        if request.user.has_org_perm(org,'depot.wupin_ui'):
                            return HttpResponseRedirect(reverse('wupin',args=[om_orgs[0].org_id]))
                        elif request.user.has_org_perm(org,'depot.chenbenka_ui'):
                            return HttpResponseRedirect(reverse('caipin',args=[om_orgs[0].org_id]))
                        elif request.user.has_org_perm(org,'depot.danju_ui'):
                            return HttpResponseRedirect(reverse('main',args=[om_orgs[0].org_id]))
                        elif request.user.has_org_perm(org,'depot.tongji_ui'):
                            return HttpResponseRedirect(reverse('tongji_main',args=[om_orgs[0].org_id]))
                        elif request.user.has_org_perm(org,'depot.xitongshezhi_ui'):
                            return HttpResponseRedirect(reverse('org_settings',args=[om_orgs[0].org_id]))
                        else:
                            return HttpResponse("你没有任何一个界面操作权限")


                    else:
                        return HttpResponseRedirect(reverse('jishikucun',args=[om_orgs[0].org_id]))
                    
            template_var['msg']=_(u'您已经没有关联的公司')
        else:
            template_var['msg']=_(u'用户名或密码不正确')
        
    return render_to_response("login.html",template_var,context_instance=RequestContext(request))



def login_debug(request,slug):
    pass



'''
    orgs注销入口
'''
def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse('login'))




'''
    用户登录公司主页
'''
@login_required(login_url="/")
@require_pos_config
def main(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        #om=OrgsMembers.objects.get(user=request.user,org=org)
        request.session['org_id']=org_id
        request.session['org']=org
        
        
        
        return render_to_response("org_main.html",template_var,context_instance=RequestContext(request))
        #return render_to_response("org_backstage.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()
 
 
'''
    选择公司,列出公司
'''
def select_orgs(request):
    template_var={}
    om_orgs_id=list(request.user.om_orgs.values_list('org',flat=True))
    orgs=Organization.objects.filter(id__in=om_orgs_id)
    
    o=orgs.filter(parent__isnull=True)
    return HttpResponseRedirect(reverse('main',args=[o[0].id]))
    
    if o.exists():
        if request.user.has_org_perm(o[0].pk,'orgs.manage'):
            children_id=list(o[0].get_descendants(include_self=False).values_list('id',flat=True))
            orgs_id=list(set(children_id+om_orgs_id))
            orgs=Organization.objects.filter(id__in=orgs_id)
    
    
    org_groups={}
    for org in orgs:
        if org_groups.has_key(org.org_group):
            org_groups[org.org_group].append(org)
        else:
            org_groups[org.org_group]=[org]
    template_var['org_groups']=org_groups
    
    return render_to_response("org_select.html",template_var,context_instance=RequestContext(request))