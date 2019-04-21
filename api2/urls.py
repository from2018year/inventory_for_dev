# -*- coding: utf-8 -*- 
from django.conf.urls import patterns, url
from piston.resource import Resource


from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import authenticate
from inventory.VERSION import SITE_MARK
from django.http import HttpResponse
from piston.authentication import HttpBasicAuthentication
import traceback
from depot.models import Organization
from api2.handler_cneter import OrganizationGaiKuangHandler

class CoolroidMemberAuthentication(object):
    """
    '此验证方式改进自HttpBasicAuthentication
    '除了要验证用户名和密码，同时也需要验证slug和key
    'url请求应形如 requesturl?slug=xxx&key=xxx
    '其中 slug是餐厅简码，key为餐厅秘钥
    """
    def __init__(self, realm='API'):
        self.realm = realm

    def is_authenticated(self, request):
    
        request_auth_parm = request.GET

        if not request_auth_parm:
            return False
             
        slug=request.GET['slug']
        key=request.GET['key']
        request.user = AnonymousUser()
    
        try:
            Organization.objects.get(slug=slug,org_guid=key)
            return True
        except:
            print traceback.print_exc()
        return False
        
   
        
    def challenge(self):
        resp = HttpResponse("Authorization Required")
        resp.status_code = 401
        return resp


class MultiAuthentication(object):
        """ Authenticated Django-Piston against multiple types of authentication """

        def __init__(self, auth_types):
            """ Takes a list of authenication objects to try against, the default
            authentication type to try is the first in the list. """
            self.auth_types = auth_types
            self.selected_auth = auth_types[0]

        def is_authenticated(self, request):
            """ Try each authentication type in order and use the first that succeeds """
            authenticated = False
            for auth in self.auth_types:
                self.selected_auth = auth
                authenticated = auth.is_authenticated(request)
                if authenticated:
                    break
            return authenticated

        def challenge(self):
            """ Return the challenge for whatever the selected auth type is (or the default 
            auth type which is the first in the list)
            """
            return self.selected_auth.challenge()
auth_coolroid = CoolroidMemberAuthentication()
auth_base=HttpBasicAuthentication(realm="coolroid user auth")
ad = { 'authentication': MultiAuthentication([auth_coolroid,auth_base]) }

class CsrfExemptResource(Resource):
    def __init__(self,handler,authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

'''
    和center交互API
'''
orggaikuang_resource=Resource(handler=OrganizationGaiKuangHandler)
urlpatterns = patterns('',
    url(r'^orggaikuang/(?P<guid>\S+)/$', orggaikuang_resource),
    url(r'^orggaikuang\.(?P<emitter_format>.+)/(?P<guid>\S+)/$', orggaikuang_resource),
)

urlpatterns += patterns('api2.views',
    url(r'add/$','add',name="api2_add"),
    url(r'list/$','list_org',name="api2_list"),
    url(r'sync_menu_item/$','sync_menu_item',name="sync_menu_item"),
    url(r'pos_sync/$','pos_sync',name="pos_sync"),
)


'''
' 来自用户中心的请求
'''
urlpatterns += patterns('api2.user_center',
    url(r'user_center_sync_org/$','user_center_sync_org',name="user_center_sync_org"),
    url(r'center_auto_login/$','center_auto_login',name="center_auto_login"),  
    url(r'center_auto_login_to_manage/$','center_auto_login_to_manage',name="center_auto_login_to_manage"),   
    url(r'change_username/$','change_username',name="change_username"),     
    url(r'org_get_reg/$','org_get_reg',name="org_get_reg"),     
    url(r'org_set_reg/$','org_set_reg',name="org_set_reg"),           
)