# -*- coding: utf-8 -*- 
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.forms.models import inlineformset_factory
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from depot.models import Organization, OrganizationGroup, Warehouse,\
    UserLevel, OrgsMembers, OrgProfile, Invoice, SnapshotWarehouse,\
    SnapshotWarehouseGood, Goods, MacrosKeyWeb, Announce, OperateLog,\
    CommonPrintTemplate, PrintTemplate, BankAccount, SaleType
from inventory.common import *
from django import db
from depot.views.forms.setting_forms import SettingOrgForm,\
    SettingOrgProfileForm, WarehouseForm, UserForm, UserPWDForm, AnnounceForm,StaffForm,ModifyStaffForm,\
    ResetPasswordForm, PermissionForm, OperateQueryForm, SettingOrgParamForm, AccountSettingForm,\
    SaleTypeSettingForm
from django.forms.models import modelformset_factory
from django.contrib.contenttypes.models import ContentType
from inventory.settings import STYLE, TMP_DIR, EXE_DIR, MEDIA_ROOT
from django.utils.http import urlquote
from caiwu.models import FundsDayHis
import logging
import traceback
from cost.models import MenuItem, CategoryPos
import json
from endless_pagination.decorators import page_template
from api2.tasks import delete_synchis

log=logging.getLogger(__name__)

