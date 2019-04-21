# -*- coding: utf-8 -*- 
from django.conf.urls.defaults import patterns,url

urlpatterns=patterns('caiwu.views',
    url(r'^caiwu_main/(?P<org_id>\w+)/$','caiwu_main',name='caiwu_main'),
    url(r'^zijin_fenxi/(?P<org_id>\w+)/$','zijin_fenxi',name='zijin_fenxi'),
    
    
    url(r'^caiwu_edit_zijin/(?P<org_id>\w+)/$','caiwu_edit_zijin',name='caiwu_edit_zijin'),
    url(r'^zijin_category1/(?P<org_id>\w+)/$','zijin_category1',name='zijin_category1'),
    url(r'^zijin_category2/(?P<org_id>\w+)/$','zijin_category2',name='zijin_category2'),
    url(r'^zijin_zijin_his/(?P<org_id>\w+)/$','zijin_his',name='zijin_his'),
    
    url(r'^lirun_fenxi/(?P<org_id>\w+)/$','lirun_fenxi',name='lirun_fenxi'),
    
)