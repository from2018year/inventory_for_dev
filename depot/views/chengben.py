# -*- coding: utf-8 -*- 
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from depot.models import Organization
from inventory.common import *
import logging
import traceback

'''
    用户登录公司主页
'''
@login_required(login_url="/")
def org_chengben(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        #om=OrgsMembers.objects.get(user=request.user,org=org)
        request.session['org_id']=org_id
        request.session['org']=org
        request.session['root_org']=org.get_root_org()
        
        return render_to_response("org_chengben.html",template_var,context_instance=RequestContext(request))
        #return render_to_response("org_backstage.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()