# -*- coding: utf-8 -*- 
from cost.models import SyncStamp, SyncHis, SyncHisStep, SyncSeq, SyncSeqDetail,\
    MenuItem, MenuItemDetail, MenuItemProfit
from depot.models import Organization, Customer, Invoice, Warehouse,\
    InvoiceDetail, Goods, Unit, OrgProfile
from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _, check_for_language
import datetime
import traceback
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson, translation
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q,Sum,Count,Min,Max,Avg
from cost.forms import DateRangeForm, MenuProfitQueryForm
from endless_pagination.decorators import page_template
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from inventory.settings import STYLE
from django import conf
import time

import platform

OS_TYPE=platform.system().upper()
    
CENTER_URL=getattr(conf.settings,'CENTER_URL',"http://www.gicater.me")

@page_template('cost_logs_index.html')
def cost_logs(request,org_id,template="cost_logs.html",extra_context=None):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    template_var['stamp']=stamp=SyncStamp.objects.get_or_create(org=org)[0]
    template_var['zdate']=datetime.datetime.now().replace(day=1)
    
    if request.method=="POST":
        template_var['syncHis']=SyncHis.objects.none()
        if extra_context is not None:
            template_var.update(extra_context)
            
        jz_time=request.POST.get('jz_time',None)
        try:
            jz_time=datetime.datetime.strptime(jz_time,'%Y-%m-%d')
            stamp.last_sync_time=jz_time
            stamp.save()
            template_var['zdate']=jz_time
        except:
            print traceback.print_exc()
    else:
        if request.GET:
            form=DateRangeForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s"%(reverse('cost_logs',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
        
        template_var['has_syncHis']=SyncHis.objects.filter(org=org).exists()
        if form.is_valid():
            syncHis=SyncHis.objects.filter(org=org,created_time__gt=form.cleaned_data['date_from'],created_time__lt=form.cleaned_data['date_to']).select_related()
                
            template_var['syncHis']=syncHis
        template_var['form']=form
        
        if extra_context is not None:
            template_var.update(extra_context)
        
    return render_to_response("cost_logs.html",template_var,context_instance=RequestContext(request))


def cost_view_raw_data(request,org_id,his_id):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    template_var['his']=SyncHis.objects.select_related().get(org=org,pk=his_id)
        
    return render_to_response("cost_view_raw_data.html",template_var,context_instance=RequestContext(request)) 

      
