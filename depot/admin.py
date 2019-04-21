# -*- coding: utf-8 -*- 
from django.contrib import admin
from depot.models import *

admin.site.register(Organization)
admin.site.register(OrganizationGroup)
admin.site.register(OrgsMembers)
admin.site.register(Warehouse)
admin.site.register(Announce)