from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from inventory.settings import MEDIA_ROOT
from django.views.generic.base import TemplateView
admin.autodiscover()

js_info_dict = {
     'domain':'djangojs','packages': ('inventory','inventory_v2'),
 }

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'inventory_v2.views.home', name='home'),
    # url(r'^inventory_v2/', include('inventory_v2.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    
    url(r'^i18n/',include('django.conf.urls.i18n')),
    url(r'^jsi18n/$','django.views.i18n.javascript_catalog',js_info_dict),
    #url(r'^jsi18n/(?P<packages>\S+?)/$', 'django.views.i18n.javascript_catalog'),
    
    url(r'^admin/', include(admin.site.urls)),
    url(r'^setlang/$','inventory.common_view.set_language',name="setlang"),
    url(r'^site_media/(?P<path>.*)$','django.views.static.serve',{'document_root':MEDIA_ROOT}),
    url(r'^$', 'depot.views.login',{'slug':None}),
    url(r'^main/$', 'depot.views.main'),
    url(r'^register/$', 'depot.views.register',name="register"),
    url(r'^depot/', include('depot.urls')),
    url(r'^cost/', include('cost.urls')),
    url(r'^caiwu/', include('caiwu.urls')),
    url(r'^export_image/','depot.views.utils.export_image'),
    #url(r'^mobile/', include('depot.urls_mobile')),
    #url(r'^mobile/depot/', include('depot.urls_mobile')),
    
    url(r'^vippass/(?P<path>.*)/$','depot.views.vippass',name='vippass'),
    url(r'^ossi/(?P<path>.*)/$',TemplateView.as_view(template_name='ossi_comment.html')),
    
)

urlpatterns += patterns('',
    ('^test/$', direct_to_template, {'template': 'test.html'}),
    url('^get_units/$', 'depot.views.get_units',name='get_units'),
    url('^set_units/$', 'depot.views.set_units',name='set_units'),
    
)