'''
    酒水自动出库列表
'''
@page_template('cost_chukudan_index.html')
def cost_chukudan(request,org_id,template='cost_chukudan.html',extra_context=None):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
    
    if request.method=="GET":
        if request.GET:
            form=DateRangeForm(request.GET.copy())
        else:
            form=DateRangeForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today()})
            
        if form.is_valid():
    
            invoices=Invoice.objects.filter(org=org,invoice_type=2002,content_type=ContentType.objects.get_for_model(pos_customer),object_id=pos_customer.pk,
                                            event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'])
            
            template_var['invoices']=invoices.distinct()
        else:
            template_var['invoices']=Invoice.objects.none()
                
    
        template_var['form']=form

        if extra_context is not None:
            template_var.update(extra_context)        
    return render_to_response(template,template_var,context_instance=RequestContext(request))

'''
    得到利润表
'''
@page_template('cost_profit_index.html')
def cost_profit(request,org_id,template='',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
  
 
    if request.method=="POST":
        import requests
        try:
            action=request.POST['action']
            if action=="sync_menuitem":
                try:
                    r=requests.post(CENTER_URL+"/capi/sync_menuitem_stock/",data={'guid':org.org_guid})
                    print 'sync menu_item by save info,guid:%s,status:%s'%(org.org_guid,r.status_code)
                    if not r.text:
                        return HttpResponse(simplejson.dumps({'message':_(u'云端似乎没有您的收银注册记录')}),mimetype='application/json')
                except:
                    print traceback.print_exc()
                    
                return HttpResponse(simplejson.dumps({'message':_(u'同步请求已发送，稍候请刷新查看更新数据')}),mimetype='application/json')
        except:
            print traceback.print_exc()
    
    sort=request.GET.get('sort','item_id')
    order=request.GET.get('order',None)
    
    if sort and order:
        template_var['sort']=sort
        template_var['order']=int(order)
    
        
    template_var['menuItems']=MenuItem.objects.filter(org=org).order_by((order=="1") and ("-"+sort) or sort)
    
    if extra_context is not None:
            template_var.update(extra_context) 
    return render_to_response("cost_profit.html",template_var,context_instance=RequestContext(request))


'''
    删除利润表
'''
def cost_delete_menuItem(request,org_id):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    MenuItem.objects.get(org=org,pk=request.POST.get('menu_item')).delete()  
        
    return HttpResponse(simplejson.dumps({'menu_item':request.POST.get('menu_item')}),mimetype='application/json')
    
@csrf_exempt 
@transaction.commit_manually  
def cost_sync(request):
    guid=request.REQUEST.get('guid',None)
    try:
        org=Organization.objects.get(org_guid=guid)
    except:
        transaction.rollback()
        print traceback.print_exc()
        return HttpResponse(simplejson.dumps({'error':_(u'非法请求')}),mimetype='application/json')
    
    default_language=None
    if STYLE=="inventory_en":
        default_language="en"
    if request.REQUEST.get('language',default_language):
        request.session['django_language'] = request.REQUEST.get('language',default_language)
        
    
    if request.method=="GET":
        stamp=SyncStamp.objects.get_or_create(org=org)[0]
        
        last_sync_time=stamp.last_sync_time or datetime.datetime.now().replace(day=1)
        print 'get method token is',get_token(request),get_token(request),get_token(request)
        transaction.commit()
        return HttpResponse(simplejson.dumps({'token':get_token(request),'last_sync':datetime.datetime.strftime(last_sync_time,'%Y-%m-%d %H:%M:%S')}),mimetype='application/json')
    
    else:
        try:
            stamp=SyncStamp.objects.get_or_create(org=org)[0]
            last_sync_time=stamp.last_sync_time or datetime.datetime.now().replace(day=1)
            
            pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
            pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
            
            warehouse=Warehouse.objects.get(org=org,oindex=1)
            
            sale_str=request.POST.get('sale_str','')

            
            
            syncHis=SyncHis.objects.create(org=org,raw_str=sale_str)
            SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'接受到数据,默认出库仓库为%(w)s')%{'w':warehouse})
            
            sale=simplejson.loads(sale_str)
            
            
            
            if sale['guid']!=org.org_guid:
                SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'餐厅ID不对应,发送为%(fa)s,本店配置为%(pei)s')%{'fa':sale['guid'],'pei':org.org_guid})
                raise
            
            ERRORS=0
            SUCCESS=0
            
            for date_datas in sale['datas']:

                invoice=None
                try:
                    zdate=datetime.datetime.strptime(date_datas['zdate'],'%Y-%m-%d').date()
                    seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(date_datas['details']))
                    
                    invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),result=True,org=org,warehouse_root=warehouse,event_date=zdate,invoice_type=2002,
                                                   content_object=pos_customer,charger=pos_user,user=pos_user,remark=_(u'由收银同步'),voucher_code=seq.pk)
                    
                    total_price=0
                    chenben_price=0
                    
                    #遍历菜品列表
                    for detail in date_datas['details']:

                        cost = 0
    
                        #根据菜品单位/nlu/单位 生成一一个唯一菜品记录
                        try:
                            menuItem,created=MenuItem.objects.get_or_create(org=org,item_id=detail['item_id'],status=1,unit=detail['unit'],nlu=detail['nlu'],defaults={'item_name':detail['item_name'],'price':detail['price'],'cost':0})
                        except:
                            print traceback.print_exc()
                            MenuItem.objects.filter(org=org,item_id=detail['item_id'],unit=detail['unit'],nlu=detail['nlu']).delete()
                            menuItem,created=MenuItem.objects.get_or_create(org=org,item_id=detail['item_id'],status=1,unit=detail['unit'],nlu=detail['nlu'],defaults={'item_name':detail['item_name'],'price':detail['price'],'cost':0})
                            
                        if not created:
                            menuItem.item_name=detail['item_name']
                            menuItem.price=detail['price']
                            menuItem.cost = 0
                            menuItem.save()


                            
                        
                        #根据nlu和单位匹配
                        if not menuItem.details.all():
                            SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'还未给菜品%s配置原材料，无法自动出库')%(menuItem.item_name,))
                            transaction.commit()
                            continue
                            

                        for menu_detail in menuItem.details.all():

                            try:
                                good = menu_detail.good
                                good.sale_price = good.sale_price_ori
                                good.save()
                                num = detail['num'] * menu_detail.weight
                                invoice_detail=InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=num,unit1=menu_detail.goods_unit,price=menu_detail.good.sale_price_ori,
                                                                 avg_price=menu_detail.good.sale_price,num=num,last_nums=num,total_price=menu_detail.good.sale_price_ori*num,chenben_price=num*menu_detail.good.price_ori)

                                total_price+=menu_detail.good.sale_price_ori*num

                                chenben_price+=num*menu_detail.good.price_ori

                                cost+=menu_detail.good.price_ori*menu_detail.weight



                                SyncHisStep.objects.create(syncHis=syncHis,remark=_(u"匹配到原材料%(good)s,数量%(num)s")%{'good':good,'num':num})
                            except ObjectDoesNotExist:
                                SyncHisStep.objects.create(syncHis=syncHis,remark=_(u"未找到物品%s，请先配置菜品和物品对应关系")%(good,))
                                continue

                            except:
                                print traceback.print_exc()
                                SyncHisStep.objects.create(syncHis=syncHis,remark=_(u"未配置菜品与物品关系"))
                                continue

                        menuItem.cost = cost
                        menuItem.profit = menuItem.price - menuItem.cost
                        if menuItem.price == 0:
                            menuItem.percent2 = 0
                        else:
                            menuItem.percent2 = menuItem.profit/menuItem.price *100
                        menuItem.save()
                        invoice.total_price = total_price
                        invoice.sale_price = chenben_price

                        invoice.save()


                        sd=SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'匹配到菜品'),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,nlu=menuItem.nlu,price=detail['price'],num=detail['num'],unit=detail['unit'],total_price=detail['total_price'],cost=menuItem.cost)
                        sd.save()

                        '''
                            try:
                                good=detail.good
                                #sd.goods_text=good.name
                                #sd.save()
                            
                            #如果收银菜品有单位
                                if menuItem.unit:
                                    units=Unit.objects.filter(good=good,unit=menuItem.unit)
                                
                                #找到匹配原料单位的辅助单位与菜品相同
                                    if units.exists():
                                        unit=units[0]
                                        num=good.change_nums(detail['num'],units[0])
                                        SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'找到菜品%(c)s对应的单位%(b)s')%{'c':menuItem.item_name,'b':unit})
                                        menuItem.cost=unit.price or good.change_nums(1,unit)*good.chengben_price
                                        menuItem._percent=1
                                        menuItem.save()
                                    #更新辅助单位售价
                                        unit.sale_price=detail['price']
                                        unit.save()
                                    
                                        detail=InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=detail['num'],unit1=unit,price=detail['price'],
                                                                 avg_price=detail['total_price']/num,num=num,last_nums=num,total_price=detail['total_price'],chenben_price=num*good.chengben_price)
                                        total_price+=detail.total_price
                                        chenben_price+=detail.chenben_price
                                elif good.unit and menuItem.unit==good.unit.unit:
                                    unit=good.unit
                                    num=good.change_nums(detail['num'],good.unit)
                                    SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'找到菜品%(c)s对应的单位%(b)s')%{'c':menuItem.item_name,'b':unit})
                                    menuItem.cost=good.chengben_price
                                    menuItem._percent=1
                                    menuItem.save()
                                    #更新物品售价
                                    good.sale_price=detail['price']
                                    good.save()
                                    
                                    detail=InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=detail['num'],unit1=unit,price=detail['price'],
                                                                 avg_price=detail['total_price']/num,num=num,last_nums=num,total_price=detail['total_price'],chenben_price=num*good.chengben_price)
                                    total_price+=detail.total_price
                                    chenben_price+=detail.chenben_price
                                else:
                                    SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'未找到菜品%(c)s的单位%(b)s,忽略此菜品扣减')%{'c':menuItem.item_name,'b':menuItem.unit})                           
                            else:
                                #收银菜品无单位，按照主单位扣减
                                unit=good.unit
                                num=detail['num']
                                SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'找到菜品%(c)s对应的单位[警告：菜品无单位，按照主单位]%(b)s')%{'c':menuItem.item_name,'b':unit})
                                menuItem.cost=good.chengben_price
                                menuItem.unit=good.unit and good.unit.unit or ''
                                menuItem._percent=1
                                menuItem.save()
                                #更新物品售价
                                good.sale_price=detail['price']
                                good.save()
                                    
                                detail=InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=detail['num'],unit1=unit,price=detail['price'],
                                                                 avg_price=detail['total_price']/num,num=num,last_nums=num,total_price=detail['total_price'],chenben_price=num*good.chengben_price)
                                total_price+=detail.total_price
                                chenben_price+=detail.chenben_price
                                
                        except ObjectDoesNotExist:
                            menuItem.cost = 0
                            SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'未找到菜品%(c)s物品编码%(b)s,忽略此菜品扣减')%{'c':menuItem.item_name,'b':menuItem.nlu})   
                        except Exception,e:
                            menuItem.cost = 0
                            print traceback.print_exc()
                            SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'未找到菜品%(c)s发生错误%(b)s,忽略此菜品扣减')%{'c':menuItem.item_name,'b':e.message})
                        
                        '''
                    
                    
                    transaction.commit()
                    status=invoice.confirm(pos_user)
                        
                        
                    if status==2:
                        transaction.commit()
                        SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'日期%(d)s的数据已处理完毕,审核已成功,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'h':invoice.invoice_code})
                        SUCCESS = True
                    else:
                        transaction.rollback()
                        SUCCESS = False
                        SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code}) 
                        
                
            
                    if SUCCESS:
                        stamp.last_sync_time=datetime.datetime.now()
                        stamp.save()
                
                    transaction.commit()
                    return HttpResponse(simplejson.dumps({'last_sync':datetime.datetime.strftime(last_sync_time,'%Y-%m-%d %H:%M:%S'),'success_count':SUCCESS}),mimetype='application/json')
                
                except:
                    print traceback.print_exc()
        except:
            transaction.rollback()
            print traceback.print_exc()
            return HttpResponse(simplejson.dumps({'error':_(u'处理错误')}),mimetype='application/json')
        
