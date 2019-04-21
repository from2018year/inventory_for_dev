# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.core.cache import cache
from cost.models import CategoryPos
from django.utils.translation import ugettext as _
from gicater.utils.encrypt import encrypt_half_md5,valid_half_encrypt
from django.contrib.auth import authenticate,login as auth_login
from django.template.context import RequestContext
from django.utils import simplejson
from django.db.models import Q
import time
import traceback
from depot.models import Organization, UserLevel, OrgsMembers, MacrosKeyWeb,\
    Warehouse, Supplier, Customer, ConDepartment, Category, OrgProfile, Unit,\
    Goods, SyncTableVer
from datetime import datetime
import logging
from inventory.common import create_ma_web, fetch_key_web, update_key_web
from django.views.decorators.csrf import csrf_exempt

from django import conf
from django.db import transaction

from tasks import sync_menu_stock

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
log=logging.getLogger(__name__)

@csrf_exempt
@transaction.autocommit
def add(request):
    if request.GET.get('username',None):
        username=request.GET.get('username')
        if User.objects.filter(username=username).exists():
            return HttpResponse(simplejson.dumps({'valid':False,'message': _(u'用户名已存在')}),mimetype='application/json')
        return HttpResponse(simplejson.dumps({'valid':True,'message': _(u'用户名可以使用')}),mimetype='application/json')
    
    if request.GET.get('org_slug',None):
        slug=request.GET.get('org_slug')
        if Organization.objects.filter(slug__iexact=slug).exists():
            return HttpResponse(simplejson.dumps({'valid':False,'message': _(u'二级域名已存在')}),mimetype='application/json')
        return HttpResponse(simplejson.dumps({'valid':True,'message': _(u'二级域名可以使用')}),mimetype='application/json')
        
    template_var={}
    
    t=request.GET.get('t','')
    token=request.GET.get('token','')
    
    now_time=int(time.time())
    if request.method=="GET":
        if (now_time-int(t))>30 or not valid_half_encrypt("add", token, t):
            return HttpResponse(_(u'无效链接'))
    else:
        valid=request.GET.get('valid','')
        if valid!='skip' and ((now_time-int(t))>300 or not valid_half_encrypt("add", token, t)):
            return HttpResponse(simplejson.dumps({"error":_(u'网页链接已失效，请重新打开此页面')}),mimetype='application/json')
        
        try:
            username=request.POST.get('username')
            password=request.POST.get('password')
            if not password or password=='!':
                password='123456'
            org_name=request.POST.get('org_name')
            org_slug=request.POST.get('org_slug')
            org_slug=(org_slug and [org_slug] or [None])[0]
            org_phone=request.POST.get('org_phone','')
            org_address=request.POST.get('org_address','')
            style=request.POST.get('style')
            nyear=int(request.POST.get('nyear'))
            sites=int(request.POST.get('sites'))
            org_guid=request.POST.get('org_guid')
            remark=request.POST.get('remark')
            print request.POST
            
            '''
            ' 如果餐厅ID已经使用，则禁止创建新店
            '''
            if org_guid and Organization.objects.filter(org_guid=org_guid):
                return HttpResponse(simplejson.dumps({'error':u'相同的餐厅ID已经关联店铺，不能新建'}),mimetype='application/json')
            
            try:
                User.objects.get(username=username)
                return HttpResponse(simplejson.dumps({'error':u'用户名已存在，不能新建'}),mimetype='application/json')
            except:
                pass
            
            org=Organization.objects.create(slug=org_slug,org_guid=org_guid,style=style,org_name=org_name,stores_address=org_address,phone=org_phone,remark=remark)
            try:
                org.profile
            except:
                OrgProfile.objects.get_or_create(org=org)
            
            user=User.objects.create_user(username=username, email=None,password=((password=='!') and [None] or [password])[0])
            OrgsMembers.objects.create(user=user,org=org,level=0,superior=True)
            key_str=create_ma_web(org,nyear=nyear,sites=sites)
            key=MacrosKeyWeb.objects.create(org=org,key_str=key_str)
            status,expired_date,sites=fetch_key_web(key)
            
            Warehouse.objects.create(org=org,name=_(u'总仓'),oindex=True)
            Supplier.objects.create(org=org,name=_(u'默认供货商'),abbreviation='mrghs')
            Customer.objects.create(org=org,name=_(u'默认客户'),abbreviation='mrkh')
            ConDepartment.objects.create(org=org,name=_(u'默认部门'),abbreviation='mrbm')
            
            Category.objects.get_or_create(parent__isnull=True,org=org.get_root_org(),defaults={'name':_(u'全部分类')})
            
            org.sync_center()
            
            if password=='!':
                return HttpResponse(simplejson.dumps({'org_id':org.id,'key_str':key_str,'expired_date':expired_date.strftime('%Y-%m-%d'),'sites':sites}),mimetype='application/json')
            else:
                if style=='english' and False:
                    return HttpResponse(simplejson.dumps({'org_id':org.id,'key_str':key_str,'expired_date':expired_date.strftime('%Y-%m-%d'),'sites':sites,
                                                      'org_name':org_name,'slug':org_slug,'username':username,'password':password,"message":u"商家名称:%s<br/>网址：%s<br/>用户名:%s<br/>密码：%s"%(org_name,getattr(conf.settings,'ENGLISH_URL',"http://182.92.104.138/"),username,password)}),mimetype='application/json')
                else:
                    print {'org_id':org.id,'key_str':key_str,'expired_date':expired_date.strftime('%Y-%m-%d'),'sites':sites,
                                                      'org_name':org_name,'slug':org_slug,'username':username,'password':password,"message":u"商家名称:%s<br/>网址：%s<br/>用户名:%s<br/>密码：%s"%(org_name,getattr(conf.settings,style=='gicater' and 'DEFAUT_URL' or 'AGENT_URL',"http://www.weipython.com/"),username,password)}
                    return HttpResponse(simplejson.dumps({'org_id':org.id,'key_str':key_str,'expired_date':expired_date.strftime('%Y-%m-%d'),'sites':sites,
                                                      'org_name':org_name,'slug':org_slug,'username':username,'password':password,"message":u"商家名称:%s<br/>网址：%s<br/>用户名:%s<br/>密码：%s"%(org_name,getattr(conf.settings,style=='gicater' and 'DEFAUT_URL' or 'AGENT_URL',"http://www.weipython.com/"),username,password)}),mimetype='application/json')
            
        except:
            print traceback.print_exc()
            return HttpResponse(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')
    return render_to_response("api2_new.html",template_var,context_instance=RequestContext(request))

def list_org(request):
    template_var={}
    
    t=request.GET.get('t','')
    token=request.GET.get('token','')
    
    now_time=int(time.time())
    if request.method=="GET":
        if (now_time-int(t))>300 or not valid_half_encrypt("list", token, t):
            return HttpResponse(_(u'无效链接'))
        
    else:

        if request.POST.get('mod_org',''):
            mod_org=request.POST.get('mod_org')
            org=Organization.objects.get(pk=mod_org)
            qixian=int(request.POST.get('qixian'))
            fendian=int(request.POST.get('fendian'))
            
            
            if qixian or fendian:
                new_ma=create_ma_web(org, qixian, add_sites=fendian) 
                res,_day,sites=fetch_key_web(new_ma,org.pk)
                log.debug("after new expired date is %s,sites is %s"%(_day,sites))
        
                update_key_web(new_ma,org)
                log.debug(u"user %s change %s auth success"%(request.user,org.org_name))
                
                
            return HttpResponse(simplejson.dumps({'success':True}),mimetype='application/json')
        elif request.POST.get('passwd_mod_org',''):
           
            passwd_mod_org=request.POST.get('passwd_mod_org')
            org=Organization.objects.get(pk=passwd_mod_org)
            passwd=request.POST.get('passwd')
            
            user=org.get_charger()
            if isinstance(user, User):
                user.set_password(passwd)
                user.save()
            
                return HttpResponse(simplejson.dumps({'message':_(u'成功修改用户%(user)s密码为%(passwd)s'%{'user':user.username,'passwd':passwd})}),mimetype='application/json')
            else:
                return HttpResponse(simplejson.dumps({'message':_(u'未能检索到管理员')}),mimetype='application/json')
            
        template_var['keyword']=keyword=request.POST.get('keyword','').strip()
        orgs=Organization.objects.all().order_by('parent',"-insert_date")
        
        if keyword:
            orgs=orgs.filter(Q(org_name__icontains=keyword)|Q(members__username=keyword)|Q(org_guid__istartswith=keyword)).distinct()
        
        template_var['orgs']=orgs
    return render_to_response("api2_list.html",template_var,context_instance=RequestContext(request))


@csrf_exempt
# @transaction.commit_on_success
def sync_menu_item(request):
    '''
    '    接受用户中心菜品
    '''
    item_change=request.GET.get('item_change')
    # item_change = 'True'
    guid=request.GET.get('guid')
    
    if not (item_change or guid):
        return HttpResponse(simplejson.dumps({'status':0,'description':_(u'同步在线库存参数错误')}),mimetype='application/json')
    org = Organization.objects.get(org_guid=guid)

    try:
        INDUSTRY= (org.style=='retail') and 'retail' or 'restaurant'
            
        if request.method=="GET":
            return HttpResponse(simplejson.dumps({'status':1,'description':_(u'OK')}),mimetype='application/json')
        else:
            data=request.POST.get('item_data')
            # f = open("E:\sync_menu.txt", "r")
            # data = f.read()

            sync_status = cache.get("sync_menu_item_%s" % org.id)
            if sync_status == 1:
                return HttpResponse(simplejson.dumps({'status':0, 'description': _(u'正在同步')}))
            else:
                cache.set("sync_menu_item_%s" % org.id, 1, 300)

            try:
                data_list=simplejson.loads(data)
                # data_list = eval(data)
                '''
                ' 这里没从明白是为什么，还会出现为unicode的情况
                '''
                if isinstance(data_list, unicode):
                    data_list=simplejson.loads(data_list)
                
            except:
                print(traceback.print_exc())
                return HttpResponse(simplejson.dumps({'status':0,'description':_(u'同步在线库存参数错误dumps')}),mimetype='application/json')
            if data_list:
                try:
                    if INDUSTRY == "retail":
                        is_retail = True
                    else:
                        is_retail = False


                    CategoryPos.objects.filter(org=org).update(processing=1)
                    data_count = 0
                    for record in data_list:
                        if data_count == len(data_list) - 1:
                            is_last_record = True
                        else:
                            data_count = data_count + 1
                            is_last_record = False

                        sync_menu_stock.apply_async(args=(org.id, is_retail, record, is_last_record))
                except:
                    print(traceback.print_exc())
                    return HttpResponse(simplejson.dumps({'status':0, 'description':u'加入任务队列失败'}), mimetype='application/json')

        return HttpResponse(simplejson.dumps({'status':1,'description':u'更新在线库存完毕'}),mimetype='application/json')
       
    
    except:
        # transaction.rollback()
        print traceback.print_exc()
        return HttpResponse(simplejson.dumps({'status':0,'description':_(u'未注册的在线库存系统')}),mimetype='application/json')

from Crypto.Cipher import AES
import zipfile
import StringIO

key = 'COOLROIDagilePOS'
iv =  b'0000000000000000'
mode = AES.MODE_CBC

@csrf_exempt
def pos_sync(request):
    if request.method=="GET":
        return render_to_response("pos_sync.html",{},context_instance=RequestContext(request))
    
    else:
        try:
            if request.GET.get('noaes'):
                post_data=request.POST.copy()
            else:
                decryptor = AES.new(key, mode,iv)
                ciphertext = decryptor.decrypt(request.body)
                post_data=simplejson.loads(ciphertext.split('\0')[0].strip())
                
            guid=post_data.get('guid',None)
            org=Organization.objects.get(org_guid=guid)
            
            try:
                stv,created=SyncTableVer.objects.get_or_create(org=org)
            except:
                print traceback.print_exc()
                ids=list(SyncTableVer.objects.filter(org=org).order_by('-id').values_list('id',flat=True))[1:]
                SyncTableVer.objects.filter(id__in=ids).delete()
                stv=SyncTableVer.objects.get(org=org)
            
            s = StringIO.StringIO()
            zf = zipfile.ZipFile(s, "w")
            
            versions=[]
            if "menu_item" in post_data.keys():
                if post_data['menu_item']!=stv.good_ver:
                    versions.append('menu_item:%s'%stv.good_ver)
                    products=Goods.objects.filter(org=org,item_type=1).select_related()
                    
                    base_number=1000000000000
                    descriptors_menu_item_slu_set=set()
                    item_main_group_set=set()
                    product_list=[]
                    
                    for product in products:
                        second_group_obj=product.category
                        if second_group_obj.level==1:
                            second_group={'id':base_number+second_group_obj.id,'name':second_group_obj.name}
                            main_group={'id':second_group_obj.id,'name':second_group_obj.name}
                        else:
                            second_group={'id':second_group_obj.id,'name':second_group_obj.name}
                            main_group={'id':second_group_obj.parent.id,'name':second_group_obj.parent.name}
                            
                        
                        descriptors_menu_item_slu_set.add((str(second_group['id']),second_group['name']))
                        item_main_group_set.add((str(main_group['id']),main_group['name'],str(second_group['id'])))
                    
                        _product_list=[str(product.id),product.name,str(second_group['id']),product.abbreviation,str(product.sale_price_ori),str(product.price_ori),product.unit and product.unit.unit or '']
                        for unit in Unit.objects.filter(org=org,good=product):
                            _product_list.extend([str(unit.sale_price),str(unit.price),unit.unit])
                            
                        _product_list.extend(['0']*12)
                        product_list.append(_product_list[:19])
            
                    descriptors_menu_item_str_list=['dmi_slu_id,dmi_slu_name']
                    for descriptors_menu_item_slu in descriptors_menu_item_slu_set:
                        descriptors_menu_item_str_list.append(u','.join(descriptors_menu_item_slu).encode('utf8'))
                    zf.writestr('descriptors_menu_item_slu','\n'.join(descriptors_menu_item_str_list)) 
                    
                    item_main_group_list=['main_group_id,main_group_name,second_group_id']    
                    for item_main_group in item_main_group_set:
                        item_main_group_list.append(u','.join(item_main_group).encode('utf8'))
                    zf.writestr('item_main_group','\n'.join(item_main_group_list))
                    
                    product_str=['item_id,item_name1,slu_id,nlu,price_1,cost_1,unit_1,price_2,cost_2,unit_2,price_3,cost_3,unit_3,price_4,cost_4,unit_4,price_5,cost_5,unit_5']
                    for p in product_list:
                        product_str.append(u','.join(p).encode('utf8'))
                    zf.writestr('menu_item','\n'.join(product_str))
        
            
            if len(versions):
                zf.writestr('#data_version,db_tables,version')
                zf.writestr('data_version','\n'.join(versions).encode('utf8'))
                
            zf.close()
            
            if len(versions):
                resp = HttpResponse(s.getvalue(), mimetype = "application/x-zip-compressed")
                resp['Content-Disposition'] = 'attachment; filename=%s.zip' % 'server_version'
                resp['Content-Length'] = s.tell()
                s.seek(0)
                return resp
            else:
                return HttpResponse(simplejson.dumps({'status':0,'description':_(u'所欲版本最新')}),mimetype='application/json')
        except Exception,e:
            print traceback.print_exc()
            return HttpResponse(simplejson.dumps({'status':1,'description':e.message}),mimetype='application/json')