'''
    进入设置页面
'''
def org_settings(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['root']=org.is_root_node()
    
    return render_to_response("org_settings.html",template_var,context_instance=RequestContext(request))


'''
    设置本部
'''
def settings_org(request,org_id,template_name):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['auto_mode']=auto_mode=OrgProfile.objects.get(org=org).auto_out_stock_mode
    
    if request.method=="GET":
        template_var['org_form']=SettingOrgForm(instance=org)
        OrgProfile.objects.get_or_create(org=org)
        template_var['org_profile_form']=SettingOrgProfileForm(instance=org.profile)
        
    else:
        
        org_form=SettingOrgForm(request.POST.copy(),instance=org)
        org_profile_form=SettingOrgProfileForm(request.POST.copy(),instance=org.profile)
    
        if org_form.is_valid() and org_profile_form.is_valid():
            org=org_form.save()
            org_profile=org_profile_form.save() 
            org_profile.org=org
            org_profile.save()
            return HttpResponseRedirect(reverse('settings_org',args=[org.pk]))
        else:
            print org_form.errors,org_profile_form.errors
            
            
            
            return HttpResponseRedirect(reverse('settings_org',args=[org.pk]))
            
        template_var['org_form']=org_form
        template_var['org_profile_form']=org_profile_form
    return render_to_response(template_name and template_name or "settings/settings_org.html",template_var,context_instance=RequestContext(request))
    

'''
    设置属组
'''
def org_add_group(request,org_id):
    try:
        if request.method=="POST":
            org=Organization.objects.get(pk=org_id)
            group_name=request.POST['group_name']
            og,created=OrganizationGroup.objects.get_or_create(org=org,name=group_name)
            
            return HttpResponse(simplejson.dumps({'id':str(og.pk),'name': og.name}),mimetype='application/json')
    except:
        print traceback.print_exc()
        
        
'''
    查看分部
'''    
def org_branch(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    org_groups={}
    for org in org.get_descendants(include_self=True):
        if org_groups.has_key(org.org_group):
            org_groups[org.org_group].append(org)
        else:
            org_groups[org.org_group]=[org]
    template_var['org_groups']=org_groups
   
    return render_to_response("settings/settings_brach.html",template_var,context_instance=RequestContext(request))

'''
    添加或修改分部
'''
def org_modify(request,org_id,mod_org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    mod_org=None
    if mod_org_id:
        if mod_org_id==org_id:
            mod_org=Organization.objects.get(parent__isnull=True,pk=mod_org_id)
        else:
            mod_org=Organization.objects.get(parent_id=org_id,pk=mod_org_id)
    
    template_var['mod_org']=mod_org

    
    
    
    if request.method=="GET":
        template_var['org_form']=SettingOrgForm(instance=mod_org)
        template_var['org_profile_form']=SettingOrgProfileForm(instance=mod_org and mod_org.profile or None)
        
    else:
        org_form=SettingOrgForm(request.POST.copy(),instance=mod_org)
        org_profile_form=SettingOrgProfileForm(request.POST.copy(),instance=mod_org and mod_org.profile or None)
    
        if org_form.is_valid() and org_profile_form.is_valid():
            child_org=org_form.save(commit=False)
            if not child_org==org:
                child_org.parent=org
            child_org.save()
            
            org_profile=org_profile_form.save(commit=False) 
            org_profile.org=child_org
            org_profile.save()

            
            return HttpResponseRedirect(reverse('org_branch',args=[org.pk]))
            
        template_var['org_form']=org_form
        template_var['org_profile_form']=org_profile_form
        
    
    return render_to_response("settings/org_modify.html",template_var,context_instance=RequestContext(request))

'''
    删除分部
'''
def org_delete(request,org_id):
    try:
        template_var={}
        org=Organization.objects.get(pk=org_id)
        template_var['org']=org
        del_org_id=request.POST.get('del_org_id','0')
        
        Organization.objects.get(parent=org,pk=del_org_id).delete()
        
        return HttpResponse(del_org_id)
    except:
        print traceback.print_exc()


'''
   列出 仓库，仅列出一级
'''
def warehouses(request,org_id,parent_warehouse_id=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    if request.method=="POST":
        warehouse_id=request.POST.get('warehouse_id',None)
        warehouse=Warehouse.objects.get(org=org,pk=warehouse_id)
        warehouse.oindex=1
        warehouse.save()
        
        Warehouse.objects.filter(org=org,parent__isnull=True).exclude(pk=warehouse_id).update(oindex=0)
        
        return HttpResponse(simplejson.dumps({'warehouse_id':warehouse_id}),mimetype='application/json')
    
    if not parent_warehouse_id:
        #仓库管理
        template_var['is_shelf']=False
        template_var['warehouse_display_name']=_(u'仓库')
        warehouses=Warehouse.objects.filter(org=org,parent__isnull=True)
        
        
    else:
        #货架管理
        template_var['is_shelf']=True
        template_var['warehouse_display_name']=_(u'货架')
        template_var['parent_warehouse']=parent_warehouse=Warehouse.objects.get(pk=parent_warehouse_id)
        template_var['parent_warehouses']=parent_warehouse.get_ancestors(include_self=True)
        warehouses=Warehouse.objects.filter(org=org,parent_id=parent_warehouse_id)
        
    template_var['warehouses']=warehouses
    
    return render_to_response("settings/warehouses.html",template_var,context_instance=RequestContext(request))

'''
    新增/修改仓库
'''
def warehouses_modify(request,org_id,parent_warehouse_id=None,mod_warehouse_id=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    parent_warehouse=None
    template_var['warehouse_display_name']=_(u'仓库')
    if parent_warehouse_id:
        template_var['warehouse_display_name']=_(u'货架')
        parent_warehouse=Warehouse.objects.get(org=org,pk=parent_warehouse_id)
        template_var['parent_warehouses']=parent_warehouse.get_ancestors(include_self=True)
        
    mod_warehouse=None
    if mod_warehouse_id:
        mod_warehouse=Warehouse.objects.get(org=org,pk=mod_warehouse_id)
    else:
        
        if not parent_warehouse_id and Warehouse.objects.filter(parent__isnull=True,org=org).count()>=int(request.session['sites']):
            if STYLE=="agile":
                template_var['msg']=('<div style="text-align:center"><div style="display:block;margin:100px auto;padding:20px;background:#eee;border: 3px solid rgb(188, 204, 238);">%s</div></div>'%_(u'您的仓库数已达授权数'))
            else:
                template_var['msg']=('<div style="text-align:center"><div style="display:block;margin:100px auto;padding:20px;background:#eee;border: 3px solid rgb(188, 204, 238);">%s</div></div>'%_(u'您的仓库数已达授权数'))
    
            return render_to_response("settings/warehouses_modify.html",template_var,context_instance=RequestContext(request))
    
        
    if request.method=="GET":
        template_var['s_user']=mod_warehouse and mod_warehouse.charger or ''
        template_var['form']=WarehouseForm(initial={'parent':parent_warehouse_id},instance=mod_warehouse)
    else:
        template_var['s_user']=s_user=request.POST.get('s_user','')
        form=WarehouseForm(request.POST.copy(),initial={'parent':parent_warehouse_id},instance=mod_warehouse)
        if form.is_valid():
            warehouse=form.save(commit=False)
            warehouse.parent=parent_warehouse
            warehouse.org=org
            try:
                warehouse_id=Warehouse.objects.get(org=org,name=form.cleaned_data['name'],parent=parent_warehouse).pk
            except:
                warehouse_id=None
                
            if not mod_warehouse_id:
                if warehouse_id:
                    del form.cleaned_data['name']
                    
                    form.errors['name']= _(u'名称重复1')
                elif warehouse_id!=mod_warehouse_id:
                    del form.cleaned_data['name']
                    
                    form.errors['name']= _(u'名称重复2')
                else:
                    warehouse.save()
                        
                    return parent_warehouse and HttpResponseRedirect(reverse('shelf_list',
                                                                             args=[org.pk,parent_warehouse_id])) or HttpResponseRedirect(reverse('warehouses_list',args=[org.pk]))
                
            else:
                warehouse.save()
                

                return parent_warehouse and HttpResponseRedirect(reverse('shelf_list',
                    args=[org.pk,parent_warehouse_id])) or HttpResponseRedirect(reverse('warehouses_list',args=[org.pk]))
                
    
        template_var['form']=form
    template_var['parent_warehouse']=parent_warehouse
    template_var['mod_warehouse']=mod_warehouse
    return render_to_response("settings/warehouses_modify.html",template_var,context_instance=RequestContext(request))
    

'''
    删除仓库
'''
def warehouses_delete(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        del_warehouses_id=request.POST.get('del_warehouses_id','0')
        
        Warehouse.objects.get(org=org,pk=del_warehouses_id).delete()
        
        return HttpResponse(del_warehouses_id)
    except:
        print traceback.print_exc()


'''
    选择用户
    s_type=0,*
    0--选择本店会员数据
    *--选择本店和指定分店会员
'''
def select_user(request,org_id):
    template_var={}
    org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    
    s_type=int(request.GET.get('s_type',0))
    if s_type:
        pass
    else:
        users=User.objects.filter(om_orgs__org_id=org_id)
    
    template_var['keyword']=keyword=request.GET.get('keyword','') 
       
    if keyword:    
        users=users.filter(Q(username__icontains=keyword)|Q(tel__icontains=keyword))
    template_var['users']=users
        
    return render_to_response("settings/select_user.html",template_var,context_instance=RequestContext(request))


'''
    用户组
'''
def orgs_levels(request,org_id):
    template_var={}

    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['org_permissions']=Permission.objects.exclude(name__startswith="Can").filter(content_type=ContentType.objects.get_for_model(Organization)).order_by('id')
    template_var['warehouse_permissions']=Permission.objects.exclude(name__startswith="Can").filter(content_type=ContentType.objects.get_for_model(Warehouse)).order_by('id')
    
    template_var['warehouses']=Warehouse.objects.filter(org=org,parent__isnull=True)
    template_var['p_len']=template_var['warehouse_permissions'].count() #+template_var['org_permissions'].count()
    
    groupSet=inlineformset_factory(Organization,UserLevel,can_delete=True,extra=1) 

        
    if request.method=="POST":
        groupFormSet=groupSet(request.POST,instance=org)
        if groupFormSet.is_valid():
            groupFormSet.save()
            template_var['groupFormSet']=groupSet(instance=org)
        else:
            template_var['groupFormSet']=groupFormSet
            
    else:
        template_var['groupFormSet']=groupSet(instance=org) 
    
    return render_to_response("settings/orgs_levels.html",template_var,context_instance=RequestContext(request))

'''
    用户
'''
def orgs_users(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    UserFormSet=modelformset_factory(User,fields=('username','user_levels'),extra=0)
    template_var['levels']=levels=org.user_levels.all().order_by('id')
    
    if request.method=="POST":
        userFormSet=UserFormSet(request.POST)
        if userFormSet.is_valid():
            #userFormSet.save()
            for form in userFormSet:
                form.cleaned_data['id'].user_levels.remove(*list(levels.values_list('id',flat=True)))
                form.cleaned_data['id'].user_levels.add(*form.cleaned_data['user_levels'])
        else:
            template_var['userFormSet']=userFormSet
            
        template_var['userFormSet']=userFormSet
    
    else:
        user_id=list(OrgsMembers.objects.filter(org=org).values_list('user',flat=True))
        userFormSet=UserFormSet(queryset=User.objects.filter(id__in=user_id))
        template_var['userFormSet']=userFormSet
        
        
    return render_to_response("settings/orgs_users.html",template_var,context_instance=RequestContext(request))


'''
    添加/编辑用户
'''
def org_user_modify(request,org_id,mod_user_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['levels']=org.user_levels.all().order_by('id')
    
    mod_user=None
    if mod_user_id:
        mod_user=User.objects.get(om_orgs__org=org,pk=mod_user_id)
    template_var['mod_user']=mod_user
    
    if request.method=="GET":
        template_var['userForm']=UserForm(instance=mod_user)
        
    else:
        userForm=UserForm(request.POST,request.FILES,instance=mod_user)
        if userForm.is_valid():
            u=userForm.save(commit=False)
            if not mod_user:
                u.set_password(userForm.cleaned_data['password'])
            u.save()
            userForm.save_m2m()
            OrgsMembers.objects.get_or_create(org=org,user=u)
            template_var['u']=u
            return HttpResponseRedirect(reverse('orgs_users',args=[org_id]))
        template_var['userForm']=userForm
        
    return render_to_response("settings/org_user_modify.html",template_var,context_instance=RequestContext(request))


'''
    删除用户
'''
def orgs_user_delete(request,org_id):
    try:
        template_var={}
        org=Organization.objects.get(pk=org_id)
        template_var['org']=org
        user_del_id=request.POST.get('user_del_id','0')
        if org.om_members.filter(user__is_active=True).count()>1:
            User.objects.get(om_orgs__org=org,pk=user_del_id).delete()
            return HttpResponse(user_del_id)
        else:
            return HttpResponse(_(u'必须保留一个用户以登陆系统'))
        
    except:
        print traceback.print_exc()
        
'''
    禁止用户登录
'''
def orgs_deny_login(request,org_id):
    try:
        org=Organization.objects.get(pk=org_id)
        user_id=request.POST['user_id']
        user=User.objects.get(om_orgs__org=org,pk=user_id)
        user.is_active=False
        user.save()
        return HttpResponse(user_id)
    except:
        print traceback.print_exc()

'''
    允许用户登录
'''
def orgs_allow_login(request,org_id):
    org=Organization.objects.get(pk=org_id)
    user_id=request.POST['user_id']
    user=User.objects.get(om_orgs__org=org,pk=user_id)
    user.is_active=True
    user.save()
    return HttpResponse(user_id)
        
        
'''
    修改用户名密码
'''
def org_user_modify_pwd(request,org_id,mod_user_id):
    template_var={}
    template_var['org']=org=Organization.objects.get(pk=org_id)
    user=User.objects.get(om_orgs__org=org,pk=mod_user_id)
    template_var['user']=user
    if request.method=="GET":
        form=UserPWDForm(initial={'user':user.pk,'opwd':False})
        template_var['form']=form
        
    else:
        form=UserPWDForm(request.POST.copy(),initial={'user':user.pk,'opwd':False})
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            template_var['success']=True
        template_var['form']=form
    return render_to_response("settings/org_user_modify_pwd.html",template_var,context_instance=RequestContext(request))

'''
    修改用户名密码-自己修改
'''
def org_user_modify_pwd2(request,org_id,mod_user_id):
    template_var={}
    template_var['org']=org=Organization.objects.get(pk=org_id)
    user=User.objects.get(om_orgs__org=org,pk=mod_user_id)
    template_var['user']=user
    template_var['opwd']=True
    if request.method=="GET":
        form=UserPWDForm(initial={'user':user.pk,'opwd':True})
        template_var['form']=form
        
    else:
        form=UserPWDForm(request.POST.copy(),initial={'user':user.pk,'opwd':True})
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            template_var['success']=True
        template_var['form']=form
    return render_to_response("settings/org_user_modify_pwd.html",template_var,context_instance=RequestContext(request))


'''
    备份中心
''' 

def backup(request,org_id):
    template_var={}
    template_var['org']=org=Organization.objects.get(pk=org_id)
    
    backups=[]
    BACKUP_DIR=os.path.join(TMP_DIR,'../backup')
    
    if not os.path.exists(BACKUP_DIR):
        os.mkdir(BACKUP_DIR)
        
    #遍历当前的备份
    list_dirs=os.walk(BACKUP_DIR)
    for root, dirs, files in list_dirs: 
        for f in files:
            backups.append('%s'%f.decode('gbk'))
    
    template_var['backups']=backups
    return render_to_response("settings/backup.html",template_var,context_instance=RequestContext(request))

'''
    做备份
'''
def do_backup(request,org_id):
    try:
        backup(request,org_id)
    except:
        print traceback.print_exc()
    try:
        BACKUP_DIR=os.path.join(TMP_DIR,'../backup')
        cstr="\"%smysqldump.exe\" --default-character-set=utf8 \
                --ignore-table=inventory_v2.macros_key_hj \
                --ignore-table=inventory_v2.menu_item \
                --ignore-table=inventory_v2.descriptors_menu_item_slu \
                --ignore-table=inventory_v2.item_main_group \
                --ignore-table=inventory_v2.menu_item_handle \
                --ignore-table=inventory_v2.descriptors_menu_item_slu_handle \
                --ignore-table=inventory_v2.item_main_group_handle \
                --ignore-table=inventory_v2.history_day_end \
                --ignore-table=inventory_v2.total_statistics \
                --ignore-table=inventory_v2.history_order_detail \
                --ignore-table=inventory_v2.history_order_head \
                 -u%s -p%s -P%s -h%s %s"%(EXE_DIR,DATABASES['default']['USER'],
                                                                     DATABASES['default']['PASSWORD'],
                                                                     DATABASES['default']['PORT'],
                                                                     DATABASES['default']['HOST'],
                                                                     DATABASES['default']['NAME'])
        
        
        if not os.path.exists(BACKUP_DIR):
            os.mkdir(BACKUP_DIR) 
        
        fname=datetime.date.today().strftime('%Y-%m-%d')    
        cstr="cmd /c %s > \"%s\""%(cstr,os.path.join(TMP_DIR,'../backup/%s'%fname).replace('\\','/')) 
        print cstr
        f=os.popen(cstr)
        msg=f.read()
        f.close()
        
                
        return HttpResponse(fname)
    except:
        print traceback.print_exc()
        
'''
    下载备份
'''
def down_backup(request,org_id):
    try:
        def readFile(filename,buf_size=262144):
            f=open(filename,'rb')
            while True:
                c=f.read(buf_size)
                if c:
                    yield c
                else:
                    break
            f.close()
        
        backup=request.GET.get('backup',None)

        pwd=os.path.join(EXE_DIR,'../backup/%s'%backup)
        
        response=HttpResponse(readFile(pwd),mimetype='application/octet-stream') 
        response['Content-length']=os.path.getsize(pwd)
        response['Content-Disposition'] = u'attachment;filename=%s'%urlquote(backup)
        return response
    except:
        print(traceback.format_exc())
        
        
'''
    删除备份
'''
def del_backup(request,org_id):
    try:
        backup=request.POST.get('backup',None)
        if backup:
            path=os.path.join(EXE_DIR,'../backup/%s'%backup)
            os.remove(path)
            
        return HttpResponse(backup)
    except:
        print traceback.print_exc()
        
'''
    删除所有单据 del_all_receipt
'''        
def del_all_receipt(request,org_id):
    try:
        from cost.models import SyncStamp,SyncHis
        invoices = Invoice.objects.filter(org=org_id)
        while invoices.count():
            invoices.delete()

        snapshots = SnapshotWarehouse.objects.filter(org=org_id)
        while snapshots.count():
            snapshots.delete()
        
        # GoodsUseRate.objects.filter(org=org_id).delete()
        fundsdayhis = FundsDayHis.objects.filter(org=org_id)
        while fundsdayhis.count():
            fundsdayhis.delete()
        
        syncstamp = SyncStamp.objects.filter(org=org_id)
        while syncstamp.count():
            syncstamp.delete()

        synchis = SyncHis.objects.filter(org=org_id)
        # while synchis.count():
            # synchis.delete()
        for his in synchis:
            delete_synchis.apply_async(args=(his.id,))



        #删除菜品对应表
        menu_item = MenuItem.objects.filter(org=org_id)
        while menu_item.count():
            menu_item.delete()

        category = CategoryPos.objects.filter(org=org_id)
        while category.count():
            category.delete()
        
        try:
            org=Organization.objects.get(slug=org_id)
        except:
            org=Organization.objects.get(pk=org_id)
        
        for good in Goods.objects.filter(org=org):
            good.nums=0
            good.add_nums=0
            good.save()
            
        return HttpResponse(backup)
    except:
        print traceback.print_exc()
        
'''
    使用备份
'''
def use_backup(request,org_id):
    try:
        backup=request.POST.get('backup',None)
        if backup:
            #mysql -uroot -pagile -P3308 -h127.0.0.1 -Dmember_v2 <  ..\backup\2013-09-20
            
            cstr="\"%smysql.exe\" --default-character-set=utf8 -u%s -p%s -P%s -h%s -D%s"%(EXE_DIR,DATABASES['default']['USER'],
                                                                     DATABASES['default']['PASSWORD'],
                                                                     DATABASES['default']['PORT'],
                                                                     DATABASES['default']['HOST'],
                                                                     DATABASES['default']['NAME'])
        
        
            if not os.path.exists(os.path.join(EXE_DIR,'../backup')):
                os.mkdir(os.path.join(EXE_DIR,'../backup')) 
             
            db.close_connection()
            
            fname=datetime.date.today().strftime('%Y-%m-%d')    
            cstr="cmd /k %s < \"%s\""%(cstr,os.path.join(EXE_DIR,'../backup/%s'%backup).replace('\\','/')) 
            print cstr
            f=os.popen(cstr)
            msg=f.read()
            f.close()
            
        return HttpResponse(backup)
    except:
        print traceback.print_exc()
        
'''
    下载还原工具
'''
def down_backup_tools(request,org_id):
    f=open('%shuanyuan-kucun.bat'%EXE_DIR,'r+')
    flist=f.readlines()
    f.close()
    flist[3]=("set MEMBER=%s\n"%MEDIA_ROOT).replace('/','\\')
    
    str="\r\n".join(flist)
    
    response=HttpResponse(str,mimetype='application/octet-stream') 
    response['Content-length']=len(str)
    response['Content-Disposition'] = u'attachment;filename=%s'%urlquote('huanyuan-kucun.bat')
    return response


'''
    系统升级
'''
def version_update(request,org_id):
    template_var={}
    template_var['org']=Organization.objects.get(pk=org_id)
    return render_to_response("settings/update.html",template_var,context_instance=RequestContext(request))


'''
    查看授权
'''
def org_auth_web(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    key_arr=[]
    if org.get_root_org()==org:
        keys=MacrosKeyWeb.objects.filter(org=org)
        
        for key in keys:
            res,_date,sites=fetch_key_web(key)
            key_arr.append([key.key_str,key.event_date,res,_date,sites])
            
    
        template_var['key_arr']=key_arr
    return render_to_response("settings/org_auth_web.html",template_var,context_instance=RequestContext(request))


def org_import_auth(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    if request.method=="POST":
        template_var['ma']=ma=request.POST.get('ma','')
        res,date,sites=fetch_key_web(ma,org_id)
        if res:
            template_var['msg']=_(u"<span style='color:red'>注册码校验错误，错误号%s<span>")%res
        else:
            update_key_web(ma,org)
            template_var['msg']=_(u"您已注册成功,允许商家数为%(shuang)s,许可期限为%(xu)s")%{'shuang':sites,'xu':("%s"%date)[:10]}
            template_var['success']=True
            org.expiry_date=date
            org.save()
            
            request.session['sites']=sites
            request.session['expired_date']=date
            
    keys=MacrosKeyWeb.objects.filter(org=org)
    if not keys.exists():
        #没有key的时候，自动生成1周的免费使用期
        MacrosKeyWeb.objects.create(org=org,key_str=create_ma_web(org))
        keys=MacrosKeyWeb.objects.filter(org=org)
    
    key=keys[0]
    res,_date,sites=fetch_key_web(key)
    
    #key,ind,res,_date,sites=fetch_key()
    template_var['sites']=sites
    template_var['ma']=key.key_str
    if not key:
        template_var['res']=_(u'您的试用期限已到')
    else:
        if res==0:
            template_var['res']=_(u'您的到期时间为%s,如需重新注册')%(("%s"%_date)[:10])
        elif res==3:
            template_var['res']=_(u'您的软件已过期,的到期时间为%s')%(("%s"%_date)[:10])
        else:
            template_var['res']=_(u'注册码不正确')
            
    return render_to_response("settings/register.html",template_var,context_instance=RequestContext(request))



'''
    公司公告
'''
def org_announce(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['announces']=Announce.objects.filter(org=org)
    
    return render_to_response("settings/org_announces.html",template_var,context_instance=RequestContext(request))


'''
    新增公告
'''
def org_announce_modify(request,org_id,announce_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    announce=None
    if announce_id:
        announce=Announce.objects.get(pk=announce_id)
        
    if request.method=="GET":
        template_var['form']=AnnounceForm(instance=announce)
    else:
        form=AnnounceForm(request.POST.copy(),instance=announce)
        if form.is_valid():
            announce=form.save(commit=False)
            announce.org=org
            announce.user=request.user
            announce.save()
            
            return HttpResponseRedirect(reverse('org_announce',args=[org.pk]))
        else:
            template_var['form']=form

    return render_to_response("settings/org_announce_modify.html",template_var,context_instance=RequestContext(request))


'''
    删除公告
'''
def org_announce_delete(request,org_id):
    announce_id=request.POST.get('announce_id')
    
    announce=Announce.objects.get(pk=announce_id)
    announce.delete()
    
    return HttpResponse(announce_id)

'''
   员工设置
'''
def staff_list(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    users = User.objects.filter(om_orgs__org=org)
    for user in users:
        if user.is_org_superuser(org.pk):
            user.is_superior = True
        else:
            user.is_superior = False
    template_var['users'] = users

    return render_to_response("settings/staff_list.html",template_var,context_instance=RequestContext(request))

#添加员工
def add_staff(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['staff_form'] = staff_form = StaffForm(org)

    if request.method == "POST":
        form=StaffForm(org,request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            user.user_levels.add(form.cleaned_data['user_levels'])
            user.save()
            OrgsMembers.objects.create(org=org,user=user)
            form.save_m2m()

            #生成日志
            created_user = request.user.username

            content = _(u"添加了员工%s") %user.username.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)

            template_var['style'] = 'text-success'
            template_var['message'] = '新增成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))
        else:
            template_var['staff_form']=form


    return render_to_response("settings/add_staff.html",template_var,context_instance=RequestContext(request))

def staff_modify(request,org_id,staff_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)


    if staff_id:
        staff = User.objects.get(pk=staff_id)

    if request.method == "GET":
        template_var['staff_form']=ModifyStaffForm(org=org,instance=staff)

    else:
        form=ModifyStaffForm(org,request.POST.copy(),instance=staff)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            user.user_levels.clear()
            user.user_levels.add(form.cleaned_data['user_levels'])
            form.save_m2m()

            #生成日志
            created_user = request.user.username

            content = _(u"修改了员工%s的信息") %user.username.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)


            template_var['style'] = 'text-success'
            template_var['message'] = '修改成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))
        #else:
            template_var['staff_form']=form




    return render_to_response("settings/modify_staff.html",template_var,context_instance=RequestContext(request))

def staff_delete(request,org_id,staff_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if staff_id:
        staff = User.objects.get(pk=staff_id)

        content = _(u"删除了员工%s") %staff.username.encode('utf8')

        staff.user_levels.clear()
        staff.delete()

        #生成日志
        created_user = request.user.username
        OperateLog.objects.create(created_user=created_user,content=content,org=org)

    return HttpResponseRedirect(reverse('staff_list',args=[org.uid]))

def staff_deactivate(request,org_id,staff_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if staff_id:
        staff = User.objects.get(pk=staff_id)
        if staff.is_active == 0:
            staff.is_active = 1

            #生成日志
            created_user = request.user.username

            content = _(u"启用了员工%s") %staff.username.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)
        else:
            staff.is_active = 0

            #生成日志
            created_user = request.user.username

            content = _(u"停用了员工%s") %staff.username.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)

        staff.save()
        return HttpResponseRedirect(reverse('staff_list',args=[org.uid]))

def reset_password(request,org_id,staff_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if request.method == "GET":
        template_var['form']=form=ResetPasswordForm()
    else:
        staff = User.objects.get(pk=staff_id)
        form=ResetPasswordForm(request.POST.copy())
        if form.is_valid():
            staff.set_password(form.cleaned_data['password'])
            staff.save()

            #生成日志
            created_user = request.user.username

            content = _(u"重置了员工%s的密码") %staff.username.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)

            template_var['style'] = 'text-success'
            template_var['message'] = '重置成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))
        else:
            template_var['form']=form

    
    return render_to_response("settings/resetpw_staff.html",template_var,context_instance=RequestContext(request))


'''
    操作权限设置
'''
def permission_list(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['roles']=roles=UserLevel.objects.filter(org=org)

    #template_var['caigoushenqing_perms']=roles.permissions.filter(codename__startswith='caigoushenqing')

    return render_to_response("settings/permission_list.html",template_var,context_instance=RequestContext(request))

def add_permission_role(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['roles']=roles=UserLevel.objects.filter(org=org)
    template_var['permissionform']=permissionform=PermissionForm()

    if request.method == "POST":
        form=PermissionForm(request.POST.copy())
        if form.is_valid():
            all_data = []
            try:
                user_level = form.cleaned_data.pop("user_level")
            except KeyError:
                perm_data = {}
                return HttpResponse("请输入员工名称")
            for data in form.cleaned_data:
                all_data.extend(form.cleaned_data[data])
            
            role = UserLevel.objects.create(name=user_level,org=org)
            for data in all_data:
                print 'data:',data
                permission = Permission.objects.get(codename=data)
                role.permissions.add(permission)

            #生成日志
            created_user = request.user.username

            content = _(u"添加了权限角色%s") %role.name.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)

            template_var['style'] = 'text-success'
            template_var['message'] = '新增成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))




    return render_to_response("settings/add_permission.html",template_var,context_instance=RequestContext(request))

def permission_role_detail(request,role_id):
    template_var = {}
    user_level = UserLevel.objects.get(id=role_id)
    template_var['permissions']=permissions=user_level.permissions.filter(Q(codename__icontains='_add')|Q(codename__icontains='_modify')|Q(codename__icontains='_delete')|Q(codename__icontains='_confirm')|Q(codename__icontains='_query')|Q(codename__icontains='_export')|Q(codename__icontains='_print')|Q(codename__icontains='huishouzhan')|Q(codename__icontains='_ui'))
    return render_to_response("settings/role_detail.html",template_var,context_instance=RequestContext(request))

def modify_permission_role(request,org_id,role_id):
    template_var = {}

    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['role']=role=UserLevel.objects.get(id=role_id)
    template_var['permissionform']=permissionform=PermissionForm()
    permissions = role.get_userlevel_permissions()

    data={}

    for permission in permissions:
        data[permission.id] = permission.codename

    template_var['jsondata'] = json.dumps(data)

    if request.method == "POST":
        form=PermissionForm(request.POST.copy())
        if form.is_valid():
            all_data = []
            role.permissions.clear()
            for data in form.cleaned_data:
                all_data.extend(form.cleaned_data[data])

            for data in all_data:
                               
                permission = Permission.objects.get(codename=data)
                role.permissions.add(permission)

            #生成日志
            created_user = request.user.username

            content = _(u"修改了%s的权限") %role.name.encode('utf8')
            OperateLog.objects.create(created_user=created_user,content=content,org=org)

            template_var['style'] = 'text-success'
            template_var['message'] = '修改成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))


    return render_to_response("settings/modify_permission.html",template_var,context_instance=RequestContext(request))


def delete_permission_role(request,org_id,role_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    role = UserLevel.objects.get(id=role_id)
    content = _(u"删除了权限角色%s") %role.name.encode('utf8')

    role.delete()

    #生成日志
    created_user = request.user.username
    OperateLog.objects.create(created_user=created_user,content=content,org=org)

    return HttpResponseRedirect(reverse('permission_list',args=[org.uid]))


@page_template('settings/operate_log_index.html')
def operate_log(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    logs = OperateLog.objects.filter(org=org).order_by('-created_time')
    template_var['logs'] = logs

    template_var['form']=form=OperateQueryForm()

    if request.method == "POST":
        form = OperateQueryForm(request.POST.copy())
        if form.is_valid():
            logs=OperateLog.objects.filter(org=org,created_time__gte=form.cleaned_data['date_from'],created_time__lte=form.cleaned_data['date_to']+datetime.timedelta(1))
            if form.cleaned_data['created_user']:
                logs = logs.filter(created_user__icontains=form.cleaned_data['created_user'])

            if form.cleaned_data['content']:
                logs = logs.filter(content__icontains=form.cleaned_data['content'])

            template_var['logs'] = logs


    if extra_context is not None:
            template_var.update(extra_context)


    return render_to_response("settings/operate_log.html",template_var,context_instance=RequestContext(request))


#参数设置
def settings_param(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['org_profile_form']=org_profile_form=SettingOrgParamForm(instance=org.profile)

    if request.method == "POST":
        form = SettingOrgParamForm(request.POST.copy(),instance=org.profile)

        if form.is_valid():
            form.save()
            content = _(u"修改了参数设置")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)
            return HttpResponseRedirect(reverse("org_settings",args=[org.uid]))
        else:
            print form.errors

    return render_to_response("settings/param.html",template_var,context_instance=RequestContext(request))

def print_template_setting(request,org_id,common_template_id=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    if not common_template_id:
        common_template_id = 1

    template_var['print_template_list']=print_template_list=PrintTemplate.objects.filter(org=org,common_template=common_template_id)
    template_var['common_template']=common_template=CommonPrintTemplate.objects.get(pk=common_template_id)

    return render_to_response("print_template/setting_template.html",template_var,context_instance=RequestContext(request))


#银行账户
def settings_account(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['accounts']=accounts=BankAccount.objects.filter(org=org)
    return render_to_response("settings/account_setting.html",template_var,context_instance=RequestContext(request))

def change_account_status(request,org_id,account_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    account = BankAccount.objects.get(pk=account_id)
    account.status = not account.status
    account.save()
    return HttpResponseRedirect(reverse("settings_account",args=[org.uid]))

def add_bank_account(request,org_id,account_id=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    account=None

    if account_id:
        account = BankAccount.objects.get(pk=account_id)
        template_var['form']=form=AccountSettingForm(instance=account)
    else:
        template_var['form']=form=AccountSettingForm()

    if request.method == "POST":
        form = AccountSettingForm(request.POST.copy(),instance=account)

        if form.is_valid():
            account = form.save(commit=False)
            account.org = org
            account.save()
            template_var['style'] = 'text-success'
            template_var['message'] = '操作成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))

    return render_to_response("settings/add_account.html",template_var,context_instance=RequestContext(request))

#销售类型设置
def sale_type_setting(request,org_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['sale_types']=sale_types=SaleType.objects.filter(org=org)

    return render_to_response("settings/sale_type_setting.html",template_var,context_instance=RequestContext(request))

def add_sale_type(request,org_id,sale_type_id=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    sale_type=None

    if sale_type_id:
        sale_type = SaleType.objects.get(pk=sale_type_id)
        template_var['form']=form=SaleTypeSettingForm(instance=sale_type)
    else:
        template_var['form']=form=SaleTypeSettingForm()

    if request.method == "POST":
        form = SaleTypeSettingForm(request.POST.copy(),instance=sale_type)

        if form.is_valid():
            new_type = form.save(commit=False)
            new_type.org = org
            new_type.save()
            template_var['style'] = 'text-success'
            template_var['message'] = '操作成功'
            return render_to_response("settings/settings_info.html",template_var,context_instance=RequestContext(request))

    return render_to_response("settings/add_sale_type.html",template_var,context_instance=RequestContext(request))


def delete_sale_type(request,org_id,sale_type_id):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    sale_type = SaleType.objects.get(pk=sale_type_id)
    sale_type.delete()

    return HttpResponseRedirect(reverse('sale_type_setting',args=[org.uid]))