@transaction.commit_manually
@csrf_exempt
def cost_sync_online(request):

    start_time = time.time()
    
    guid=request.REQUEST.get('guid',None)
    try:
        org=Organization.objects.get(org_guid=guid)
        mode=OrgProfile.objects.get(org=org).auto_out_stock_mode
    except:
        org=None
        mode=-1    #没有org返回-1

    default_language = request.REQUEST.get('language',org.style=="english" and 'en' or 'zh-cn')
    
    if default_language and check_for_language(default_language):
        if hasattr(request, 'session'):
            request.session['django_language'] = default_language    
        translation.activate(default_language)
    
    INDUSTRY=(org.style=='retail') and 'retail' or 'restaurant'        
    if INDUSTRY=="restaurant":
        if request.method=="GET":
            '''
            ' 考虑到大部分菜是没有配置的，这里返回需要请求的菜
            '''

            ids=list(MenuItemDetail.objects.filter(org=org).values_list('menuItem__item_id',flat=True).distinct())
            transaction.commit()
            return HttpResponse(simplejson.dumps({'status':org and 1 or 0,'ids':ids,'auto_out_stock_mode':mode}),mimetype='application/json')
        else:
            try:
                pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
                pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
                warehouse=Warehouse.objects.filter(org=org)[0]
                
                seq=None
                syncHis=SyncHis.objects.create(org=org,raw_str="order_normal_datas:%(order_normal_datas)s,order_void_datas:%(order_void_datas)s"%{'order_normal_datas':request.POST['order_normal_datas'],'order_void_datas':request.POST['order_void_datas']})
                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'接受到数据,默认出库仓库为%(w)s')%{'w':warehouse})
                
                order_normal_datas=simplejson.loads(request.POST['order_normal_datas'])
                order_void_datas=simplejson.loads(request.POST['order_void_datas'])
                
                ERRORS=0
                SUCCESS=0
                edit_invoice_list=[]
                
                invoice=None
                menuItemCache=MenuItem.objects.filter(org=org).select_related('details')
                menuItemDetailCache=MenuItemDetail.objects.filter(org=org)
                for order_normal_data in order_normal_datas:
                    try:
                        zdate=datetime.datetime.strptime(order_normal_data['zdate'],'%Y-%m-%d').date()
                        seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_normal_data['details']))
                        
                        #每天应该只生成一个单
                        try:
                            invoice=Invoice.objects.get(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                        except:
                            queryset=Invoice.objects.filter(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                            if queryset.exists():
                                invoice=queryset[1]
                            else:
                                
                                invoice=Invoice.objects.create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,invoice_code=Invoice.fix_get_next_invoice_code(),result=True,warehouse_root=warehouse,
                                                           content_object=pos_customer,remark=_(u'由收银同步'),voucher_code=seq.pk)
                                invoice.save()


                        
                        
                        if invoice.status==2:
                            invoice.unconfirm()
                        invoice_details=invoice.details.all()


                        #记录修改过的单据，稍候统一审核    
                        if not invoice in edit_invoice_list:
                            edit_invoice_list.append(invoice)
                        
                        for detail in order_normal_data['details']:

                            #SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'分析菜品%(item_name)s配置'%{'item_name':menuItem.item_name}))
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配菜品ID%(item_id)s为%(item_name)s,单位:%(unit)s,售出%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))
                            
                                menuItem.last_sale_num=detail['num']
                                menuItem.last_sale_time=zdate
                                menuItem.save() 

                                #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))

                                '''
                            except:
                                print traceback.print_exc()
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配菜品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的菜品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配菜品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):

                                good=itemGoodDetail.good
                                
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----对应原材料%(good_name)s %(num)s%(unit)s'%{'good_name':good.name,
                                                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or ''}))
                                
                                '''
                                ' 如果物品已经存在单据中，直接合并，不存在则新增
                                '''
                                invoice_detail=invoice_details.filter(good=good,unit1=itemGoodDetail.goods_unit)
                                if invoice_detail.exists():
                                    invoice_detail=invoice_detail[0]
                                    #保存即时库存
                                    invoice_detail.num_at_that_time=invoice_detail.good.nums
                                    invoice_detail.num1+=detail['num']*itemGoodDetail.weight
                                    invoice_detail.num=good.change_nums(invoice_detail.num1,itemGoodDetail.goods_unit)
                                    
                                    invoice_detail.total_price+=detail['num']*itemGoodDetail.weight*good.sale_price_ori
                                    
                                    invoice_detail.chenben_price+=detail['num']*itemGoodDetail.weight*good.price_ori
                                    invoice_detail.save()
                                else:
                                    before_num = good.nums
                                    _num=detail['num']*itemGoodDetail.weight
                                    _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                    InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=0,total_price=_base_num*good.sale_price_ori,chenben_price=_base_num*good.price_ori,num_at_that_time=before_num)
             

                    except Exception,e:
                        print traceback.print_exc()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误1'))
                if order_void_datas:  
                    for detail in order_void_datas['stock_minus_list']:
                        try:
                            zdate=datetime.datetime.strptime(detail['zdate'],'%Y-%m-%d').date()
                            seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_void_datas['stock_minus_list']))
                            
                            invoice,created=Invoice.objects.get_or_create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,defaults={'invoice_code':Invoice.get_next_invoice_code(),'result':True,'warehouse_root':warehouse,
                                                               'content_object':pos_customer,'remark':_(u'由收银同步'),'voucher_code':seq.pk})
                            invoice.save()
                            invoice_details=invoice.details.all()
                            
                            if invoice.status==2:
                                invoice.unconfirm()
                            #记录修改过的单据，稍候统一审核    
                            if not invoice in edit_invoice_list:
                                edit_invoice_list.append(invoice)
                                
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配菜品ID%(item_id)s为%(item_name)s,单位:%(unit)s,增加%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))

                                 #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price']-float(menuItem.cost))*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(flaot(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))

                                '''


                            except:
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配菜品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的菜品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配菜品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):
                                good=itemGoodDetail.good
                                
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----【反结账扣减库存】对应原材料%(good_name)s %(num)s%(unit)s,对应收银流水号%(head_id)s'%{'good_name':good.name,
                                                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or '','head_id':detail['order_head_id']}))
                                
                                '''
                                ' 反结账，直接扣减
                                '''
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=_base_num,total_price=_base_num*good.sale_price_ori,chenben_price=-_base_num*good.price_ori,num_at_that_time=before_num,
                                                                         remark=_(u'反结账来自账单%(head_id)s'%{'head_id':detail['order_head_id']}))
                            
                        except Exception,e:
                            print traceback.print_exc()
                            SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误2%s'%(e.message)))
                    

                    for detail in order_void_datas['stock_add_list']:
                        try:
                            zdate=datetime.datetime.strptime(detail['zdate'],'%Y-%m-%d').date()
                            seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_void_datas['stock_minus_list']))
                            
                            invoice,created=Invoice.objects.get_or_create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,defaults={'invoice_code':Invoice.get_next_invoice_code(),'result':True,'warehouse_root':warehouse,
                                                               'content_object':pos_customer,'remark':_(u'由收银同步'),'voucher_code':seq.pk})
                            invoice.save()
                            invoice_details=invoice.details.all()
                            
                            if invoice.status==2:
                                invoice.unconfirm()
                            #记录修改过的单据，稍候统一审核    
                            if not invoice in edit_invoice_list:
                                edit_invoice_list.append(invoice)
                                
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=-menuItem.price,num=-detail['num'],unit=detail['unit'] or '',total_price=-(float(detail['price']) * float(detail['num'])),cost=-menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配菜品ID%(item_id)s为%(item_name)s,单位:%(unit)s'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))

                                 #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num-detail['num']
                                        this_day_menu.profit = this_day_menu.profit-(float(detail['price']-float(menuItem.cost))*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))

                                '''



                            except:
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配菜品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的菜品'%{'item_id':detail['item_id']},price=0,num=-detail['num'],unit=detail['unit'] or '',total_price=-detail['price'])
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配菜品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):
                                good=itemGoodDetail.good
                                
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----【反结账还原库存】对应原材料%(good_name)s %(num)s%(unit)s,对应收银流水号%(head_id)s'%{'good_name':good.name,'sale_num':detail['num'],
                                                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or '','head_id':detail['order_head_id']}))
                                
                                '''
                                ' 反结账，直接扣减
                                '''
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=-_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=-_base_num,last_nums=-_base_num,total_price=-_base_num*good.sale_price_ori,chenben_price=-_base_num*good.price_ori,num_at_that_time=before_num,
                                                                         remark=_(u'反结账来自账单%(head_id)s'%{'head_id':detail['order_head_id']}))
                        except Exception,e:
                            print traceback.print_exc()
                            SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误3%(msg)s'%{'msg':e.message}))
                
                
                '''
                ' 数据处理后，跟新单据信息并保存
                '''

                for invoice in edit_invoice_list:
                    total_price=0
                    chenben_price=0
                    for detail in invoice.details.all():
                        
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price


                    invoice.total_price=total_price
                    invoice.sale_price=chenben_price
                    invoice.result = 1    
                    invoice.save()

                    transaction.commit()
                    
                    status=invoice.confirm(pos_user)
                    #同步收银不需要收款单
                    invoice.payinvoice_set.all().delete()
                    seq=SyncSeq.objects.filter(his=syncHis,zdate=invoice.event_date).order_by('-id')[0]
                    
                    if status==2:
                        transaction.commit()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕,审核已成功,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'h':invoice.invoice_code})
                    else:
                        transaction.rollback()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code}) 

                        transaction.rollback()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code})

                transaction.commit()
                return HttpResponse(simplejson.dumps({'status':1}),mimetype='application/json')
            except:
                transaction.rollback()
                print traceback.print_exc()
    else:
        
            
        if request.method=="GET":
            ids=list(MenuItemDetail.objects.filter(org=org).values_list('menuItem__item_id',flat=True).distinct())
            transaction.commit()
            return HttpResponse(simplejson.dumps({'status':org and 1 or 0,'auto_out_stock_mode':mode}),mimetype='application/json')
        else:
            try:
                pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
                pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
                try:
                    warehouse=Warehouse.objects.filter(org=org)[0]
                except:
                    warehouse=Warehouse.objects.create(org=org,name=_(u'默认仓库'))
                
                seq=None
                syncHis=SyncHis.objects.create(org=org,raw_str="order_normal_datas:%(order_normal_datas)s,order_void_datas:%(order_void_datas)s"%{'order_normal_datas':request.POST['order_normal_datas'],'order_void_datas':request.POST['order_void_datas']})
                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'接受到数据,默认出库仓库为%(w)s')%{'w':warehouse})
                
                order_normal_datas=simplejson.loads(request.POST['order_normal_datas'])
                order_void_datas=simplejson.loads(request.POST['order_void_datas'])
                
                ERRORS=0
                SUCCESS=0
                edit_invoice_list=[]
                
                invoice=None
                menuItemCache=MenuItem.objects.filter(org=org).select_related('details')
                menuItemDetailCache=MenuItemDetail.objects.filter(org=org)
                for order_normal_data in order_normal_datas:
                    try:
                        zdate=datetime.datetime.strptime(order_normal_data['zdate'],'%Y-%m-%d').date()
                        seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_normal_data['details']))
                        
                        #每天应该只生成一个单
                        invoice,created=Invoice.objects.get_or_create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,defaults={'invoice_code':Invoice.get_next_invoice_code(),'result':True,'warehouse_root':warehouse,
                                                           'content_object':pos_customer,'remark':_(u'由收银同步'),'voucher_code':seq.pk})
                        invoice.save()
                        invoice_details=invoice.details.all()
                        
                        if invoice.status==2:
                            invoice.unconfirm()
                        #记录修改过的单据，稍候统一审核    
                        if not invoice in edit_invoice_list:
                            edit_invoice_list.append(invoice)
                        
                        for detail in order_normal_data['details']:
                            #SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'分析菜品%(item_name)s配置'%{'item_name':menuItem.item_name}))
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配商品ID%(item_id)s为%(item_name)s,单位:%(unit)s,售出%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))
                            
                                menuItem.last_sale_num=detail['num']
                                menuItem.last_sale_time=zdate
                                menuItem.save()

                                #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price']-float(menuItem.cost))*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num'])) 

                                '''


                            except:
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配商品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的商品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配商品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):
                                good=itemGoodDetail.good
                                
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----对应原材料%(good_name)s %(num)s%(unit)s'%{'good_name':good.name,
                                #                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or ''}))
                                
                                '''
                                ' 如果物品已经存在单据中，直接合并，不存在则新增
                                '''
                                invoice_detail=invoice_details.filter(good=good,unit1=itemGoodDetail.goods_unit)
                                if invoice_detail.exists():
                                    invoice_detail=invoice_detail[0]
                                    invoice_detail.num_at_that_time=invoice_detail.good.nums
                                    invoice_detail.num1+=detail['num']*itemGoodDetail.weight
                                    invoice_detail.num=good.change_nums(invoice_detail.num1,itemGoodDetail.goods_unit)
                                    invoice_detail.total_price+=detail['num']*itemGoodDetail.weight*good.sale_price_ori
                                    invoice_detail.chenben_price+=detail['num']*itemGoodDetail.weight*good.price_ori
                                    invoice_detail.save()
                                else:
                                    before_num = good.nums
                                    _num=detail['num']*itemGoodDetail.weight
                                    _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                    InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=0,total_price=_base_num*good.sale_price_ori,chenben_price=_base_num*good.chengben_price,num_at_that_time=before_num)
                        
                    except Exception,e:
                        print traceback.print_exc()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误1%s'%(e.message)))
                if order_void_datas:  
                    for detail in order_void_datas['stock_minus_list']:
                        try:
                            zdate=datetime.datetime.strptime(detail['zdate'],'%Y-%m-%d').date()
                            seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_void_datas['stock_minus_list']))
                            
                            invoice,created=Invoice.objects.get_or_create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,defaults={'invoice_code':Invoice.get_next_invoice_code(),'result':True,'warehouse_root':warehouse,
                                                               'content_object':pos_customer,'remark':_(u'由收银同步'),'voucher_code':seq.pk})
                            invoice.save()
                            invoice_details=invoice.details.all()

                            menuItemCache=MenuItem.objects.filter(org=org).select_related('details')
                            menuItemDetailCache=MenuItemDetail.objects.filter(org=org)
                            
                            if invoice.status==2:
                                invoice.unconfirm()
                            #记录修改过的单据，稍候统一审核    
                            if not invoice in edit_invoice_list:
                                edit_invoice_list.append(invoice)
                                
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'【反结账扣减库存】已匹配商品ID%(item_id)s为%(item_name)s,单位:%(unit)s,增加%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))

                                 #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price']-float(menuItem.cost))*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num'])),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num'])),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                '''


                            except:
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配商品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的商品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配商品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):
                                good=itemGoodDetail.good
                                
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----【反结账扣减库存】对应原材料%(good_name)s %(num)s%(unit)s,对应收银流水号%(head_id)s'%{'good_name':good.name,
                                #                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or '','head_id':detail['order_head_id']}))
                                
                                '''
                                ' 反结账，直接扣减
                                '''
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=_base_num,total_price=_base_num*good.sale_price_ori,chenben_price=_base_num*good.price_ori,num_at_that_time=before_num,
                                                                         remark=_(u'反结账来自账单%(head_id)s'%{'head_id':detail['order_head_id']}))
                            
                        except Exception,e:
                            print traceback.print_exc()
                            SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误2%s'%(e.message)))
                        
                    for detail in order_void_datas['stock_add_list']:
                        try:
                            zdate=datetime.datetime.strptime(detail['zdate'],'%Y-%m-%d').date()
                            seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_void_datas['stock_minus_list']))
                            
                            invoice,created=Invoice.objects.get_or_create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,defaults={'invoice_code':Invoice.get_next_invoice_code(),'result':True,'warehouse_root':warehouse,
                                                               'content_object':pos_customer,'remark':_(u'由收银同步'),'voucher_code':seq.pk})
                            invoice.save()
                            invoice_details=invoice.details.all()
                            
                            if invoice.status==2:
                                invoice.unconfirm()
                            #记录修改过的单据，稍候统一审核    
                            if not invoice in edit_invoice_list:
                                edit_invoice_list.append(invoice)
                                
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'【反结账还原库存】已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=-menuItem.price,num=-detail['num'],unit=detail['unit'] or '',total_price=-(float(detail['price']) * float(detail['num'])),cost=-menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配商品ID%(item_id)s为%(item_name)s,单位:%(unit)s'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))

                                  #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num-detail['num']
                                        this_day_menu.profit = this_day_menu.profit-(float(detail['price']-float(menuItem.cost))*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                '''


                            except:
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配商品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的商品'%{'item_id':detail['item_id']},price=0,num=-detail['num'],unit=detail['unit'] or '',total_price=-detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配商品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'商品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):
                                good=itemGoodDetail.good
                                
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----【反结账还原库存】对应原材料%(good_name)s %(num)s%(unit)s,对应收银流水号%(head_id)s'%{'good_name':good.name,'sale_num':detail['num'],
                                #                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or '','head_id':detail['order_head_id']}))
                                
                                '''
                                ' 反结账，直接扣减
                                '''
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=-_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=-_base_num,last_nums=-_base_num,total_price=-_base_num*good.sale_price_ori,chenben_price=-_base_num*good.price_ori,num_at_that_time=before_num,
                                                                         remark=_(u'反结账来自账单%(head_id)s'%{'head_id':detail['order_head_id']}))
                        except Exception,e:
                            print traceback.print_exc()
                            SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误3%(msg)s'%{'msg':e.message}))
                
                
                '''
                ' 数据处理后，跟新单据信息并保存
                '''
                for invoice in edit_invoice_list:
                    total_price=0
                    chenben_price=0
                    for detail in invoice.details.all():
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price
                    
                    invoice.total_price=total_price
                    invoice.sale_price=chenben_price
                    invoice.result = 1    
                    invoice.save()
                    transaction.commit()
                    
                    status=invoice.confirm(pos_user)
                    #同步收银不需要收款单
                    invoice.payinvoice_set.all().delete()
                    seq=SyncSeq.objects.filter(his=syncHis,zdate=invoice.event_date).order_by('-id')[0]
                    
                    if status==2:
                        transaction.commit()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕,审核已成功,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'h':invoice.invoice_code})
                    else:
                        transaction.rollback()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code}) 
            
                transaction.commit()
                return HttpResponse(simplejson.dumps({'status':1}),mimetype='application/json')
            except:
                transaction.rollback()
                print traceback.print_exc()

@page_template('menu_item_analysis_index.html')
def menu_item_analysis(request,org_id,extra_context=None):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    menus = MenuItemProfit.objects.filter(org=org)

    total_pri = 0
    total_cost = 0

    if request.method == "GET":
        template_var['form']=MenuProfitQueryForm()
        menus = menus.filter(zdate__gte=datetime.date.today().replace(day=1),zdate__lte=datetime.date.today()+datetime.timedelta(days=1))
        for menu in menus:
            menu.total_price = menu.price * menu.sale_num
            try:
                menu.profit_rate = round((menu.price - menu.cost) / menu.cost,2)
            except:
                menu.profit_rate = "该菜品成本为0"
            total_pri = total_pri + menu.total_price
            total_cost = total_cost + menu.cost * menu.sale_num

    else:
        template_var['form']=form=MenuProfitQueryForm(request.POST.copy())
        if form.is_valid():
            if form.cleaned_data['date_from']:
                menus = menus.filter(zdate__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                menus = menus.filter(zdate__lte=form.cleaned_data['date_to'])
            if form.cleaned_data['item_name']:
                menus = menus.filter(item_name__icontains=form.cleaned_data['item_name'])

            for menu in menus:
                menu.total_price = menu.price * menu.sale_num
                try:
                    menu.profit_rate = round((menu.price - menu.cost) / menu.cost,2)
                except ZeroDivisionError:
                    menu.profit_rate = "该菜品成本为0"
                total_pri = total_pri + menu.total_price
                total_cost = total_cost + menu.cost * menu.sale_num




    template_var['total_pri'] = total_pri
    template_var['total_cost'] = total_cost
    template_var['total_profit'] = total_pri - total_cost
    try:
        template_var['total_profit_rate'] = round((total_pri-total_cost)/total_cost,3)
    except ZeroDivisionError:
        template_var['total_profit_rate'] = "总成本为0，无利润率"
    template_var['menus'] = menus


    if extra_context is not None:
            template_var.update(extra_context)

    return render_to_response("menu_item_analysis.html",template_var,context_instance=RequestContext(request))


@transaction.commit_manually
@csrf_exempt
def daily_cost_sync_online(request):
    guid=request.REQUEST.get('guid',None)
    try:
        org=Organization.objects.get(org_guid=guid)
        mode=OrgProfile.objects.get(org=org).auto_out_stock_mode
    except:
        org=None
        mode=-1    #没有org返回-1


    default_language = request.REQUEST.get('language',org.style=="english" and 'en' or 'zh-cn')
    
    if default_language and check_for_language(default_language):
        if hasattr(request, 'session'):
            request.session['django_language'] = default_language    
        translation.activate(default_language)
    
    INDUSTRY=(org.style=='retail') and 'retail' or 'restaurant'

    if INDUSTRY == 'restaurant':
        if request.method == "GET":
            ids=list(MenuItemDetail.objects.filter(org=org).values_list('menuItem__item_id',flat=True).distinct())
            transaction.commit()
            return HttpResponse(simplejson.dumps({'status':org and 1 or 0,'ids':ids,'auto_out_stock_mode':mode}),mimetype='application/json')
        else:
            try:
                pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
                pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
                warehouse=Warehouse.objects.filter(org=org)[0]
                
                seq=None
                syncHis=SyncHis.objects.create(org=org,raw_str="order_normal_datas:%(order_normal_datas)s,order_void_datas:%(order_void_datas)s"%{'order_normal_datas':request.POST['order_normal_datas'],'order_void_datas':request.POST['order_void_datas']})
                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'接受到数据,默认出库仓库为%(w)s')%{'w':warehouse})
                
                order_normal_datas=simplejson.loads(request.POST['order_normal_datas'])
                order_void_datas=simplejson.loads(request.POST['order_void_datas'])
                
                ERRORS=0
                SUCCESS=0
                edit_invoice_list=[]
                
                invoice=None
                menuItemCache=MenuItem.objects.filter(org=org).select_related('details')
                menuItemDetailCache=MenuItemDetail.objects.filter(org=org)
                for order_normal_data in order_normal_datas:
                    try:
                        zdate=datetime.datetime.strptime(order_normal_data['zdate'],'%Y-%m-%d').date()
                        seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_normal_data['details']))
                        
                        #每天应该只生成一个单
                        try:
                            invoice=Invoice.objects.get(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                        except:
                            queryset=Invoice.objects.filter(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                            if queryset.exists():
                                invoice=queryset[1]
                            else:
                                
                                invoice=Invoice.objects.create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,invoice_code=Invoice.fix_get_next_invoice_code(),result=True,warehouse_root=warehouse,
                                                           content_object=pos_customer,remark=_(u'由收银同步'),voucher_code=seq.pk)
                                invoice.save()


                        
                        
                        if invoice.status==2:
                            invoice.unconfirm()
                        invoice_details=invoice.details.all()
                        invoice_details.delete()


                        #记录修改过的单据，稍候统一审核    
                        if not invoice in edit_invoice_list:
                            edit_invoice_list.append(invoice)
                        
                        for detail in order_normal_data['details']:

                            #SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'分析菜品%(item_name)s配置'%{'item_name':menuItem.item_name}))
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配菜品ID%(item_id)s为%(item_name)s,单位:%(unit)s,售出%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))
                            
                                menuItem.last_sale_num=detail['num']
                                menuItem.last_sale_time=zdate
                                menuItem.save() 

                                #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                '''
                            except:
                                print traceback.print_exc()
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配菜品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的菜品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配菜品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):

                                good=itemGoodDetail.good
                                
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----对应原材料%(good_name)s %(num)s%(unit)s'%{'good_name':good.name,
                                                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or ''}))
                                
                                '''
                                ' 如果物品已经存在单据中，直接合并，不存在则新增
                                
                                invoice_detail=invoice_details.filter(good=good,unit1=itemGoodDetail.goods_unit)
                                if invoice_detail.exists():
                                    invoice_detail=invoice_detail[0]
                                    #保存即时库存
                                    invoice_detail.num_at_that_time=invoice_detail.good.nums
                                    invoice_detail.num1+=detail['num']*itemGoodDetail.weight
                                    invoice_detail.num=good.change_nums(invoice_detail.num1,itemGoodDetail.goods_unit)
                                    #若销售的是一对多菜品，同步销售单的总价还是为收银发送过来的price，单据详情金额显示的是物品预估价格，会有不一致的情况
                                    invoice_detail.total_price+=detail['price']
                                    
                                    invoice_detail.chenben_price+=detail['num']*itemGoodDetail.weight*good.price_ori
                                    invoice_detail.save()
                                    '''
                                
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=0,total_price=_base_num*good.sale_price_ori,chenben_price=_base_num*good.price_ori,num_at_that_time=before_num)
             

                    except Exception,e:
                        print traceback.print_exc()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误1'))

            
                '''
                ' 数据处理后，跟新单据信息并保存
                '''
                for invoice in edit_invoice_list:
                    total_price=0
                    chenben_price=0
                    for detail in invoice.details.all():
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price                    
                    invoice.total_price=total_price
                    invoice.sale_price=chenben_price
                    invoice.result = 1    
                    invoice.save()
                    transaction.commit()
                    
                    status=invoice.confirm(pos_user)
                    #同步收银不需要收款单
                    invoice.payinvoice_set.all().delete()
                    seq=SyncSeq.objects.filter(his=syncHis,zdate=invoice.event_date).order_by('-id')[0]
                    
                    if status==2:
                        transaction.commit()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕,审核已成功,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'h':invoice.invoice_code})
                    else:
                        transaction.rollback()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code}) 
            
                transaction.commit()
                return HttpResponse(simplejson.dumps({'status':1}),mimetype='application/json')
            except:
                transaction.rollback()
                print traceback.print_exc()
                
                        

    else:
        if request.method == "GET":
            ids=list(MenuItemDetail.objects.filter(org=org).values_list('menuItem__item_id',flat=True).distinct())
            transaction.commit()
            return HttpResponse(simplejson.dumps({'status':org and 1 or 0,'auto_out_stock_mode':mode}),mimetype='application/json')
        else:
            try:
                pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
                pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
                warehouse=Warehouse.objects.filter(org=org)[0]
                
                seq=None
                syncHis=SyncHis.objects.create(org=org,raw_str="order_normal_datas:%(order_normal_datas)s,order_void_datas:%(order_void_datas)s"%{'order_normal_datas':request.POST['order_normal_datas'],'order_void_datas':request.POST['order_void_datas']})
                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'接受到数据,默认出库仓库为%(w)s')%{'w':warehouse})
                
                order_normal_datas=simplejson.loads(request.POST['order_normal_datas'])
                order_void_datas=simplejson.loads(request.POST['order_void_datas'])
                
                ERRORS=0
                SUCCESS=0
                edit_invoice_list=[]
                
                invoice=None
                menuItemCache=MenuItem.objects.filter(org=org).select_related('details')
                menuItemDetailCache=MenuItemDetail.objects.filter(org=org)
                for order_normal_data in order_normal_datas:
                    try:
                        zdate=datetime.datetime.strptime(order_normal_data['zdate'],'%Y-%m-%d').date()
                        seq=SyncSeq.objects.create(his=syncHis,zdate=zdate,raw_str=simplejson.dumps(order_normal_data['details']))
                        
                        #每天应该只生成一个单
                        try:
                            invoice=Invoice.objects.get(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                        except:
                            queryset=Invoice.objects.filter(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002)
                            if queryset.exists():
                                invoice=queryset[1]
                            else:
                                
                                invoice=Invoice.objects.create(org=org,event_date=zdate,charger=pos_user,user=pos_user,invoice_type=2002,invoice_code=Invoice.fix_get_next_invoice_code(),result=True,warehouse_root=warehouse,
                                                           content_object=pos_customer,remark=_(u'由收银同步'),voucher_code=seq.pk)
                                invoice.save()


                        
                        
                        if invoice.status==2:
                            invoice.unconfirm()
                        invoice_details=invoice.details.all()
                        invoice_details.delete()


                        #记录修改过的单据，稍候统一审核    
                        if not invoice in edit_invoice_list:
                            edit_invoice_list.append(invoice)
                        
                        for detail in order_normal_data['details']:

                            #SyncHisStep.objects.create(syncHis=syncHis,remark=_(u'分析菜品%(item_name)s配置'%{'item_name':menuItem.item_name}))
                            try:
                                menuItem=menuItemCache.get(item_id=detail['item_id'],unit=detail['unit'] or '')
                                
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'已匹配%(item_name)s'%{'item_name':menuItem.item_name}),menuItem=menuItem,item_id=menuItem.item_id,item_name=menuItem.item_name,price=menuItem.price,num=detail['num'],unit=detail['unit'] or '',total_price=float(detail['price']) * float(detail['num']),cost=menuItem.cost)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'已匹配菜品ID%(item_id)s为%(item_name)s,单位:%(unit)s,售出%(sale_num)s份'%{'item_id':menuItem.item_id,'item_name':menuItem.item_name,'unit':detail['unit'] or '','sale_num':detail['num']}))
                            
                                menuItem.last_sale_num=detail['num']
                                menuItem.last_sale_time=zdate
                                menuItem.save() 

                                #生成对应菜品利润表，如果是同一天同一个菜品，则合并
                                '''
                                try:
                                    this_day_menu = MenuItemProfit.objects.get(org=org,item_id=detail['item_id'],unit=detail['unit'] or '')
                                    if this_day_menu.zdate.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
                                        this_day_menu.sale_num = this_day_menu.sale_num+detail['num']
                                        this_day_menu.profit = this_day_menu.profit+(float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                        this_day_menu.save()
                                    else:
                                        MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))
                                except:
                                    print traceback.print_exc() 
                                    MenuItemProfit.objects.create(org=org,item_name=menuItem.item_name,item_id=detail['item_id'],nlu=menuItem.nlu,cost=menuItem.cost,price=round(float(detail['price'])/float(detail['num']),2),sale_num=detail['num'],profit=float(detail['price'])-float(menuItem.cost)*float(detail['num']))

                                '''
                            except:
                                print traceback.print_exc()
                                SyncSeqDetail.objects.create(seq=seq,goods_text=_(u'未匹配菜品'),menuItem=None,item_id=detail['item_id'],item_name=u'id为%(item_id)s的菜品'%{'item_id':detail['item_id']},price=0,num=detail['num'],unit=detail['unit'] or '',total_price=detail['price'],cost=0)
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'未配菜品ID%(item_id)s,单位:%(unit)s,忽略'%{'item_id':detail['item_id'],'unit':detail['unit'] or ''}))
                                continue
                            
                            if not menuItem.details.exists():
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)未配置原材料对应关系,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            if menuItem.sync_type:
                                pass
                                #SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品需要自动出库'))
                            else:
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'菜品%(item_name)s(%(unit)s)不需要自动出库,忽略'%{'item_name':menuItem.item_name,'unit':menuItem.unit or _(u'无单位')}))
                                continue
                            
                            detail_single=menuItemDetailCache.filter(menuItem=menuItem).count()==1   
                            for itemGoodDetail in menuItemDetailCache.filter(menuItem=menuItem):

                                good=itemGoodDetail.good
                                
                                SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'----对应原材料%(good_name)s %(num)s%(unit)s'%{'good_name':good.name,
                                                                            'num':itemGoodDetail.weight,'unit':itemGoodDetail.goods_unit and itemGoodDetail.goods_unit.unit or ''}))
                                
                                '''
                                ' 如果物品已经存在单据中，直接合并，不存在则新增
                                
                                invoice_detail=invoice_details.filter(good=good,unit1=itemGoodDetail.goods_unit)
                                if invoice_detail.exists():
                                    invoice_detail=invoice_detail[0]
                                    #保存即时库存
                                    invoice_detail.num_at_that_time=invoice_detail.good.nums
                                    invoice_detail.num1+=detail['num']*itemGoodDetail.weight
                                    invoice_detail.num=good.change_nums(invoice_detail.num1,itemGoodDetail.goods_unit)
                                    #若销售的是一对多菜品，同步销售单的总价还是为收银发送过来的price，单据详情金额显示的是物品预估价格，会有不一致的情况
                                    invoice_detail.total_price+=detail['price']
                                    
                                    invoice_detail.chenben_price+=detail['num']*itemGoodDetail.weight*good.price_ori
                                    invoice_detail.save()
                                    '''
                                
                                before_num = good.nums
                                _num=detail['num']*itemGoodDetail.weight
                                _base_num=good.change_nums(_num,itemGoodDetail.goods_unit)
                                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=warehouse,warehouse_root=warehouse,num1=_num,unit1=itemGoodDetail.goods_unit,price=good.sale_price_ori,
                                                                         avg_price=detail_single and good.sale_price_ori or 0,num=_base_num,last_nums=0,total_price=_base_num*good.sale_price_ori,chenben_price=_base_num*good.price_ori,num_at_that_time=before_num)
             

                    except Exception,e:
                        print traceback.print_exc()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'解析遇到错误1'))

            
                '''
                ' 数据处理后，跟新单据信息并保存
                '''
                for invoice in edit_invoice_list:
                    total_price=0
                    chenben_price=0
                    for detail in invoice.details.all():
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price                    
                    invoice.total_price=total_price
                    invoice.sale_price=chenben_price
                    invoice.result = 1    
                    invoice.save()
                    transaction.commit()
                    
                    status=invoice.confirm(pos_user)
                    #同步收银不需要收款单
                    invoice.payinvoice_set.all().delete()
                    seq=SyncSeq.objects.filter(his=syncHis,zdate=invoice.event_date).order_by('-id')[0]
                    
                    if status==2:
                        transaction.commit()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕,审核已成功,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'h':invoice.invoice_code})
                    else:
                        transaction.rollback()
                        SyncHisStep.objects.create(syncHis=syncHis,seq=seq,remark=_(u'日期%(d)s的数据已处理完毕，审核未成功:%(r)s,单号<a class="rel_invocie" href="javascript:void(0)">%(h)s</a>')%{'d':zdate.strftime('%Y-%m-%d'),'r':status,'h':invoice.invoice_code}) 
            
                transaction.commit()
                return HttpResponse(simplejson.dumps({'status':1}),mimetype='application/json')
            except:
                transaction.rollback()
                print traceback.print_exc()