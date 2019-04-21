# -*- coding: utf-8 -*- 
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from depot.models import Organization, Goods, Unit, Category, Supplier,\
    ConDepartment, Customer, Invoice, Warehouse, InvoiceDetail, EditGoodsMenuLog, EditGoodsMenuLogDetail,\
    OrgProfile
from cost.models import CategoryPos, MenuItem, MenuItemDetail
from django.utils import simplejson
from endless_pagination.decorators import page_template
from django.utils.translation import ugettext as _
from django.db.models import Q
import requests
from cost.views import CENTER_URL, OS_TYPE
from django.http import HttpResponse, HttpResponseBadRequest
import traceback
import datetime
from inventory.common import get_abbreviation
from django.db import transaction
from django import conf
from depot.views.base import require_pos_config
from inventory.uperms.context_processors import auth_org_perm
from django.core.cache import cache

@require_pos_config
def wupin(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['symbol']=symbol=OrgProfile.objects.get(org=org).symbol

    goods = Goods.objects.filter(org=org)
    price_ori = 0
    sale_price_ori = 0

    for good in goods:
        price_ori += good.price_ori * good.nums
        sale_price_ori += good.sale_price_ori * good.nums

    template_var['price_ori'] = price_ori
    template_var['sale_price_ori'] = sale_price_ori

    if goods.exists():
        template_var['has_goods'] = True
    else:
        template_var['has_goods'] = False

    if request.method=="POST":
        try:
            action=request.POST['action']
            if action=="delete":
                tag=request.POST['tag']
                gid=request.POST['gid']
                
                
                details=InvoiceDetail.objects.filter(good_id=gid)
                if details.count()==1 and details[0].invoice.invoice_type==9999:
                    details.delete()
                Goods.objects.get(pk=gid).delete()
  
                
                return HttpResponse(simplejson.dumps({'success':1,'tag':int(tag)}),mimetype='application/json')
        except:
            print traceback.print_exc()
    else:

        template_var['keyword']=request.GET.get('keyword','')   
        template_var['category_id']=request.GET.get('category_id','') 
    #template_var['categorys']=Category.objects.filter(org=org).values_list('id','parent_id','name')    
    return render_to_response("simple/wupin.html",template_var,context_instance=RequestContext(request)) 

@page_template('simple/list_wupin_index.html') 
def list_wupin(request,org_id,category_id=None,template='simple/list_wupin.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['symbol'] = symbol = OrgProfile.objects.get(org=org).symbol
        
    if request.method=="GET":  
        warehouses=request.user.get_warehouses(org)
        goods=Goods.objects.filter(org=org,status=1).select_related('item_detail')
        
        keyword=request.GET.get('keyword')
        if keyword:
            goods=goods.filter(Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword))
            
        if category_id:
            category=Category.objects.get(pk=category_id)
            goods=goods.filter(category__in=category.get_descendants(include_self=True))
    
        template_var['order']=order=request.GET.get('order','name')
        template_var['goods']=goods.select_related().order_by(order)
        
        if extra_context is not None:
            template_var.update(extra_context)    
            
        return render_to_response(template,template_var,context_instance=RequestContext(request)) 

@require_pos_config
def caipin(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    if request.method=="POST":
        try:
            action=request.POST['action']
            if action=="sync_menuitem":
                inv_sync = cache.get("inv_sync_%s"%(org_id,))
                if inv_sync is None:
                    cache.set("inv_sync_%s"%(org_id,),1,60*5)
                else:
                    return HttpResponse(simplejson.dumps({'message':_(u'同步请求已发送，稍候请刷新查看更新数据')}),mimetype='application/json')
                try:
                    
                    r=requests.post(CENTER_URL+"/capi/sync_menuitem_stock/",data={'guid':org.org_guid,'host':getattr(conf.settings,'DEFAUT_URL','http://stock.sandypos.com').strip('/')},timeout=300)
                    print 'sync menu_item by save info,guid:%s,status:%s'%(org.org_guid,r.status_code)
                    if not r.text:
                        return HttpResponse(simplejson.dumps({'message':_(u'云端似乎没有您的收银注册记录')}),mimetype='application/json')
                except:
                    print traceback.print_exc()
                    
                return HttpResponse(simplejson.dumps({'message':_(u'同步请求已发送，稍候请刷新查看更新数据')}),mimetype='application/json')
        
            elif action=="delete":
                tag=request.POST['tag']
                mid=request.POST['mid']
                
                menuItem=MenuItem.objects.get(pk=mid)
                menuItem.status=0
                menuItem.save()
                
                return HttpResponse(simplejson.dumps({'success':1,'tag':int(tag)}),mimetype='application/json')
        except:
            print traceback.print_exc()
    else:
        template_var['keyword']=request.GET.get('keyword','')
        template_var['categorys']=CategoryPos.objects.filter(org=org,processing=0).values_list('id','parent_id','name') #simplejson.dumps()  
        
    return render_to_response("simple/caipin.html",template_var,context_instance=RequestContext(request)) 

@page_template('simple/list_caipin_index.html') 
def list_caipin(request,org_id,category_id=None,template='simple/list_caipin.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    if request.method=="GET":


        menuItems=MenuItem.objects.filter(org=org,status=1,processing=0)
        
        keyword=request.GET.get('keyword')
        if keyword:
            menuItems=menuItems.filter(Q(item_name__icontains=keyword)|Q(nlu__icontains=keyword))
            
        if category_id:
            category=CategoryPos.objects.get(pk=category_id)
            menuItems=menuItems.filter(categoryPos__in=category.get_descendants(include_self=True))
            # menuItems = menuItems.filter(categoryPos=category)
        
        template_var['menuItems']=menu_items=menuItems.select_related()

        #显示的最大菜品数
        max_item = OrgProfile.objects.get(org=org).max_item
        symbol = OrgProfile.objects.get(org=org).symbol
        template_var['max_item'] = range(max_item)
        template_var['max_item_len'] = max_item
        template_var['symbol'] = symbol
        
        if extra_context is not None:
            template_var.update(extra_context)    
            
        return render_to_response(template,template_var,context_instance=RequestContext(request)) 

@page_template('simple/list_caipin_index.html')  
def caipin_delete(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['delete']=True
        
    if request.method=="POST":
        try:
            action=request.POST['action']
            if action=="recover":
                tag=request.POST['tag']
                mid=request.POST['mid']
                
                menuItem=MenuItem.objects.get(pk=mid)
                menuItem.status=1
                menuItem.save()
                
                return HttpResponse(simplejson.dumps({'success':1,'tag':int(tag)}),mimetype='application/json')
        except:
            print traceback.print_exc()
    else:
        #显示的最大菜品数
        menuItems=MenuItem.objects.filter(org=org,status=0,processing=0)
        max_item = OrgProfile.objects.get(org=org).max_item
        template_var['menuItems']=menuItems.select_related()
        template_var['max_item'] = range(max_item)
        template_var['max_item_len'] = max_item
        template_var['categorys']=CategoryPos.objects.filter(org=org,processing=0).values_list('id','parent_id','name') #simplejson.dumps()  
    

    return render_to_response("simple/caipin.html",template_var,context_instance=RequestContext(request)) 

@page_template('simple/list_caipin_index.html') 
def list_delete_caipin(request,org_id,category_id=None,delete=False,template='simple/list_caipin.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['delete']=True    
    if request.method=="GET":
        max_item = OrgProfile.objects.get(org=org).max_item
        template_var['max_item'] = range(max_item)
        template_var['max_item_len'] = max_item
        #template_var['categorys']=CategoryPos.objects.filter(org=org,processing=0).values_list('id','parent_id','name') #simplejson.dumps()   
        menuItems=MenuItem.objects.filter(org=org,status=0)
        
        keyword=request.GET.get('keyword')
        if keyword:
            menuItems=menuItems.filter(Q(item_name__icontains=keyword)|Q(nlu__icontains=keyword))  
        
        if category_id:
            category=CategoryPos.objects.get(pk=category_id)
            menuItems=menuItems.filter(categoryPos__in=category.get_descendants(include_self=True))
        template_var['menuItems']=menuItems.select_related()
        
    if extra_context is not None:
        template_var.update(extra_context)    
            
    return render_to_response(template,template_var,context_instance=RequestContext(request)) 

def recover_menuitem(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    menu_item_id = request.POST.get("mid")

    tag = request.POST.get("tag")

    menu_item = MenuItem.objects.get(pk=menu_item_id)

    menu_item.status = 1

    menu_item.save()


    return HttpResponse(simplejson.dumps({'success':1,'tag':int(tag)}),mimetype='application/json')

'''
'    菜品原材料对应关系
'''
def menuItem_detail(request,menuItem_id):
    template_var={}
    
    NONE_ROW=[None]*7
    template_var['menuItem']=menuItem=MenuItem.objects.get(pk=menuItem_id)
    org=menuItem.org
    details=menuItem.details.all()
    template_var['max_item']=OrgProfile.objects.get(org=org).max_item
    
    if request.method=="GET":
        template_var['datas']=simplejson.dumps(details.exists() and [(detail.good_id,detail.good.name,detail.weight,detail.goods_unit and detail.goods_unit.unit or None,
                                               detail.good.get_unit_price(detail.goods_unit)[0],detail.good.get_unit_price(detail.goods_unit)[0]*detail.weight,detail.pk) for detail in details] or [NONE_ROW])
    else:
        try:
            
            auto_reduce=request.POST['auto_reduce']
            if auto_reduce=='false':
                menuItem.sync_type=0
            else:
                menuItem.sync_type=1
            menuItem.save()
            
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[1] == "null":
                        detail[1] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 1 or i) for i in [0,2] if (not detail[i] or detail[i]<0)]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            if detail[6]:
                                exists_key.append(detail[6])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
        except:
            print traceback.print_exc()
        
        if  not details_data_error_count: #details_data and
            try:
                all_key=list(details.values_list('id',flat=True))
                delete_key=set(all_key)-set(exists_key)
                details.filter(id__in=list(delete_key)).delete()
                
                total_price=0    
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[3] and (dd[3]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[3])[0]) or None
                        
                        num=good.change_nums(dd[5],unit)
                       
                        if dd[6]:
                            detail=MenuItemDetail.objects.get(pk=dd[6])
                            detail.good=good
                            detail.weight=dd[2]
                            detail.goods_unit=unit
                            detail.save()
                        else:
                            detail=MenuItemDetail.objects.create(org=org,menuItem=menuItem,
                                    good=good,weight=dd[2],goods_unit=unit
                                )
                        
                            
                       
                        total_price+=dd[5]
                    except:
                
                        print traceback.print_exc()
                        continue
                
                menuItem.cost=total_price
                if total_price:
                    menuItem.percent1=menuItem.cost and (menuItem.price-menuItem.cost)*100.0/menuItem.cost or 0
                    menuItem.percent2=menuItem.price and (menuItem.price-menuItem.cost)*100.0/menuItem.price or 0
                else:
                    menuItem.percent1=0
                    menuItem.percent2=0
                    
                menuItem.profit=menuItem.price-menuItem.cost
                menuItem.save()
     
                if request.is_ajax():
                    details=menuItem.details.all()
                    datas=[{'name':detail.good.name,'unit':detail.goods_unit and detail.goods_unit.unit or None,'weight':detail.weight,'price':detail.good.price} for detail in details]
                    '''
                    @创建更新菜品物品同步记录
                    @date:2017/4/13

                    '''
                    if not datas:
                        edit_log = EditGoodsMenuLog.objects.create(org=org,menu_id=menuItem_id,menu_name=menuItem.item_name,created_user=request.user,is_cleaned=1)
                    else:
                        edit_log = EditGoodsMenuLog.objects.create(org=org,menu_id=menuItem_id,menu_name=menuItem.item_name,created_user=request.user)
                    log_detail_list = []

                    for data in datas:
                        log_detail_list.append(EditGoodsMenuLogDetail(log_id=edit_log,item_name=data['name'],unit=data['unit'],num=data['weight'],price=data['price'],total_price=data['price']*data['weight']))

                    EditGoodsMenuLogDetail.objects.bulk_create(log_detail_list)
                        


                    return HttpResponse(simplejson.dumps({'success':1,'seq':int(request.GET['seq']),'cost':menuItem.cost,'profit':menuItem.profit,
                                                          'percent1':round(menuItem.percent1,2),'percent2':round(menuItem.percent2,2),'datas':datas}),mimetype='application/json')
            
            except:
                print traceback.print_exc()    
        else:
           
            if request.is_ajax():
                return HttpResponseBadRequest(simplejson.dumps({'details_data_error':details_data_error}),mimetype='application/json')
  
        
    return render_to_response('simple/menuItem_detail.html',template_var,context_instance=RequestContext(request)) 


def import_from_pos(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    if request.method=="GET":    
        template_var['categorys']=Category.objects.filter(org=org).values_list('id','parent_id','name')
        template_var['categorys_pos']=CategoryPos.objects.filter(org=org,processing=0).values_list('id','parent_id','name')
        
        return render_to_response('simple/import_from_pos.html',template_var,context_instance=RequestContext(request))
    else:
        from_pos_category_list = request.POST.get('from_pos_category').split(',')
        print isinstance(from_pos_category_list,list)
        for categoryPos_id in from_pos_category_list:
            print 'abcd'
            try:
                
                category=Category.objects.get(pk=request.POST['to_category'])
                categoryPos=CategoryPos.objects.get(pk=int(categoryPos_id))
                auto_reduce=int(request.POST['auto_reduce'])
                keep_tree=int(request.POST['keep_tree'])


    
                menuItems=MenuItem.objects.filter(categoryPos__in=categoryPos.get_descendants(include_self=True))

            

           
                if keep_tree:
                    child_categoryPos=categoryPos.get_descendants(include_self=True)
                    main_category,created=Category.objects.get_or_create(parent=category,name=categoryPos.name,org=org,defaults={'user':request.user})
 
                    for categoryPos in child_categoryPos:
                        scategory,created=Category.objects.get_or_create(parent=(categoryPos.id==int(categoryPos_id)) and category or main_category,name=categoryPos.name,org=org,defaults={'user':request.user})
                    
                        _menuItems=menuItems.filter(categoryPos=categoryPos)
                        for _menuItem in _menuItems:
                            unit=None
                            if _menuItem.unit:
                                unit,created=Unit.objects.get_or_create(unit=_menuItem.unit,good__isnull=True,org=org)
                            goods,created=Goods.objects.get_or_create(name=_menuItem.item_name,category=scategory,org=org,defaults={'unit':unit,'abbreviation':get_abbreviation(_menuItem.item_name),'sale_price_ori':_menuItem.price,'sale_price':_menuItem.price,'last_modify_user':request.user})
                        
                            if auto_reduce:
                                MenuItemDetail.objects.get_or_create(org=org,menuItem=_menuItem,good=goods,weight=1,goods_unit=goods.unit)
                        
                                weight=1
                                good_unit=goods.unit
                                standard_weight=goods.change_nums(weight,good_unit)
                            
                                _menuItem.cost=standard_weight*goods.refer_price
                                _menuItem.profit=_menuItem.price-_menuItem.cost
                                _menuItem.percent1=_menuItem.cost and (_menuItem.price-_menuItem.cost)*100.0/_menuItem.cost or 0
                                _menuItem.percent2=_menuItem.price and (_menuItem.price-_menuItem.cost)*100.0/_menuItem.price or 0
                                _menuItem.sync_type=1
                                _menuItem.save()
                else:
                    for _menuItem in menuItems:
                        unit=None
                        if _menuItem.unit:
                            unit,created=Unit.objects.get_or_create(unit=_menuItem.unit,good__isnull=True,org=org)
                        goods,created=Goods.objects.get_or_create(name=_menuItem.item_name,category=category,org=org,defaults={'unit':unit,'abbreviation':get_abbreviation(_menuItem.item_name),'sale_price':_menuItem.price,'last_modify_user':request.user})
                    
                        if auto_reduce:
                            MenuItemDetail.objects.get_or_create(org=org,menuItem=_menuItem,good=goods,weight=1,goods_unit=goods.unit)
                    
                            weight=1
                            good_unit=goods.unit
                            standard_weight=goods.change_nums(weight,good_unit)
                        
                            _menuItem.cost=standard_weight*goods.refer_price
                            _menuItem.profit=_menuItem.price-_menuItem.cost
                            _menuItem.percent1=_menuItem.cost and (_menuItem.price-_menuItem.cost)*100.0/_menuItem.cost or 0
                            _menuItem.percent2=_menuItem.price and (_menuItem.price-_menuItem.cost)*100.0/_menuItem.price or 0
                            _menuItem.sync_type=1
                            _menuItem.save()          
            
                Category.objects.partial_rebuild(Category.objects.filter(org=org)[0].tree_id)
            except Exception,e:
                print traceback.print_exc()
                return HttpResponse(simplejson.dumps({'success':0,'message':e.message}),mimetype='application/json')
        return HttpResponse(simplejson.dumps({'success':1,'category_id':category.id}),mimetype='application/json')

@transaction.commit_manually        
def in_out_simple(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    gid=request.GET.get('gid')
    template_var['good']=good=Goods.objects.get(org=org,pk=gid)
        
    if request.method=="GET":        
        template_var['suppliers']=Supplier.objects.filter(org=org,status=1)
        template_var['departments']=ConDepartment.objects.filter(org=org,status=1)
        template_var['customers']=Customer.objects.filter(org=org,status=1)

        units=good.units
        if units:
            template_var['units']=units
        
        response=render_to_response('simple/in_out_simple.html',template_var,context_instance=RequestContext(request))
        transaction.commit()
        return response
    
    else:
        try:
            invoice_type=int(request.POST.get('in_invoice_type') or request.POST.get('out_invoice_type'))
            nums=float(request.POST.get('in_nums') or request.POST.get('out_nums'))
            unit_id=request.POST.get('in_unit') or request.POST.get('out_unit')
            try:
                price=float(request.POST.get('in_price') or request.POST.get('out_price'))
            except ValueError:
                price = 0
            remark=request.POST.get('remark')
            
            supplier_cus=request.POST.get('supplier_cus')
            customer_cus=request.POST.get('customer_cus')
            department_cus=request.POST.get('department_cus')
            
            tag=request.GET.get('tag')

            if invoice_type == 1000 or invoice_type == 1001:
                #权限判断
                if not request.user.has_org_perm(org,'depot.caigouruku_add'):
                    return HttpResponse(simplejson.dumps({'success':0,'message':_(u'处理失败,没有权限')}),mimetype='application/json')

            warehouse=Warehouse.objects.filter(org=org)[0]
            
            invoice=Invoice.objects.create(org=org,warehouse_root=warehouse,event_date=datetime.date.today(),invoice_type=invoice_type,charger=request.user,
                                           user=request.user,remark=remark,content_object=request.user,invoice_code=Invoice.get_next_invoice_code())
            
            if unit_id:
                unit=Unit.objects.get(pk=unit_id)
                num=good.change_nums(nums,unit)
            else:
                unit=None
                num=nums
             
            if invoice_type == 1001:
                supplier,created=Supplier.objects.get_or_create(org=org,name=supplier_cus,defaults={'abbreviation':get_abbreviation(supplier_cus)})
                invoice.content_object=supplier
                
                
            elif invoice_type == 2000:
                supplier,created=Supplier.objects.get_or_create(org=org,name=supplier_cus,defaults={'abbreviation':get_abbreviation(supplier_cus)})
                invoice.content_object=supplier
                
                
            elif invoice_type == 2001:
                department,created=ConDepartment.objects.get_or_create(org=org,name=department_cus,defaults={'abbreviation':get_abbreviation(department_cus)})
                invoice.content_object=department
            elif invoice_type == 2002:
                customer,created=Supplier.objects.get_or_create(org=org,name=customer_cus,defaults={'abbreviation':get_abbreviation(customer_cus)})
                invoice.content_object=customer
            
            if invoice_type in (1000,1001,2000,2001):
                InvoiceDetail.objects.create(invoice=invoice,good=good,
                                    batch_code=InvoiceDetail.get_next_detail_code(),warehouse_root=invoice.warehouse_root,
                                    warehouse=warehouse,
                                    num1=nums,unit1=unit,price=price,total_price=nums*price,
                                    num=num,last_nums=num,
                                    avg_price=num and (nums*price)/num or 0
                                )
                #更新成本价
                if unit and unit.good:
                    unit.price=price
                    unit.save()
                else:
                    good.price=price
                    good.save()
                
                invoice.total_price=nums*price
            elif invoice_type==2002:
                InvoiceDetail.objects.create(invoice=invoice,good=good,
                                    batch_code=InvoiceDetail.get_next_detail_code(),warehouse_root=invoice.warehouse_root,
                                    warehouse=warehouse,
                                    num1=nums,unit1=unit,price=price,total_price=nums*price,
                                    num=num,last_nums=num,
                                    avg_price=num and (nums*price)/num or 0,
                                    chenben_price=good.chengben_price*num
                                )
                
                if unit and unit.good:
                    unit.sale_price=price
                    unit.save()
                else:
                    good.sale_price=price
                    good.save()
            
                invoice.total_price=nums*price
                invoice.sale_price=good.chengben_price*num
                
            
            invoice.save()
            
            try:
                res=invoice.confirm(request.user)
                if res!=2:
                    transaction.rollback()
                    invoice.delete()
                    return HttpResponse(simplejson.dumps({'success':0,'message':_(u'处理失败,是否数量不足,请先入库')}),mimetype='application/json')
            except Exception,e:
                invoice.delete()
                transaction.rollback()
                print traceback.print_exc()
                return HttpResponse(simplejson.dumps({'success':0,'message':e.message}),mimetype='application/json')
            
            good=Goods.objects.get(pk=gid)
            transaction.commit()
            return HttpResponse(simplejson.dumps({'success':1,'invoice_type':invoice_type,'good_nums':good.nums,'tag':tag,'unit':unit and unit.unit or '',
                                                  'nums':nums,'price':price,'date':invoice.event_date.strftime('%Y-%m-%d'),'good_id':good.id}),mimetype='application/json')
        
        except Exception,e:
            transaction.rollback()
            print traceback.print_exc()
            return HttpResponse(simplejson.dumps({'success':0,'message':e.message}),mimetype='application/json')


def goods_img(request, goods_id):
    template_var = {}
    if request.method == "GET":
        goods = Goods.objects.get(pk=goods_id)

        try:
            url = goods.cover.url
            template_var["goods"] = goods
        except:
            print(traceback.print_exc())
        return render_to_response('simple/goods_img.html',template_var)

