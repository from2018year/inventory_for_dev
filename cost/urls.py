# -*- coding: utf-8 -*- 

from django.conf.urls.defaults import patterns,url


'''
    和用户中心交互的的url
'''
urlpatterns=patterns('cost.views',
    url(r'^cost_logs/(?P<org_id>\w+)/$','cost_logs',name='cost_logs'),
    #url(r'^cost_sync/$','cost_sync',name='cost_sync'),
    url(r'^cost_sync_online/$','cost_sync_online',name='cost_sync_online'),
    url(r'^daily_cost_sync_online/$','daily_cost_sync_online',name='daily_cost_sync_online'),
    
    url(r'^cost_view_raw_data/(?P<org_id>\w+)/(?P<his_id>\w+)/$','cost_view_raw_data',name='cost_view_raw_data'),
    url(r'^cost_chukudan/(?P<org_id>\w+)/$','cost_chukudan',name='cost_chukudan'),
    url(r'^cost_profit/(?P<org_id>\w+)/$','cost_profit',name='cost_profit'),
    url(r'^cost_delete_menuItem/(?P<org_id>\w+)/$','cost_delete_menuItem',name='cost_delete_menuItem'),
    #菜品利润分析
    url(r'^menu_item_analysis/(?P<org_id>\w+)/$','menu_item_analysis',name='menu_item_analysis'),
    
    
)