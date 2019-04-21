# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from depot.models import Organization, OrgsMembers, Warehouse, Category
from django.utils.translation import ugettext as _
from gicater.utils.encrypt import encrypt_half_md5,valid_half_encrypt
from django.contrib.auth import authenticate,login as auth_login
from django.template.context import RequestContext
import simplejson
import logging
import time
import traceback
from depot.views.base import sync_auth_key
log=logging.getLogger(__name__)


def vippass(request,path):
    pass
    

def center_login(request,guid):
    pass
        
           
def new_org_with_cmd(request,guid):
    pass

    


