# -*- coding: utf-8 -*- 
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from endless_pagination.decorators import page_template
from depot.models import Organization,Unit, Brand, Category, Goods,\
    ConDepartment, Supplier, Customer, Invoice, Warehouse, SupplierGroup,\
    SyncTableVer, InvoiceDetail
from inventory.common import *
from inventory.common import _Wookbook
from pyExcelerator.Formatting import Font
from pyExcelerator.Style import XFStyle
from django.db.models import Q,Sum,Count
from django.forms.models import modelformset_factory, inlineformset_factory
from depot.views.forms.info_forms import UnitForm, BrandForm, CategoryForm,\
    GoodsForm, ConDepartmentForm, SupplierForm, CustomerForm,\
    make_AuxiliaryUnitForm
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson
from inventory.MACROS import IN_BASE_TYPE, IN_BASE_TYPE_STR
import logging
import traceback
from cost.models import MenuItemDetail, MenuItem

'''
    用户登录公司信息
'''
@login_required(login_url="/")
def info(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        #om=OrgsMembers.objects.get(user=request.user,org=org)
        request.session['org_id']=org_id
        request.session['org']=org
        request.session['root_org']=org.get_root_org()
        
        return render_to_response("org_info.html",template_var,context_instance=RequestContext(request))
        #return render_to_response("org_backstage.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()
        
        

'''
    物品单位
'''
def goods_unit(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    template_var['global_units']=Unit.objects.filter(org__isnull=True)
    
    unit_set=inlineformset_factory(Organization,Unit,form=UnitForm,extra=1,exclude=('is_global'),can_delete=True)
    queryset=Unit.objects.select_related().filter(status__gte=0,org=org,parent__isnull=True).order_by('-status')
    
    if request.method=="GET":
        template_var['formset']=formset=unit_set(instance=org,queryset=queryset)
    else:
        formset=unit_set(request.POST.copy(),instance=org,queryset=queryset)
        if formset.is_valid():
            instances=formset.save()
            for instance in instances:
                try:
                    Unit.objects.get(org=org,good__isnull=True,unit=instance.unit)
                except:
                    instance.org=org
                    instance.save()
            template_var['formset']=formset=unit_set(instance=org,queryset=Unit.objects.select_related().filter(status__gte=0,org=org,parent__isnull=True).order_by('-status'))
        else:
            template_var['formset']=formset
    return render_to_response("info/goods_unit.html",template_var,context_instance=RequestContext(request))

        
        
'''
    物品品牌
'''
def goods_brand(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    brand_set=inlineformset_factory(Organization,Brand,form=BrandForm,extra=1,exclude=('is_global'),can_delete=True)
    queryset=Brand.objects.select_related().filter(status__gte=0,org=org).order_by('-status')
    
    if request.method=="GET":
        template_var['formset']=formset=brand_set(instance=org,queryset=queryset)
    else:
        formset=brand_set(request.POST.copy(),instance=org,queryset=queryset)
        if formset.is_valid():
            instances=formset.save(commit=False)
            for instance in instances:
                instance.org=org
                instance.save()
            template_var['formset']=formset=brand_set(instance=org,queryset=Brand.objects.select_related().filter(status__gte=0).order_by('-status'))
        else:
            template_var['formset']=formset
    return render_to_response("info/goods_brand.html",template_var,context_instance=RequestContext(request))


'''
    物品分类和物品
'''
def goods_and_category(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    return render_to_response("info/goods_and_category.html",template_var,context_instance=RequestContext(request))


'''
    添加物品分类
'''
def add_category(request,org_id,category_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    parent=int(request.REQUEST.get('parent',0) or 0)
    parent=parent and Category.objects.get(pk=parent) or Category.objects.get_or_create(parent__isnull=True,org=root_org,defaults={'name':_(u'全部分类')})[0]

    category_id=request.GET.get('edit_id',0)
    category=None
    if category_id:
        category=Category.objects.get(pk=category_id)
        template_var['mod']="mod"
        
        
    if request.method=="GET":
        if category:
            template_var['form']=CategoryForm(instance=category,initial={'org':org,'user':request.user.pk})
        else:
            template_var['form']=CategoryForm(instance=category,initial={'org':org,'user':request.user.pk,'parent':parent and parent.pk or None})
    else:
        form=CategoryForm(request.POST.copy(),request.FILES,instance=category,initial={'org':org,'user':request.user.pk,'parent':parent and parent.pk or None})
        
        if form.is_valid():
            category=form.save(commit=False)
            category.org=org
            category.user=request.user
            category.save()
    
            Category.objects.partial_rebuild(Category.objects.filter(org=org_id)[0].tree_id)
            
            template_var['success']=True
        template_var['form']=form
    
    return render_to_response("info/add_category.html",template_var,context_instance=RequestContext(request))


'''
    删除分组
'''
def del_category(request,org_id):
    
        template_var={}
        org=Organization.objects.get(pk=org_id)
        template_var['org']=org
        root_org=org.get_root_org()
        
        category_id=request.POST.get('category_id')
        category=Category.objects.get(pk=category_id)
        
        categorys=category.get_descendants(include_self=True)
        for good in Goods.objects.filter(category__in=categorys):
            details=InvoiceDetail.objects.filter(good=good)
            if details.count()==1 and details[0].invoice.invoice_type==9999:
                details.delete()
        
        try:
            category.delete()
            return HttpResponse(category_id)
        except:
            Category.objects.partial_rebuild(category.get_root().tree_id)
   

'''
    添加/编辑物品
'''
def add_goods(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['callback']=callback=request.REQUEST.get('callback',0)
        
    category_id=request.GET.get('category_id',0)
    goods_id=request.GET.get('goods_id',None)
    
    goods=None
    if goods_id:
        goods=Goods.objects.get(pk=goods_id)
    category=category_id and Category.objects.get(pk=category_id) or None
    
    if request.method=="GET":
        template_var['form']=GoodsForm(instance=goods,initial={'org':org,'user':request.user.pk,'category':category and category.pk or 0,'max_warning':1000})
    else:
        form=GoodsForm(request.POST.copy(),request.FILES,instance=goods,initial={'org':org,'user':request.user.pk,'category':category and category.pk or 0})
        
        if form.is_valid():
            old_unit=goods and goods.unit or None
            goods=form.save(commit=False)
            goods.last_modify_user=request.user
            goods.org=org
            #如果更改过成本方案
            #if 'chengben_type' in form.changed_data or 'customer_price_life' in form.changed_data or 'customer_price_life_type' in form.changed_data:
            #    goods.update_chengben()
            goods.price=goods.price or 0
            goods.refer_price=goods.price or goods.price_ori
            goods.sale_price=goods.sale_price or goods.sale_price_ori
            
            goods.profit= goods.sale_price_ori-goods.price_ori
            goods.percent1=goods.price_ori and (goods.sale_price_ori-goods.price_ori)*100.0/goods.price_ori or 0
            goods.percent2=goods.sale_price_ori and (goods.sale_price_ori-goods.price_ori)*100.0/goods.sale_price_ori or 0
        
            
            #如果是自己填的单位
            unit_change=False
            
            customer_unit=request.POST.get('unitbox','')
            if not customer_unit:
                goods.unit=None
            elif (goods.unit and goods.unit.unit!=customer_unit.strip()) or not goods.unit:
                unit,created=Unit.objects.get_or_create(unit=customer_unit,org=org,good__isnull=True)
                old_unit=goods.unit
                goods.unit=unit
                unit_change=True
            goods.save()
            
            try:
                stv,created=SyncTableVer.objects.get_or_create(org=org)
                stv.good_ver=int(time.time())
                stv.save()
            except:
                print traceback.print_exc()
                ids=list(SyncTableVer.objects.filter(org=org).order_by('-id').values_list('id',flat=True))[1:]
                SyncTableVer.objects.filter(id__in=ids).delete()
                SyncTableVer.objects.get_or_create(org=org,good_ver=int(time.time()))
                
            
            '''
            ' 更新对应的菜品配置和利润
            '''
            if unit_change or 'unit' in form.changed_data and goods.unit:
                MenuItemDetail.objects.filter(good=goods,goods_unit__isnull=True).update(goods_unit=goods.unit)
                MenuItemDetail.objects.filter(good=goods,goods_unit=old_unit).update(goods_unit=goods.unit)
            
            if 'price_ori' in form.changed_data:
                for detail in MenuItemDetail.objects.filter(good=goods):
                    menuItem=MenuItem.objects.get(pk=detail.menuItem_id)
                    
                    total_price=0
                    for d in menuItem.details.all():
                        total_price+=d.weight*d.good.get_unit_price(d.goods_unit)[0]
                    menuItem.cost=total_price

                    if total_price:
                        menuItem.percent1=menuItem.cost and (menuItem.price-menuItem.cost)*100.0/menuItem.cost or 0
                        menuItem.percent2=menuItem.price and (menuItem.price-menuItem.cost)*100.0/menuItem.price or 0
                    else:
                        menuItem.percent1=0
                        menuItem.percent2=0
                        
                    menuItem.profit=menuItem.price-menuItem.cost
                    menuItem.save()
            
            if callback:
                template_var['success']=True
                template_var['form']=form
                template_var['callback']=1
                template_var['goods']=simplejson.dumps({'pk':goods.pk,'code':goods.code,'name':goods.name,'category_id':goods.category_id,'category':goods.category.name,
                        'is_batchs':goods.is_batchs,'unit_id':goods.unit_id,'unit':goods.unit and goods.unit.unit or '','abbreviation':goods.abbreviation,
                        'price':goods.price,'refer_price':goods.refer_price,'shelf_life':goods.shelf_life,'shelf_life_type':goods.get_shelf_life_type_display()})
            
                return render_to_response("info/mod_goods.html",template_var,context_instance=RequestContext(request))
            
            if not goods.unit:
                goods.auxiliary_unit.all().delete()
            
            if int(request.POST.get('next',0)):
                return HttpResponseRedirect(request.get_full_path())
            
            if not goods_id:
                if goods.unit:
                    #return HttpResponseRedirect('%s?init=1'%reverse('auxiliary_unit',args=[org_id,goods.pk]))
                    pass
                else:
                    pass
            template_var['success']=True
        template_var['form']=form
    
    return render_to_response("info/mod_goods.html",template_var,context_instance=RequestContext(request))


'''
     编辑辅助单位
'''
def auxiliary_unit(request,org_id,goods_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    template_var['init']=request.GET.get('init')
    goods=Goods.objects.get(pk=goods_id)
    
    template_var['goods']=goods
    AuxiliaryUnitForm=make_AuxiliaryUnitForm(org,goods.unit)
    AuxiliaryUnitSet=inlineformset_factory(Goods, Unit,form=AuxiliaryUnitForm,exclude=('status','is_global'),can_delete=True,extra=1)
    
    if request.method=="GET":
        template_var['formset']=formset=AuxiliaryUnitSet(instance=goods)
    else:
        formset=AuxiliaryUnitSet(request.POST.copy(),instance=goods)
        if formset.is_valid():
            formset.save()
            template_var['success']=True
            template_var['formset']=AuxiliaryUnitSet(instance=goods)
            
            
            try:
                stv,created=SyncTableVer.objects.get_or_create(org=org)
                stv.good_ver=int(time.time())
                stv.save()
            except:
                print traceback.print_exc()
                ids=list(SyncTableVer.objects.filter(org=org).order_by('-id').values_list('id',flat=True))[1:]
                SyncTableVer.objects.filter(id__in=ids).delete()
                SyncTableVer.objects.get_or_create(org=org,good_ver=int(time.time()))
                
        else:
            template_var['formset']=formset
    
    return render_to_response("info/auxiliary_unit.html",template_var,context_instance=RequestContext(request))


'''
    列出物品,未增加多店考虑
'''
@page_template('info/goods_index_page.html') 
def list_goods(request,org_id,mod=False,template='info/list_goods_opt.html',extra_context=None): 
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        root_org=org.get_root_org()
        
        category_id=request.REQUEST.get('category_id',None)
        if category_id:
            category=Category.objects.get(pk=category_id)
            template_var["category_id"]=category_id
        else:
            category=Category.objects.get(org=root_org,parent__isnull=True)
            
        categorys=category.get_descendants(include_self=True)
        goods=Goods.objects.filter(Q(category__in=categorys)|Q(category=category))
        
        
        keyword=request.GET.get('keyword','')
        if keyword:
            goods=goods.filter(Q(code__icontains=keyword)|Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword))#.filter(status=True,category__status=True)
            template_var["keyword"]=keyword
        #如果带有仓库参数，则按仓库来
        '''if request.GET.has_key('warehouse_id'):
            warehouse_id=request.GET.get('warehouse_id','')
            template_var["warehouse_id"]=warehouse_id
  
            if warehouse_id:
                template_var['warehouse_id']=int(warehouse_id)
                _warehouse_id=request.GET.get('warehouse','')
                goods=goods.filter(details__invoice__invoice_type__in=IN_BASE_TYPE,details__invoice__warehouse_root_id=_warehouse_id or warehouse_id,
                                   details__invoice__status=2)#.annotate(sum=Sum('details__last_nums'))
                                   
                #测试是否对该仓库有可写权限
                #warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read']).values_list('id',flat=True)
          
                
            else:
                warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read'])
                
                goods=goods.filter(details__invoice__invoice_type__in=IN_BASE_TYPE,details__invoice__warehouse_root__in=warehouses,
                                   details__invoice__status=2)#.annotate(sum=Sum('details__last_nums'))
                                   
        #再按货位查询
        shelf_id=request.GET.get('shelf_id')
        if shelf_id:
            shelf=Warehouse.objects.get(org=org,pk=shelf_id)
            goods=goods.filter(details__warehouse__in=shelf.get_descendants(include_self=True))
            w=list(shelf.get_descendants(include_self=True).values_list('id',flat=True))
            w=",".join([str(x) for x in w])
    
            template_var['goods']=Goods.objects.filter(id__in=goods).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_invoicedetail.warehouse_id in (%s)'%(IN_BASE_TYPE_STR,w),when=True,distinct=True)).distinct()   
        else:
            template_var['goods']=goods.annotate(sum=Sum('details__last_nums'))
        '''
        template_var['goods'] = goods.annotate(sum=Sum('nums'))
        template_var['mod']=mod
        if extra_context is not None:
            template_var.update(extra_context)
            
        return render_to_response(template,template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()

'''
    列出物品,未增加多店考虑
'''
def download_pandian_goods(request,org_id): 
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        root_org=org.get_root_org()
        
        contains_data=request.GET.has_key('data')
        
        category_id=request.REQUEST.get('category_id',None)
        if category_id:
            category=Category.objects.get(pk=category_id)
            template_var["category_id"]=category_id
        else:
            category=Category.objects.get(org=root_org,parent__isnull=True)
            
        categorys=category.get_descendants(include_self=True)
        goods=Goods.objects.filter(Q(category__in=categorys)|Q(category=category))
        
        
        keyword=request.GET.get('keyword','')
        if keyword:
            goods=goods.filter(Q(code__icontains=keyword)|Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)).filter(status=True,category__status=True)
            template_var["keyword"]=keyword
        #如果带有仓库参数，则按仓库来
        if request.GET.has_key('warehouse_id'):
            warehouse_id=request.GET.get('warehouse_id','')
            template_var["warehouse_id"]=warehouse_id
            warehouse_obj=None
            if warehouse_id:
                template_var['warehouse_id']=int(warehouse_id)
                warehouse_obj = Warehouse.objects.get(pk=warehouse_id)
                goods=goods.filter(details__invoice__invoice_type__in=IN_BASE_TYPE,details__invoice__warehouse_root_id=warehouse_id,
                                   details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                                   
                #测试是否对该仓库有可写权限
                warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read','warehouse_mamage']).values_list('id',flat=True)
          
                
            else:
                warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read','warehouse_mamage'])
                
                goods=goods.filter(details__invoice__invoice_type__in=IN_BASE_TYPE,details__invoice__warehouse_root__in=warehouses,
                                   details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                                   
                
        
        template_var['goods']=goods
        
        #
        wb=_Wookbook()
        #ws=wb.add_sheet(u'%s'%org.org_name)       
        
        #ws.col(0).width=4000
        #wcs.col(0).width=4000
        font=Font()
        font.name="Arial"
        font.bold=True
        font.shadow=True
        #font.height=300
        style=XFStyle()
        style.font=font
        
        font2=Font()
        font2.name="Arial"
        font2.bold=True
        font2.shadow=True
        style2=XFStyle()
        style2.font=font2
        
        #ws.write_merge(0,0,0,50,_(u'即时库存'),style)
        #wcs.write_merge(0,0,0,50,u'%s%s检测分表'%(paper.name,cclass.classes_name),style)
        
        i=0
        heads=[_(u'物品名称【必填】'),_(u'物品编码'),_(u'物品分类【必填】'),_(u'上级分类'),_(u'规格'),_(u'单位'),_(u'助查码'),_(u'参考价格'),_(u'下限数量'),_(u'上限数量'),_(u'品牌'),_(u'分批管理'),_(u'SN管理'),_(u'ABC分类'),_(u'初始库存'),_(u'仓库')]
        ws=wb.add_sheet(_(u'物品列表'))
        j=0
        while j<len(heads):
            ws.write(0,j,heads[j],style)
            j+=1        
                
        i=1#第1行
        #if contains_data:
        for good in goods:
            j=0
            ws.write(i,j,unicode(good.name),style)
            j+=1
            ws.write(i,j,unicode(good.code),style)
            j+=1
            ws.write(i,j,unicode(good.category),style)
            j+=1
            if good.category.parent:
                ws.write(i,j,unicode(good.category.parent),style)
            j+=1
            if good.standard:
                ws.write(i,j,unicode(good.standard),style)
            j+=1
            if good.unit:
                ws.write(i,j,unicode(good.unit),style)
            j+=1
            ws.write(i,j,unicode(good.abbreviation),style)
            j+=1
            ws.write(i,j,unicode(good.price),style)
            j+=1
            ws.write(i,j,unicode(good.min_warning),style)
            j+=1
            ws.write(i,j,unicode(good.max_warning),style)
            j+=1
            if good.brand:
                ws.write(i,j,unicode(good.brand),style)
            j+=1
            ws.write(i,j,unicode(good.is_batchs),style)
            j+=1
            ws.write(i,j,unicode(good.is_sn),style)
            j+=1
            ws.write(i,j,unicode(good.ABC),style)
            j+=1
            ws.write(i,j,unicode(good.sum),style)
            j+=1
            if warehouse_obj:
                ws.write(i,j,unicode(warehouse_obj.full_name),style)
            else:
                ws.write(i,j,unicode(_('All')),style)
            j+=1
            i+=1
         
        ws.col(0).width=0x1300
        ws.col(2).width=0x1300
        ws.col(15).width=0x1800
               
        #datetime.date.today().strftime('%Y-%m-%d')
        response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
        fname=(u"%s_%s"%(_(u'即时库存'),datetime.date.today().strftime('%Y-%m-%d'))).encode('gbk')
        #print '11111','attachment; filename=\"%s.xls\"'% fname
        response['Content-Disposition'] = 'attachment; filename=\"%s.xls\"'% fname

        return response          
        
    except:
        print traceback.print_exc()        
'''
    删除物品,未增加多店考虑
'''
def del_goods(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    goods_id=request.POST.get('goods_id',None)
    if goods_id:
        details=InvoiceDetail.objects.filter(good_id=goods_id)
        if details.count()==1 and details[0].invoice.invoice_type==9999:
            details.delete()
        Goods.objects.get(pk=goods_id).delete()
        
    return HttpResponse(goods_id)
        
    
'''
    领用部门列表
'''
def departments(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['departments']=ConDepartment.objects.filter(org=org)
    
    return render_to_response("info/departments.html",template_var,context_instance=RequestContext(request))

'''
    新增/修改领料部门
'''
def mod_department(request,org_id,department_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['parent_id']=parent_id=request.REQUEST.get('parent_id',None)
    
    department=None
    if department_id:
        department=ConDepartment.objects.get(pk=department_id)
    
    if request.method=="GET":
        template_var['form']=ConDepartmentForm(initial={'org':org.pk},instance=department)
    else:
        form=ConDepartmentForm(request.POST.copy(),initial={'org':org.pk},instance=department)
        if form.is_valid():
            form.save()
            template_var['success']=True
            if not parent_id:
                return HttpResponseRedirect(reverse('departments',args=[org.pk]))
        
        template_var['form']=form
    template_var['department']=department
    return render_to_response("info/mod_department.html",template_var,context_instance=RequestContext(request))

'''
    删除领料部门
'''
def department_delete(request,org_id):
    template_var={}
    org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    root_org=org.get_root_org()
    
    del_department_id=request.POST.get('del_department_id')
    department=ConDepartment.objects.get(pk=del_department_id)
    if Invoice.objects.filter(content_type=ContentType.objects.get_for_model(department),object_id=department.pk).exists():
        return HttpResponse(_(u'已有关联单据，禁止删除'))
    department.delete()
    
    return HttpResponse(del_department_id)

'''
    供货商分类
'''
def supplier_group(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    supplierSet=inlineformset_factory(Organization,SupplierGroup,exclude=('status',),can_delete=True,extra=1)
    
    if request.method=="POST":
        formset=supplierSet(request.POST,instance=org)
        if formset.is_valid():
            formset.save()
            template_var['formset']=supplierSet(instance=org)
        else:
            template_var['formset']=formset
    else:
        template_var['formset']=supplierSet(instance=org) 
        
    return render_to_response("info/supplier_group.html",template_var,context_instance=RequestContext(request))

'''
    供货商列表
'''
def suppliers(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['suppliers']=Supplier.objects.filter(org=org).order_by('group')
    
    return render_to_response("info/suppliers.html",template_var,context_instance=RequestContext(request))

'''
    新增/修改供货商
'''
def mod_supplier(request,org_id,supplier_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['parent_id']=parent_id=request.REQUEST.get('parent_id',None)
    
    supplier=None
    if supplier_id:
        supplier=Supplier.objects.get(pk=supplier_id)
    
    if request.method=="GET":
        template_var['form']=SupplierForm(initial={'org':org.pk},instance=supplier)
    else:
        form=SupplierForm(request.POST.copy(),initial={'org':org.pk},instance=supplier)
        if form.is_valid():
            form.save()
            template_var['success']=True
            if not parent_id:
                return HttpResponseRedirect(reverse('suppliers',args=[org.pk]))
        
        template_var['form']=form
    template_var['supplier']=supplier
    return render_to_response("info/mod_supplier.html",template_var,context_instance=RequestContext(request))

'''
    删除供货商
'''
def supplier_delete(request,org_id):
    template_var={}
    org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    root_org=org.get_root_org()
    
    del_supplier_id=request.POST.get('del_supplier_id')
    
    supplier=Supplier.objects.get(pk=del_supplier_id)
    if Invoice.objects.filter(content_type=ContentType.objects.get_for_model(supplier),object_id=supplier.pk).exists():
        return HttpResponse(_(u'已有关联单据，禁止删除'))
    supplier.delete()
    
    
    return HttpResponse(del_supplier_id)


'''
    顾客列表
'''
def customers(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    #Customer.create_or_get_posuser(org)
    template_var['customers']=Customer.objects.filter(org=org).order_by('customer_type')
    
    return render_to_response("info/customers.html",template_var,context_instance=RequestContext(request))


'''
    新增/修改顾客
'''
def mod_customer(request,org_id,customer_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['parent_id']=parent_id=request.REQUEST.get('parent_id',None)
    
    customer=None
    if customer_id:
        customer=Customer.objects.get(pk=customer_id)
    
    if request.method=="GET":
        template_var['form']=CustomerForm(initial={'org':org.pk},instance=customer)
    else:
        form=CustomerForm(request.POST.copy(),initial={'org':org.pk},instance=customer)
        if form.is_valid():
            form.save()
            template_var['success']=True
            if not parent_id:
                return HttpResponseRedirect(reverse('customers',args=[org.pk]))
        
        template_var['form']=form
    template_var['customer']=customer
    return render_to_response("info/mod_customer.html",template_var,context_instance=RequestContext(request))


'''
    删除顾客
'''
def customer_delete(request,org_id):
    template_var={}
    org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    root_org=org.get_root_org()
    
    del_customer_id=request.POST.get('del_customer_id')
    customer=Customer.objects.get(pk=del_customer_id)
    if Invoice.objects.filter(content_type=ContentType.objects.get_for_model(customer),object_id=customer.pk).exists():
        return HttpResponse(_(u'已有关联单据，禁止删除'))
    customer.delete()
    
    return HttpResponse(del_customer_id)


def get_units(request):
    try:
        units=Unit.objects.select_related().filter(status__gte=0,parent__isnull=True).order_by('-status')
        
        return HttpResponse(simplejson.dumps({'data':[list(u) for u in units.values_list('id','unit','des')]}),mimetype='application/json')
    except:
        print traceback.print_exc()
        
def set_units(request):
    print request.POST.get('data','')
    return HttpResponse(simplejson.dumps({'des':'OK'}),mimetype='application/json')
    
    