# -*- coding: utf-8 -*- 
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect,\
    HttpResponseBadRequest

import sys
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from endless_pagination.decorators import page_template
from depot.models import Organization,Unit, Brand, Category, Goods,\
    ConDepartment, Supplier, Customer, Invoice, InvoiceDetail, Warehouse,\
    DetailRelBatch, SnapshotWarehouse, SnapshotWarehouseGood,\
    SnapshotWarehouseDetail, Announce, OrgProfile, SyncTableVer,\
    CommonPrintTemplate, PrintTemplate, OperateLog, PayInvoice, PayInvoiceDetail,\
    BankAccount
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from depot.views.utils import user_can_confirm_invoice
from dateutil import rrule
from pyExcelerator.Formatting import Font
from pyExcelerator.Style import XFStyle
from inventory.settings import TMP_DIR
from pyExcelerator.ImportXLS import parse_xls
from inventory.MACROS import INVOICE_CODE_TEMPLATE, IN_BASE_TYPE,\
    IN_BASE_TYPE_STR
from decimal import Decimal
import operator 
from inventory.common import *
from inventory.common import _Wookbook
from django.db.models import Q,Sum,Count,F
from django.forms.models import modelformset_factory, inlineformset_factory
from depot.views.forms.info_forms import UnitForm, BrandForm, CategoryForm,\
    GoodsForm, ConDepartmentForm, SupplierForm, CustomerForm
from depot.views.forms.warehouse_forms import make_InvoiceSelectSimpleForm,\
    make_InvoiceDetailForm, make_InvoiceForm, make_SelectGoodsForm,\
    make_InvoiceTuiSimpleForm, make_InvoiceTuiDetailForm,\
    make_InvoiceConSimpleForm, make_InvoiceTuiKuDetailForm,\
    make_InvoiceSaleSimpleForm, make_InvoiceSelectDiaoboForm,\
    InvoiceQueryForm, FukuandanAddForm, SelectInvoicesForm
from django.utils import simplejson
from copy import deepcopy
import logging
import traceback
from django.contrib.auth.models import User
from cost.models import SyncHis, SyncSeq
import xlwt

from utils import anti_resubmit

log=logging.getLogger(__name__)

'''
    库位调拨
'''
@page_template('main/kuweidiaobo_index.html')
def kuweidiaobo(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    InvoiceSelectDiaoboForm=make_InvoiceSelectDiaoboForm(org,request.user)
    
    if request.method=="GET":
        if request.GET:
            form=InvoiceSelectDiaoboForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&from_warehouse=&to_warehouse="%(reverse('kuweidiaobo',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=InvoiceSelectDiaoboForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'warehouse':None})
        
       
        if form.is_valid():
            invoices=Invoice.objects.filter(org=org,invoice_type=10000,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'])
            
            warehouses=request.user.get_warehouses(org,['depot.warehouse_write'])
            if form.cleaned_data['from_warehouse']:
                invoices=invoices.filter(warehouse_root=form.cleaned_data['from_warehouse'])
            
            if form.cleaned_data['to_warehouse']:
                invoices=invoices.filter(content_type=ContentType.objects.get_for_model(form.cleaned_data['from_warehouse']),object_id=form.cleaned_data['from_warehouse'].pk)
                
            template_var['invoices']=invoices.distinct()
            
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            
        else:
            template_var['invoices']=Invoice.objects.none()            
        template_var['form']=form

        if extra_context is not None:
            template_var.update(extra_context)
    return render_to_response("main/kuweidiaobo.html",template_var,context_instance=RequestContext(request))


'''
    新增库位调拨
'''
@transaction.commit_manually
def kuweidiaobo_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*9
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice=None

    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
    
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=10000)
    
    if request.method=="GET":
        template_var['form']=InvoiceForm(instance=invoice)
        template_var['warehouse_list_str']=simplejson.dumps(Warehouse.warehouse_list(org))
        
        template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.warehouse.full_name,
                                               _detail.rel_warehouse.full_name,
                                               _detail.num1,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.total_price,_detail.pk) for _detail in invoice.details.all()] or [NONE_ROW])
    else:
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
            
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        
                        detail_data_error=[(i==0 and 1 or i) for i in [0,2,3,4] if (not detail[i] or detail[i]<0)]
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            if detail[8]:
                                exists_key.append(detail[8])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
        
            
            if form.is_valid() and details_data and not details_data_error_count:
        
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.result=1
                invoice.save()
                
                
                if invoice_id:
                    #先清除没有的
                    all_key=list(invoice.details.values_list('id',flat=True))
                    delete_key=set(all_key)-set(exists_key)
                    invoice.details.filter(id__in=list(delete_key)).delete()
            
            
                total_price=0
                
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[5] and (dd[5]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[5])[0]) or None
                        
                        num=good.change_nums(dd[4],unit)
                        
                        if dd[8]:
                            detail=InvoiceDetail.objects.get(pk=dd[8])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[2])
                            detail.rel_warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3])
                            detail.rel_warehouse_root=detail.rel_warehouse.get_root()
                            detail.num1=dd[4]
                            detail.unit1=unit
                            detail.price=dd[6]
                            detail.total_price=dd[4]*dd[6]
                            detail.num=num
                            detail.last_nums=num
                        else:
                            rel_warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3])
                            detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                    batch_code=InvoiceDetail.get_next_detail_code(),warehouse_root=invoice.warehouse_root,
                                    warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[2]),
                                    rel_warehouse=rel_warehouse,
                                    rel_warehouse_root=rel_warehouse.get_root(),
                                    num1=dd[4],unit1=unit,price=dd[6],total_price=dd[4]*dd[6],
                                    num=num,last_nums=num
                                )
                        
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                        total_price+=detail.total_price
                    except:
                        print traceback.print_exc()
                        continue
                
                invoice.total_price=total_price
                invoice.save()
                 
                #同时新增一张出调拨出库单和调拨入库单
                invoice_content=ContentType.objects.get_for_model(invoice)
                out_invoice,created=Invoice.objects.get_or_create(invoice_type=2009,content_type=invoice_content,object_id=invoice.pk,defaults={
                                'invoice_code':Invoice.get_next_invoice_code(),'result':True,'org':org,'warehouse_root':invoice.warehouse_root,
                                'event_date':datetime.date.today(),'charger':invoice.charger,'user':invoice.user,'total_price':invoice.total_price,
                                'remark':_(u'自动调拨出库单据')})
                
                out_invoice.details.all().delete()
                if not created:
                    out_invoice.total_price=invoice.total_price
                    out_invoice.save()
                
                in_invoice,created=Invoice.objects.get_or_create(invoice_type=1009,content_type=invoice_content,object_id=invoice.pk,defaults={
                                'invoice_code':Invoice.get_next_invoice_code(),'result':True,'org':org,'warehouse_root':invoice.content_object,
                                'event_date':datetime.date.today(),'charger':invoice.charger,'user':invoice.user,'total_price':invoice.total_price,
                                'remark':_(u'自动调拨入库单据')})
                
                in_invoice.details.all().delete()
                if not created:
                    in_invoice.total_price=invoice.total_price
                    in_invoice.save()
                
                
                for detail in invoice.details.all():
                    out_detail=deepcopy(detail)
                    out_detail.id=None
                    out_detail.invoice=out_invoice
                    out_detail.batch_code=''
                    out_detail.created_time=None
                    out_detail.modify_time=None
                    out_detail.save()
                    
                for detail in invoice.details.all():    
                    in_detail=deepcopy(detail)
                    in_detail.id=None
                    in_detail.batch_code=InvoiceDetail.get_next_detail_code()
                    in_detail.invoice=in_invoice
                    in_detail.warehouse=detail.rel_warehouse
                    in_detail.warehouse_root=detail.rel_warehouse_root
                    in_detail.rel_warehouse=detail.warehouse
                    in_detail.rel_warehouse_root=detail.rel_warehouse_root
                    in_detail.created_time=None
                    in_detail.modify_time=None
                    in_detail.save()
                    
                    
                
                if form.cleaned_data['sstatus'] and user_can_confirm_invoice(invoice.warehouse_root, invoice.invoice_type, request.user):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')
                transaction.commit()
                if request.is_ajax():
                    return HttpResponse(simplejson.dumps(form.cleaned_data['sstatus'] and {'action':'goon','url':reverse('kuweidiaobo',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
                               
            else:
                
                if request.is_ajax():
                    form_error_dict={}
                    
                    if form.errors:
                        for error in form.errors:
                            e=form.errors[error]
                            form_error_dict[error]=unicode(e)
                    
                            
                    transaction.rollback()
                    return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
            template_var['form']=form
        except:
            print traceback.print_exc()
    response=render_to_response("main/kuweidiaobo_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
    return response

'''
    初始入库
'''
@page_template('main/chushiruku_index.html')
def chushiruku(request,org_id,extra_context=None):
    '''
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    invoiceSelectSimpleForm=make_InvoiceSelectSimpleForm(org,request.user)
    
    if request.method=="GET":
        if request.GET:
            form=invoiceSelectSimpleForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&warehouse=&status=10"%(reverse('chushiruku',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=invoiceSelectSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'status':10})
        
       
        if form.is_valid():
            invoices=Invoice.objects.filter(org=org,invoice_type=1000,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'],remark__contains=form.cleaned_data['remark'])
            if not form.cleaned_data['status']==10:
                invoices=invoices.filter(status=form.cleaned_data['status'])
            
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write','depot.warehouse_manage')):
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'])
                else:
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'],user=request.user)
            else:
                filters = [] 

                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write','depot.warehouse_manage')):
                        filters.append(Q(warehouse_root=warehouse)) 
                    else:
                        filters.append(Q(warehouse_root=warehouse,user=request.user))
                        
                q = reduce(operator.or_, filters) 

                invoices=invoices.filter(q)
                
            template_var['invoices']=invoices.distinct()
            
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            
        else:
            template_var['invoices']=Invoice.objects.none()            
        template_var['form']=form

        '''

    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoiceSelectSimpleForm=make_InvoiceSelectSimpleForm(org,request.user)
    invoices = Invoice.objects.filter(org=org,invoice_type=1000,is_delete=0)
    

    template_var['invoices'] = invoices

    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    result = request.GET.get('result')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        supplier = Supplier.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=supplier)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices

    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/chushiruku.html",template_var,context_instance=RequestContext(request))

'''
    新增初始入库
'''
#@anti_resubmit('chushiruku_add')
@transaction.commit_manually
def chushiruku_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*9
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice=None
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)

    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=1000)
    
    if request.method=="GET":
        template_var['form']=InvoiceForm(instance=invoice)
        template_var['warehouse_list_str']=simplejson.dumps(Warehouse.warehouse_list(org))
        template_var['time_span']=simplejson.dumps([unicode(x[1]) for x in TIME_SPAN])
        template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,'',_detail.good.name,_detail.warehouse.full_name,
                                               _detail.num1,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.total_price,_detail.pk) for _detail in invoice.details.all()] or [NONE_ROW])
        
    else:
        form=InvoiceForm(request.POST.copy(),instance=invoice)
        
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
            
            TIME_SPAN_LIST=[x[1] for x in TIME_SPAN]
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 2 or i) for i in [0,4,6] if (not detail[i] or detail[i]<0) and (i!=4 or detail[i])]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            if detail[8]:
                                exists_key.append(detail[8])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
        
        
            if form.is_valid() and details_data and not details_data_error_count:
                
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=request.user
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.result=0
                invoice.save()
                
                if invoice_id:
                    #先清除没有的
                    all_key=list(invoice.details.values_list('id',flat=True))
                    delete_key=set(all_key)-set(exists_key)
                    invoice.details.filter(id__in=list(delete_key)).delete()
                
                total_price=0    
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[5] and (dd[5]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[5])[0]) or None
                        
                        num=good.change_nums(dd[4],unit)
                        
                        if dd[8]:
                            detail=InvoiceDetail.objects.get(pk=dd[8])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3])
                            detail.num1=dd[4]
                            detail.unit1=unit
                            detail.price=dd[6]
                            detail.total_price=dd[4]*dd[6]
                            detail.num=num
                            detail.last_nums=num
                        else:
                            detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                    batch_code=InvoiceDetail.get_next_detail_code(),warehouse_root=invoice.warehouse_root,
                                    warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3]),
                                    num1=dd[4],unit1=unit,price=dd[6],total_price=dd[4]*dd[6],
                                    num=num,last_nums=num
                                )
                        '''
                        '     更新单位单价
                        '''
                        if unit and unit.good:
                            unit.price=dd[6]
                            unit.save()
                        else:
                            good.price=dd[6]
                            good.save()
                            
                        
                        #if dd[4]:
                            #detail.shelf_life=dd[4]
                            #detail.shelf_life_type=TIME_SPAN_LIST.index(dd[5])+1
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                    
                
                        total_price+=detail.total_price
                    except:
                        print traceback.print_exc()
                        continue
                invoice.total_price=total_price
                invoice.save()

                transaction.commit()
                
                
                
                #if form.cleaned_data['sstatus'] and user_can_confirm_invoice(invoice.warehouse_root, invoice.invoice_type, request.user):
                    #try:
                        #invoice.confirm(request.user)
                    #except:
                        #print traceback.print_exc()
     
                if request.is_ajax():
                    transaction.commit()
                    return HttpResponse(simplejson.dumps(form.cleaned_data['sstatus'] and {'action':'goon','url':reverse('chushiruku',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
        except:
            transaction.rollback()
            print traceback.print_exc() 
        else:
           
            if request.is_ajax():
                form_error_dict={}
                
                if form.errors:
                    for error in form.errors:
                        e=form.errors[error]
                        form_error_dict[error]=unicode(e)
                transaction.rollback()
                return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
        template_var['form']=form

    response=render_to_response("main/chushiruku_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
        
    return response



@page_template('main/caigouruku_index.html')
def caigouruku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoiceSelectSimpleForm=make_InvoiceSelectSimpleForm(org,request.user)
    invoices = Invoice.objects.filter(org=org,invoice_type=1001,is_delete=0)
    

    template_var['invoices'] = invoices


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    result = request.GET.get('result')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        supplier = Supplier.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=supplier)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices
    '''
        if request.GET:
            form=invoiceSelectSimpleForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&warehouse=&status=10"%(reverse('caigouruku',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=invoiceSelectSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'status':10})
        
       
        if form.is_valid():
            invoices=Invoice.objects.filter(org=org,invoice_type=1001,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'],remark__contains=form.cleaned_data['remark'])
            if not form.cleaned_data['status']==10:
                invoices=invoices.filter(status=form.cleaned_data['status'])
            
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write','depot.warehouse_manage')):
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'])
                else:
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'],user=request.user)
            else:
                filters = [] 

                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write','depot.warehouse_manage')):
                        filters.append(Q(warehouse_root=warehouse)) 
                    else:
                        filters.append(Q(warehouse_root=warehouse,user=request.user))
                        
                q = reduce(operator.or_, filters) 

                invoices=invoices.filter(q)
                
            template_var['invoices']=invoices.distinct()
            
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            template_var['invoices_weijie']=invoices.filter(result=0).distinct().aggregate(sum=Sum('total_price'),count=Count('total_price'))
        else:
            template_var['invoices']=Invoice.objects.none()            
        template_var['form']=form
    '''
    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))


    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/caigouruku.html",template_var,context_instance=RequestContext(request))


'''
    新增采购入库
'''
#@anti_resubmit('caigouruku_add')
@transaction.commit_manually
def caigouruku_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*14
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice=None
    template_var['pay_details']=pay_details=[None,]
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
        try:
            template_var['pay_details']=pay_details=PayInvoice.objects.get(invoice_from=invoice).payinvoicedetail_set.all()
        except:
            template_var['pay_details']=pay_details=[None,]


        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=1001)
    template_var['accounts']=accounts=BankAccount.objects.filter(org=org,status=0)

    #权限判断
    if not request.user.has_org_perm(org,'depot.caigouruku_add'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    
    
    if request.method=="GET":
        template_var['form']=InvoiceForm(instance=invoice)

        
        template_var['warehouse_list_str']=simplejson.dumps(Warehouse.warehouse_list(org))
        template_var['time_span']=simplejson.dumps([unicode(x[1]) for x in TIME_SPAN])
        template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,'',_detail.good.name,_detail.warehouse.full_name,
                                               _detail.num1,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.total_price,_detail.pk,_detail.good.code,_detail.good.category.name,_detail.good.nums,_detail.good.min_warning,_detail.good.remark) for _detail in invoice.details.all()] or [NONE_ROW])
        
    else:
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
            
            TIME_SPAN_LIST=[x[1] for x in TIME_SPAN]
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]

                    
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 2 or i) for i in [0,4,6] if (not detail[i] or detail[i]<0) and (i!=4 or detail[i])]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            if detail[10]:
                                exists_key.append(detail[10])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
        except:
            transaction.rollback()
            print traceback.print_exc()
        
        if form.is_valid() and details_data and not details_data_error_count:
            try:
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                #为保证单据号一致，先save一次
                #invoice.save()

                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_next_invoice_code()
                    
                invoice.total_price=0
                invoice.save()

                if invoice_id:
                    #先清除没有的
                    '''
                    all_key=list(invoice.details.values_list('id',flat=True))
                    delete_key=set(all_key)-set(exists_key)
                    invoice.details.filter(id__in=list(delete_key)).delete()
                    '''
                    last_invoice=Invoice.objects.get(pk=invoice_id)
                    last_invoice.details.all().delete()
                
                total_price=0    
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        
                        
                 
                        unit=dd[5] and (dd[5]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[5])[0]) or None
                        
                        num=good.change_nums(dd[4],unit)
                       
                        '''if dd[8]:
                            
                            detail=InvoiceDetail.objects.get(pk=dd[8])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3])
                            detail.num1=dd[4]
                            detail.unit1=unit
                            detail.price=dd[6]
                            detail.total_price=dd[4]*dd[6]
                            detail.num=num
                            detail.last_nums=num
                        else:
                        '''
                        detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                batch_code=InvoiceDetail.get_next_detail_code(),warehouse_root=invoice.warehouse_root,
                                warehouse=Warehouse.warehouse_list_to_warehouse(org,dd[3]),
                                num1=dd[4],unit1=unit,price=dd[6],total_price=dd[4]*dd[6],
                                num=num,last_nums=num
                            )
                        '''
                        '     更新单位单价
                        '''
                        good.remark=dd[13]
                        if unit and unit.good:
                            unit.price=dd[6]
                            unit.save()
                        else:
                            good.price=dd[6]
                            good.save()
                            
                        
                        #if dd[4]:
                            #detail.shelf_life=dd[4]
                            #detail.shelf_life_type=TIME_SPAN_LIST.index(dd[5])+1
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        
                        
                        detail.save()
                        total_price+=detail.total_price
                    except:
                
                        print traceback.print_exc()
                        continue
                
                invoice.total_price=total_price
                invoice.save()
                
                
                '''
                if form.cleaned_data['sstatus'] and user_can_confirm_invoice(invoice.warehouse_root, invoice.invoice_type, request.user):
                    try:
                        invoice.confirm(request.user)
                    except:
                        print traceback.print_exc()
                '''
                #生成日志
                content = _(u"修改了单据%s") %invoice.invoice_code.encode('utf8')
                OperateLog.objects.create(created_user=request.user.username,org=org,content=content)
                

                
                

                #生成付款单
                if request.POST.get('pay'):

                    if request.POST.get('date') == '':
                        pay_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
                    else:
                        pay_date = request.POST.get('date')

                    if request.POST.get('pay_id'):

                        pay_invoice = PayInvoice.objects.get(pk=request.POST.get('pay_id'))
                        pay_invoice.payinvoicedetail_set.all().delete()
                        pay_invoice.content_object=form.cleaned_data['rels']
                        pay_invoice.invoice_type=3000
                        pay_invoice.already_pay = 0
                        pay_invoice.rest_pay = pay_invoice.total_pay
                        pay_invoice.save()
                        already_pay = request.POST.get('pay')

                        try:
                            already_pay = float(already_pay)
                        except:
                            pay_invoice.delete()
                            invoice.delete()
                            transaction.rollback()
                            template_var['error_msg'] = '付款金额填寫不正確'
                            return render_to_response("main/caigouruku_add.html",template_var,context_instance=RequestContext(request))
                        if already_pay == 0:
                            pass
                        elif abs(already_pay - invoice.total_price) < 0.0000001:
                            #权限判断
                            if not request.user.has_org_perm(org,'depot.fukuandan_modify'):
                                template_var['error_title'] = '你没有权限付款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=pay_date)
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay

                            if abs(already_pay - invoice.total_price) < 0.0000001:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save()
                            pay_invoice.save()
                            transaction.commit()

                        elif already_pay > invoice.total_price:
                            pay_invoice.delete()
                            invoice.delete()
                            transaction.rollback()
                            template_var['error_msg'] = '付款金额超过应付金额'
                            return render_to_response("main/caigouruku_add.html",template_var,context_instance=RequestContext(request))


                    else:

                        pay_invoice = PayInvoice.objects.create(org=org,invoice_code=PayInvoice.get_next_invoice_code(),charger=invoice.charger,user=invoice.user,total_pay=invoice.total_price,warehouse_root=invoice.warehouse_root,event_date=request.POST.get('event_date'),invoice_from=invoice,content_object=form.cleaned_data['rels'],invoice_type=3000)
                        already_pay = request.POST.get('pay')
                        pay_invoice.save()

                        if already_pay.replace('.', '', 1).isdigit():
                            already_pay = float(already_pay)
                        else:
                            pay_invoice.delete()
                            invoice.delete()
                            transaction.rollback()
                            template_var['error_msg'] = '付款金额填寫不正確'
                            return render_to_response("main/caigouruku_add.html",template_var,context_instance=RequestContext(request))

                        

                        if already_pay == 0:
                            pass
                            
                        elif abs(already_pay - invoice.total_price) < 0.0000001:
                            #权限判断


                            if not request.user.has_org_perm(org,'depot.fukuandan_add'):
                                pay_invoice.delete()
                                template_var['error_title'] = '你没有权限新增付款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=pay_date)
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay


                            
                            if abs(already_pay - invoice.total_price) < 0.0000001:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save()
                            pay_invoice.save()

                            transaction.commit()

                        elif already_pay > invoice.total_price:

                            try:
                                pay_invoice.delete()
                                invoice.delete()
                                transaction.rollback()
                                template_var['error_msg'] = '付款金额超过应付金额'
                                return render_to_response("main/caigouruku_add.html",template_var,context_instance=RequestContext(request))
                            except:
                                
                                print traceback.print_exc()
                                transaction.rollback()
                
                auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_caigouruku

                if auto_confirm and request.user.has_org_perm(org,'depot.caigouruku_confirm'):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')

                        invoice.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        invoice.save()
                        
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')

                transaction.commit()
     
                if request.is_ajax():
                    return HttpResponse(simplejson.dumps(form.cleaned_data['sstatus'] and {'action':'goon','url':reverse('caigouruku',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
            
            except:
                transaction.rollback()
                print traceback.print_exc()    
        else:
           
            if request.is_ajax():
                form_error_dict={}
                
                if form.errors:
                    for error in form.errors:
                        e=form.errors[error]
                        form_error_dict[error]=unicode(e)
                
                        
                transaction.rollback()
                return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
        template_var['form']=form
        
    response=render_to_response("main/caigouruku_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
 
    return response

'''
    生成物品json数据
'''
def get_goods_json(request,org_id):
    try:
        try:
            org=Organization.objects.get(slug=org_id)
        except:
            org=Organization.objects.get(pk=org_id)
          
        warehouse_id=request.GET.get('warehouse_id')
            
        goodsFilter=Goods.objects.filter(org=org).distinct().select_related()
        if warehouse_id and False:
            goodsFilter=goodsFilter.filter(details__warehouse_root=warehouse_id)
        
        need_batch=request.GET.get('use',0)
        goods_array=[]
        
     
        for goods in goodsFilter:
            goods_dict={'pk':goods.pk,'code':goods.code,'name':goods.name,'category_id':goods.category_id,'category':goods.category.name,
                        'is_batchs':goods.is_batchs,'unit_id':goods.unit_id,'unit':goods.unit and goods.unit.unit or '','abbreviation':goods.abbreviation,
                        'sale_price':goods.sale_price,'price':goods.price,'refer_price':goods.refer_price,'shelf_life':goods.shelf_life,'shelf_life_type':goods.get_shelf_life_type_display(),
                        'nums':goods.nums,'min_warning':goods.min_warning,'standard':goods.standard,'remark':goods.remark,'price_ori':goods.price_ori,'sale_price_ori':goods.sale_price_ori}
            
            auxiliary_unit=goods.auxiliary_unit.all()
            if auxiliary_unit.exists():
                goods_dict.update({'auxiliary_unit':list(auxiliary_unit.values('unit','rate','price','sale_price'))})
            if need_batch:
                if warehouse_id:
                    goods_dict.update({'batches':list(goods.details.filter(warehouse_root=warehouse_id,invoice__status=2,status=1,invoice__invoice_type__in=IN_BASE_TYPE,created_time__gte=datedelta(datetime.datetime.now(),0-goods.batch_range,1)).values('batch_code','unit1__unit','price')[:10])})
                else:
                    goods_dict.update({'batches':list(goods.details.filter(invoice__status=2,status=1,invoice__invoice_type__in=IN_BASE_TYPE,created_time__gte=datedelta(datetime.datetime.now(),0-goods.batch_range,1)).values('batch_code','unit1__unit','price')[:10])})
            goods_array.append(goods_dict)
       
        return HttpResponse("goods_json=%s"%simplejson.dumps(goods_array),mimetype="application/x-javascript")
    except:
        print traceback.print_exc()
        
'''
    生成调拨数据
'''
def get_diaobo_goods_json(request,org_id):
    try:
        try:
            org=Organization.objects.get(slug=org_id)
        except:
            org=Organization.objects.get(pk=org_id)
        
        warehouse_id=request.GET.get('warehouse_id',0)   
        goodsFilter=Goods.objects.filter(org=org,details__warehouse_root=warehouse_id).distinct().select_related()
        
        goods_array=[]
        for goods in goodsFilter:
            goods_dict={'pk':goods.pk,'code':goods.code,'name':goods.name,'category_id':goods.category_id,'category':goods.category.name,
                        'is_batchs':goods.is_batchs,'unit_id':goods.unit_id,'unit':goods.unit and goods.unit.unit or '','abbreviation':goods.abbreviation,
                        'sale_price':goods.sale_price,'price':goods.price,'refer_price':goods.refer_price,'shelf_life':goods.shelf_life,'shelf_life_type':goods.get_shelf_life_type_display()}
            
            auxiliary_unit=goods.auxiliary_unit.all()
            if auxiliary_unit.exists():
                goods_dict.update({'auxiliary_unit':list(auxiliary_unit.values('unit','rate','price','sale_price'))})
            
            if warehouse_id:
                goods_dict.update({'warehouses':[warehouse.full_name for warehouse in Warehouse.objects.filter(pk__in=list(goods.details.filter(warehouse_root_id=warehouse_id).values_list('warehouse_id',flat=True).distinct()))]})
            goods_array.append(goods_dict)
           
        return HttpResponse("goods_json=%s"%simplejson.dumps(goods_array),mimetype="application/x-javascript")    
    except:
        print traceback.print_exc()   
        
'''
    选区物品添加
'''
@page_template('main/select_goods_index.html') 
def select_goods(request,org_id,template="main/select_goods.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    SelectGoodsForm=make_SelectGoodsForm(org,request.user)
    _category=Category.objects.get(org=org,parent__isnull=True)    
    categorys=_category.get_descendants(include_self=True)
    warehouse_id=request.GET.get('warehouse_id',None)
    template_var['warehouse_id']=warehouse_id
    template_var['standard']=request.GET.get('standard','')
    
    if request.method=="GET":
        template_var['form']=SelectGoodsForm()

        form=SelectGoodsForm(request.GET.copy())
        if form.is_valid():
            category=form.cleaned_data['category']
            #warehouse=form.cleaned_data['warehouse']
            keyword=form.cleaned_data['keyword']
            
            goods=Goods.objects.filter(category__in=categorys,status=1).select_related('unit')
            #if warehouse_id:
            #    goods=goods.filter(details__invoice__warehouse_root_id=warehouse_id)
                
            if category:
                goods=goods.filter(category__in=category.get_descendants(include_self=True))
                
            if keyword:
                goods=goods.filter(Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword))
            
            
            template_var['goods']=goods.annotate(sum=Sum('details__last_nums'))
            template_var['form']=form
        else:
            print form.errors
    
    if extra_context is not None:
        template_var.update(extra_context)
    
    return render_to_response(template,template_var,context_instance=RequestContext(request))


'''
    查看单据
'''
def invoice_view(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice_code=request.GET.get('invoice_code',None)
    invoice=None
    pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
    template_var['pos_user']=pos_user
    
    try:
        if invoice_id:
            invoice=Invoice.objects.get(org=org,pk=invoice_id)
            template_var['invoice']=invoice
        elif invoice_code:
            template_var['invoice']=invoice=Invoice.objects.select_related().get(org=org,invoice_code=invoice_code)
    except:
        pass
    
    if not invoice:
        return HttpResponse(_(u'未找到单据，可能已被删除'))
    #warehouses=Warehouse.objects.filter(pk__in=invoice.details.values_list('warehouse_root',flat=True))
    
    #判断是否有审核权限
    #perm=True
    #for warehouse in warehouses:
    #    perm=perm and request.user.has_org_warehouse_perm(warehouse.pk,('depot.ruku_confirm','depot.warehouse_manage'))

    #template_var['confirm']=user_can_confirm_invoice(invoice.warehouse_root,invoice.invoice_type,request.user)
    
    return render_to_response("main/invoice_view.html",template_var,context_instance=RequestContext(request))

'''
    查看单据日志
'''
def invoice_view_log(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice_code=request.GET.get('invoice_code',None)
    invoice=None
    pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
    template_var['pos_user']=pos_user
    
    try:
        if invoice_id:
            template_var['invoice']=invoice=Invoice.objects.select_related().get(org=org,pk=invoice_id)
        elif invoice_code:
            template_var['invoice']=invoice=Invoice.objects.select_related().get(org=org,invoice_code=invoice_code)
    except:
        pass
    
    if not invoice:
        return HttpResponse(_(u'未找到单据，可能已被删除'))
    
    invocie_date=invoice.event_date
  
    seqs=SyncSeq.objects.filter(zdate=invoice.event_date,his__org=org).order_by('-id')
    template_var['hises']=SyncHis.objects.filter(id__in=list(seqs.values_list('his_id',flat=True))).select_related()
    
    return render_to_response("main/invoice_view_log.html",template_var,context_instance=RequestContext(request))

'''
    审核单据
'''
@transaction.commit_manually
def confirm_invoice(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    '''try:
        invoice_id=request.POST['invoice_id']
        invoice=Invoice.objects.get(pk=invoice_id)
       
        ret=invoice.confirm(request.user)
        
        if ret!=2:
            transaction.rollback()
            return HttpResponse(ret)
        transaction.commit()
        return HttpResponse(invoice_id)
    except:
        transaction.rollback()
        print traceback.print_exc()
    '''        
    try:
        invoice=Invoice.objects.get(pk=invoice_id)
        #判断是否为采购申请单
        if invoice.invoice_type == 1004:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoushenqing_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.status = 2
            invoice.confirm_user = request.user
            invoice.save()
            
            content=_(u"审核了采购申请单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            




            #若设置了自动采购入库，则生成采购入库单
            org_profile = OrgProfile.objects.get(org=org)
            if org_profile.is_auto_caigouruku:
                caigou_invoice = Invoice.objects.create(org=org,charger=invoice.charger,invoice_type=1001,remark="自动生成",event_date=datetime.date.today(),content_type=ContentType.objects.get_for_model(Supplier),object_id=invoice.object_id,user=request.user,invoice_code=Invoice.get_next_invoice_code(),invoice_from=invoice)

                caigou_invoice.content_object=invoice.content_object
                caigou_invoice.warehouse_root=invoice.warehouse_root

                total_price = 0
                sale_price = 0

                for _detail in invoice.details.all():
                    InvoiceDetail.objects.create(invoice=caigou_invoice,good=_detail.good,batch_code=_detail.batch_code,\
                        warehouse=_detail.warehouse,warehouse_root=_detail.warehouse_root,num1=_detail.num1,unit1=_detail.unit1,\
                        price=_detail.price,avg_price=_detail.avg_price,num=_detail.num,last_nums=_detail.last_nums,remark="申请单自动生成",\
                        total_price=_detail.total_price,chenben_price=_detail.chenben_price)

                    total_price = total_price+_detail.total_price
                    sale_price = sale_price+_detail.price

                caigou_invoice.total_price = total_price
                caigou_invoice.sale_price = sale_price
                caigou_invoice.save()


                    

                content = _(u"自动生成了单据%s") %caigou_invoice.invoice_code.encode('utf8')
                OperateLog.objects.create(created_user="自动生成",org=org,content=content)


                

            transaction.commit()


            #if request.is_ajax():
                #return HttpResponse(simplejson.dumps({'action':'goon','url':reverse('caigoushenqing_view',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')

            return HttpResponseRedirect(reverse("caigoushenqing_view",args=[org.uid]))


        elif invoice.invoice_type == 1001 or invoice.invoice_type == 1000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigouruku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.confirm(request.user)


            content=_(u"审核了采购入库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            if invoice.invoice_type == 1001:
                return HttpResponseRedirect(reverse("caigouruku",args=[org.uid]))
            elif invoice.invoice_type == 1000:
                return HttpResponseRedirect(reverse("chushiruku",args=[org.uid]))

        elif invoice.invoice_type == 2002:
            #权限判断
            if not request.user.has_org_perm(org,'depot.xiaoshouchuku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.confirm(request.user)

            content=_(u"审核了销售出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()
            return HttpResponseRedirect(reverse("xiaoshouchuku",args=[org.uid]))

        elif invoice.invoice_type == 2001:
            #权限判断
            if not request.user.has_org_perm(org,'depot.lingyongchuku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.confirm(request.user)

            content=_(u"审核了领用出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()
            return HttpResponseRedirect(reverse("lingyongchuku",args=[org.uid]))

        elif invoice.invoice_type == 2000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoutuihuo_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            res = invoice.confirm(request.user)
            if res == -1:
                template_var['error_title'] = '库存数量不足'
                response = render_to_response("500.html",template_var,context_instance=RequestContext(request))
                transaction.rollback()
                return response

            content=_(u"审核了采购退货单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()
            return HttpResponseRedirect(reverse("caigoutuihuo",args=[org.uid]))

    except:
        transaction.rollback()
        print traceback.print_exc()



'''
    反审核单据
'''
@transaction.commit_manually
def unconfirm_invoice(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    '''try:
        invoice_id=request.POST['invoice_id']
        invoice=Invoice.objects.get(pk=invoice_id)
        
        ret=invoice.unconfirm()
        
        if ret==-1:
            transaction.rollback()
            return HttpResponse(_(u'单据库存已消耗，不能再进行反审核'))
        transaction.commit()
        return HttpResponse(invoice_id)
    except:
        transaction.rollback()
        print traceback.print_exc()
    '''
    try:
        invoice=Invoice.objects.get(pk=invoice_id)
        #判断是否为采购申请单
        if invoice.invoice_type == 1004:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoushenqing_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.status = 1
            invoice.confirm_user = None
            invoice.save()
            
            content=_(u"反审核了采购申请单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("caigoushenqing_view",args=[org.uid]))

        elif invoice.invoice_type == 1001 or invoice.invoice_type == 1000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigouruku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            ret = invoice.unconfirm()

            if ret==-1:
                transaction.rollback()

                content=_(u"反审核采购入库单%s失败，原因：单据内存已消耗") %invoice.invoice_code.encode("utf8")
                OperateLog.objects.create(org=org,created_user=request.user.username,content=content)
                transaction.commit()
                return HttpResponse(_(u'单据库存已消耗，不能再进行反审核'))
            
            content=_(u"反审核了采购入库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            #若同时生成了付款单，反审核后删除
            try:
                invoice.payinvoice_set.all().delete()
            except:
                pass

            transaction.commit()

            if invoice.invoice_type == 1000:
                return HttpResponseRedirect(reverse("chushiruku",args=[org.uid]))
            elif invoice.invoice_type == 1001:
                return HttpResponseRedirect(reverse("caigouruku",args=[org.uid]))

        elif invoice.invoice_type == 2002:
            #权限判断
            if not request.user.has_org_perm(org,'depot.xiaoshouchuku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")


            invoice.unconfirm()

            #若同时生成了收款单，反审核后删除
            try:
                invoice.payinvoice_set.all().delete()
            except:
                pass
            
            content=_(u"反审核了销售出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("xiaoshouchuku",args=[org.uid]))

        elif invoice.invoice_type == 2001:
            #权限判断
            if not request.user.has_org_perm(org,'depot.lingyongchuku_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")


            invoice.unconfirm()
            
            content=_(u"反审核了领用出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("lingyongchuku",args=[org.uid]))

        elif invoice.invoice_type == 2000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoutuihuo_confirm'):
                transaction.rollback()
                return HttpResponse("你没有权限")


            invoice.unconfirm()

            #若同时生成了收款单，反审核后删除
            try:
                invoice.payinvoice_set.all().delete()
            except:
                pass
            
            content=_(u"反审核了采购退货单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("caigoutuihuo",args=[org.uid]))


    except:
        transaction.rollback()
        print traceback.print_exc() 
'''
    删除单据
'''
@transaction.commit_manually
def delete_invoice(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    '''
    try:
        invoice_id=request.POST['invoice_id']
        invoice=Invoice.objects.get(pk=invoice_id)
        if invoice.status!=2:
            invoice_content=ContentType.objects.get_for_model(invoice)
            Invoice.objects.filter(content_type=invoice_content,object_id=invoice_id).delete()
            invoice.delete()
        else:
            return HttpResponse(_(u'不能删除已审核单据'))
        
        transaction.commit()
        return HttpResponse(invoice_id)
    except:
        transaction.rollback()
        print traceback.print_exc()
    '''
    try:
        invoice=Invoice.objects.get(pk=invoice_id)
        if invoice.status == 2:
            transaction.rollback()
            return HttpResponse("审核过的单据无法删除")
        if invoice.invoice_type == 1004:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoushenqing_delete'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.is_delete = 1

            invoice.save()
            
            content=(u"删除了采购申请单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("caigoushenqing_view",args=[org.uid]))

        elif invoice.invoice_type == 1001 or invoice.invoice_type == 1000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigouruku_delete'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.is_delete = 1

            invoice.save()
            
            content=_(u"删除了采购入库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            if invoice.invoice_type == 1001:
                return HttpResponseRedirect(reverse("caigouruku",args=[org.uid]))
            elif invoice.invoice_type == 1000:
                return HttpResponseRedirect(reverse("chushiruku",args=[org.uid]))

        elif invoice.invoice_type == 2002:
            #权限判断
            if not request.user.has_org_perm(org,'depot.xiaoshouchuku_delete'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.is_delete = 1

            invoice.save()
            
            content=_(u"删除了销售出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("xiaoshouchuku",args=[org.uid]))

        elif invoice.invoice_type == 2001:
            #权限判断
            if not request.user.has_org_perm(org,'depot.lingyongchuku_delete'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.is_delete = 1

            invoice.save()
            
            content=_(u"删除了领用出库单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("lingyongchuku",args=[org.uid]))

        elif invoice.invoice_type == 2000:
            #权限判断
            if not request.user.has_org_perm(org,'depot.caigoutuihuo_delete'):
                transaction.rollback()
                return HttpResponse("你没有权限")

            invoice.is_delete = 1

            invoice.save()
            
            content=_(u"删除了采购退货单%s") %invoice.invoice_code.encode("utf8")
            OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

            transaction.commit()

            return HttpResponseRedirect(reverse("caigoutuihuo",args=[org.uid]))


    except:
        transaction.rollback()
        print traceback.print_exc()  
        
'''
    采购退货
'''
@page_template('main/caigoutuihuo_index.html')
def caigoutuihuo(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()

    invoices = Invoice.objects.filter(org=org,invoice_type=2000,is_delete=0)

    template_var['invoices'] = invoices

    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    result = request.GET.get('result')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        supplier = Supplier.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=supplier)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices
    

    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/caigoutuihuo.html",template_var,context_instance=RequestContext(request))

'''
    采购退货form
'''
#@anti_resubmit("caigoutuihuo_add")
@transaction.commit_manually
def caigoutuihuo_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*15
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    #权限判断 
    if not request.user.has_org_perm(org,'depot.caigoutuihuo_add'):
        transaction.rollback()
        return HttpResponse("你没有权限")

    invoice=None
    extra=1
    template_var['pay_details']=pay_details=[None,]
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)


        try:
            template_var['pay_details']=pay_details=PayInvoice.objects.get(invoice_from=invoice).payinvoicedetail_set.all()
        except:
            template_var['pay_details']=pay_details=[None,]
        
        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=2000)
    template_var['accounts']=accounts=BankAccount.objects.filter(org=org,status=0)
    
    if request.method=="GET":

        template_var['form']=InvoiceForm(instance=invoice)
        
        try:
            if invoice.status == 2:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums+_detail.num,'') for _detail in invoice.details.all()] or [NONE_ROW])

            else:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])
        except:
            template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])
    else:
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
                
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 1 or i) for i in [0,2,5,9] if (not detail[i] or (i!=2 and detail[i]<0))]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            #if detail[7]:
                                #exists_key.append(detail[7])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)

            #查看相关单据是否存在
            invoice_from = request.POST.get('invoice_from')
            if invoice_from:
                try:
                    invoice_from = Invoice.objects.get(org=org,is_delete=0,invoice_code=invoice_from)
                except:
                    form.errors['invoice_from']="error"
            else:
                invoice_from=None

            
            if form.is_valid() and details_data and not details_data_error_count:
                invoice=form.save(commit=False)


                invoice.org=org
                invoice.charger=request.user
                invoice.invoice_from=invoice_from
                invoice.content_object=form.cleaned_data['rels']
                invoice.status = 1
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_org_next_invoice_code(org)
                invoice.total_price=0
                invoice.save()
                
                if invoice_id:
                    #先清除没有的
                    #all_key=list(invoice.details.values_list('id',flat=True))
                    #delete_key=set(all_key)-set(exists_key)
                    #invoice.details.filter(id__in=list(delete_key)).delete()
                    last_invoice=Invoice.objects.get(pk=invoice_id)
                    last_invoice.details.all().delete()

    
                total_price=0
                chenben_price=0
            
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[7] and (dd[7]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[7])[0]) or None
                        
                        before_change_num = good.nums

                        num=good.change_nums(dd[5],unit)

                        
                        '''if dd[7]:
                            detail=InvoiceDetail.objects.get(pk=dd[7])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=invoice.warehouse_root
                            detail.num1=dd[3]
                            detail.unit1=unit
                            detail.price=dd[5]
                            detail.total_price=dd[3]*dd[5]
                            detail.num=num
                            detail.last_nums=num
                        else:'''
                        detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                warehouse_root=invoice.warehouse_root,warehouse=invoice.warehouse_root,
                                num1=dd[5],unit1=unit,price=dd[9],total_price=dd[5]*dd[9],
                                num=num,last_nums=num,num_at_that_time=before_change_num
                            )
                        
                        #detail.chenben_price=good.chengben_price*num
                        detail.chenben_price=good.price_ori*num
                        '''
                        批次计算
                        if dd[2]:
                            
                            details=InvoiceDetail.objects.filter(invoice__status=2,batch_code=dd[2])
                            if details:
                                DetailRelBatch.objects.get_or_create(from_batch=detail,to_batch=details[0],level=True)
                                detail.chenben_price=InvoiceDetail.objects.get(good=good,batch_code=dd[2]).avg_price*num
                        '''    
                            
                        if unit and unit.good:
                            unit.sale_price=dd[9]
                            unit.save()
                        else:
                            good.sale_price=dd[9]
                            good.save()
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                        
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price
                        
                    except:
                        print traceback.print_exc()
                        continue
                
                
                invoice.total_price=total_price
                
                invoice.sale_price=chenben_price
                invoice.save()
            
                auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_caigoutuihuo


                        
                    
                if auto_confirm and request.user.has_org_perm(org,'depot.caigoutuihuo_confirm'):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')

                        invoice.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        invoice.save()
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')
          
                
                

                #生成收款单
                if request.POST.get('pay'):

                    if request.POST.get('pay_id'):

                        pay_invoice = PayInvoice.objects.get(pk=request.POST.get('pay_id'))
                        pay_invoice.payinvoicedetail_set.all().delete()
                        pay_invoice.content_object=form.cleaned_data['rels']
                        pay_invoice.invoice_type=3001
                        pay_invoice.already_pay = 0
                        pay_invoice.rest_pay = pay_invoice.total_pay
                        pay_invoice.save()
                        already_pay = request.POST.get('pay')

                        try:
                            already_pay = float(already_pay)
                        except:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额填寫不正確'
                            return render_to_response("main/caigoutuihuo_add.html",template_var,context_instance=RequestContext(request))
                        if already_pay == 0:
                            pass
                        elif already_pay > invoice.total_price:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额超过应付金额'
                            return render_to_response("main/caigoutuihuo_add.html",template_var,context_instance=RequestContext(request))
                        else:
                            #权限判断
                            if not request.user.has_org_perm(org,'depot.shoukuandan_modify'):
                                template_var['error_title'] = '你没有权限新增收款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=request.POST.get('date'))
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay
                            if already_pay == invoice.total_price:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save() 
                            pay_invoice.save()


                    else:
                        pay_invoice = PayInvoice.objects.create(org=org,invoice_code=PayInvoice.get_next_invoice_code(),charger=invoice.charger,user=invoice.user,total_pay=invoice.total_price,warehouse_root=invoice.warehouse_root,event_date=request.POST.get('event_date'),invoice_from=invoice,content_object=form.cleaned_data['rels'],invoice_type=3001)
                        already_pay = request.POST.get('pay')
                        pay_invoice.save()
                        try:
                            already_pay = float(already_pay)
                        except:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额填寫不正確'
                            return render_to_response("main/caigoutuihuo_add.html",template_var,context_instance=RequestContext(request))
                        if already_pay == 0:
                            pass
                        elif already_pay > invoice.total_price:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额超过应付金额'
                            return render_to_response("main/caigoutuihuo_add.html",template_var,context_instance=RequestContext(request))
                            
                        else:
                            #权限判断
                            if not request.user.has_org_perm(org,'depot.shoukuandan_add'):
                                pay_invoice.delete()
                                template_var['error_title'] = '你没有权限新增收款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=request.POST.get('date'))
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay
                            if already_pay == invoice.total_price:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save()
                            pay_invoice.save()

                transaction.commit()

                if request.is_ajax():

                    return HttpResponse(simplejson.dumps({'action':'goon','url':reverse('caigoutuihuo',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
    
                
            else:
                if request.is_ajax():
                   
                    form_error_dict={}

                   
                    if form.errors:
                        for error in form.errors:
                            e=form.errors[error]
                            form_error_dict[error]=unicode(e)

                   
               
                    transaction.rollback()
                    
                    return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
                    
            template_var['form']=form

        
        except:
            print traceback.print_exc()

    response=render_to_response("main/caigoutuihuo_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
    return response

'''
    查找使用物品
'''
@page_template('main/select_goods_use_index.html') 
def select_goods_use(request,org_id,template="main/select_goods_use.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    SelectGoodsForm=make_SelectGoodsForm(org,request.user)
    _category=Category.objects.get(org=org,parent__isnull=True)    
    categorys=_category.get_descendants(include_self=True)
    supplier_id=request.GET.get('supplier_id',None)
    warehouse_id=request.GET.get('warehouse_id',None)
    root_warehouse=Warehouse.objects.get(pk=warehouse_id)
    template_var['supplier_id']=supplier_id
    template_var['warehouse_id']=warehouse_id
    
    if request.method=="GET":
        template_var['form']=SelectGoodsForm()

        form=SelectGoodsForm(request.GET.copy())
        if form.is_valid():
            category=form.cleaned_data['category']
            warehouse=form.cleaned_data['warehouse'] 
            keyword=form.cleaned_data['keyword']
            
            goods=Goods.objects.filter(category__in=categorys).select_related('unit')
            goods=goods.filter(details__warehouse_root=root_warehouse)
            if warehouse:
                goods=goods.filter(details__warehouse=warehouse)
                
            if category:
                goods=goods.filter(category__in=category.get_descendants(include_self=True))
                
            
            '''
            ' supplier已弃用，实行宽松的出库规则，在库即可
            '''
            if False and supplier_id:
                #采购退货
                template_var['supplier']=Supplier.objects.get(pk=supplier_id)
                content_type=ContentType.objects.get_for_model(Supplier)
                
                if keyword:
                    #goods=goods.filter(
                    #                Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).filter(details__invoice__invoice_type__in=[1001,1000,1009],details__invoice__content_type=ContentType.objects.get_for_model(Supplier),
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__object_id=supplier_id,details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.filter(
                                    Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s depot_ininvoice.object_id=%s'%(IN_BASE_TYPE_STR,warehouse_id,content_type.pk,supplier_id),when=True))
                
                else:
                    #goods=goods.filter(details__invoice__invoice_type__in=[1001,1000,1009],details__invoice__content_type=ContentType.objects.get_for_model(Supplier),
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__object_id=supplier_id,details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s and depot_ininvoice.object_id=%s'%(IN_BASE_TYPE_STR,warehouse_id,content_type.pk,supplier_id),when=True))
                    
                details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,invoice__content_type=content_type,invoice__object_id=supplier_id,
                                                  invoice__warehouse_root_id=warehouse_id,invoice__status=2,last_nums__gt=0)) for good in goods]
                    
            else:
                #领用出库
                template_var['supplier']=None
                
                if keyword:
                    #goods=goods.filter(
                    #                Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).filter(details__invoice__invoice_type__in=[1001,1000,1009],
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.filter(
                                    Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
                else:
                    #goods=goods.filter(details__invoice__invoice_type__in=[1001,1000,1009],
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                
                    goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
                    
                content_type=ContentType.objects.get_for_model(Supplier)
                details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,
                                                  invoice__warehouse_root_id=warehouse_id,invoice__status=2,last_nums__gt=0)) for good in goods]
               
            template_var['goods_details']=zip(goods,details)

            template_var['form']=form
        else:
            print form.errors
    
    if extra_context is not None:
        template_var.update(extra_context)
    
    return render_to_response(template,template_var,context_instance=RequestContext(request))

'''
    查找使用物品
'''
@page_template('main/select_goods_use_diaobo_index.html') 
def select_goods_use_kuweidiaobo(request,org_id,template="main/select_goods_use.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    SelectGoodsForm=make_SelectGoodsForm(org,request.user)
    _category=Category.objects.get(org=org,parent__isnull=True)    
    categorys=_category.get_descendants(include_self=True)
    supplier_id=request.GET.get('supplier_id',None)
    warehouse_id=request.GET.get('warehouse_id',None)
    template_var['supplier_id']=supplier_id
    template_var['warehouse_id']=warehouse_id
    
    if request.method=="GET":
        template_var['form']=SelectGoodsForm()

        form=SelectGoodsForm(request.GET.copy())
        if form.is_valid():
            category=form.cleaned_data['category']
            warehouse=form.cleaned_data['warehouse']
            keyword=form.cleaned_data['keyword']
            
            goods=Goods.objects.filter(category__in=categorys).select_related('unit')
            if warehouse:
                goods=goods.filter(details__warehouse=warehouse)
                
            if category:
                goods=goods.filter(category__in=category.get_descendants(include_self=True))
                
            
            if supplier_id:
                #采购退货
                template_var['supplier']=Supplier.objects.get(pk=supplier_id)
                content_type=ContentType.objects.get_for_model(Supplier)
                
                if keyword:
                    goods=goods.filter(
                                    Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s and depot_ininvoice.object_id=%s'%(IN_BASE_TYPE_STR,warehouse_id,content_type.pk,supplier_id),when=True))
                else:
                    #goods=goods.filter(details__invoice__invoice_type__in=[1001,1000,1009],details__invoice__content_type=ContentType.objects.get_for_model(Supplier),
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__object_id=supplier_id,details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s and depot_ininvoice.object_id=%s'%(IN_BASE_TYPE_STR,warehouse_id,content_type.pk,supplier_id),when=True))
                
                details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,invoice__content_type=content_type,invoice__object_id=supplier_id,
                                                  invoice__warehouse_root_id=warehouse_id,invoice__status=2,last_nums__gt=0)) for good in goods]
                    
            else:
                #领用出库
                template_var['supplier']=None
                
                if keyword:
                    goods=goods.filter(
                                    Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
                    
                else:

                    #goods=goods.filter(details__invoice__invoice_type__in=[1001,1000,1009],
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                
                    goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
                    
                content_type=ContentType.objects.get_for_model(Supplier)
                details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,
                                                  invoice__warehouse_root_id=warehouse_id,invoice__status=2,last_nums__gt=0)) for good in goods]
               
            template_var['goods_details']=zip(goods,details)

            template_var['form']=form
        else:
            print form.errors
    
    if extra_context is not None:
        template_var.update(extra_context)
    
    return render_to_response(template,template_var,context_instance=RequestContext(request))

'''
    领用出库
'''
@page_template('main/lingyongchuku_index.html')
def lingyongchuku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()

    invoices = Invoice.objects.filter(org=org,invoice_type=2001,is_delete=0)

    template_var['invoices'] = invoices

    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    result = request.GET.get('result')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        department = ConDepartment.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=department)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices
    

    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/lingyongchuku.html",template_var,context_instance=RequestContext(request))

'''
    新增领用出库
'''
#@anti_resubmit('lingyongchuku_add')
@transaction.commit_manually
def lingyongchuku_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*15
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    #权限判断 
    if not request.user.has_org_perm(org,'depot.lingyongchuku_add'):
        transaction.rollback()
        return HttpResponse("你没有权限")

    invoice=None
    extra=1
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
        
        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=2001)
    
    if request.method=="GET":

        template_var['form']=InvoiceForm(instance=invoice)
        
        try:
            if invoice.status == 2:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums+_detail.num,'') for _detail in invoice.details.all()] or [NONE_ROW])

            else:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])
        except:
            template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])
    else:
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
                
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 1 or i) for i in [0,2,5,9] if (not detail[i] or (i!=2 and detail[i]<0))]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            #if detail[7]:
                                #exists_key.append(detail[7])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
                    
            if form.is_valid() and details_data and not details_data_error_count:
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                invoice.status = 1
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_org_next_invoice_code(org)
                invoice.total_price=0
                invoice.save()
                
                if invoice_id:
                    #先清除没有的
                    #all_key=list(invoice.details.values_list('id',flat=True))
                    #delete_key=set(all_key)-set(exists_key)
                    #invoice.details.filter(id__in=list(delete_key)).delete()
                    last_invoice=Invoice.objects.get(pk=invoice_id)
                    last_invoice.details.all().delete()

    
                total_price=0
                chenben_price=0
            
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[7] and (dd[7]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[7])[0]) or None

                        before_change_num = good.nums
                        

                        num=good.change_nums(dd[5],unit)

                        
                        '''if dd[7]:
                            detail=InvoiceDetail.objects.get(pk=dd[7])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=invoice.warehouse_root
                            detail.num1=dd[3]
                            detail.unit1=unit
                            detail.price=dd[5]
                            detail.total_price=dd[3]*dd[5]
                            detail.num=num
                            detail.last_nums=num
                        else:'''
                        print dd[9],'asdf','aaa'
                        detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                warehouse_root=invoice.warehouse_root,warehouse=invoice.warehouse_root,
                                num1=dd[5],unit1=unit,price=dd[9],total_price=dd[5]*dd[9],
                                num=num,last_nums=num,num_at_that_time=before_change_num
                            )
                        
                        #detail.chenben_price=good.chengben_price*num
                        detail.chenben_price=good.price_ori*num
                        '''
                        批次计算
                        if dd[2]:
                            
                            details=InvoiceDetail.objects.filter(invoice__status=2,batch_code=dd[2])
                            if details:
                                DetailRelBatch.objects.get_or_create(from_batch=detail,to_batch=details[0],level=True)
                                detail.chenben_price=InvoiceDetail.objects.get(good=good,batch_code=dd[2]).avg_price*num
                        '''    
                            
                        if unit and unit.good:
                            unit.sale_price=dd[9]
                            unit.save()
                        else:
                            good.sale_price=dd[9]
                            good.save()
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                        
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price
                        
                    except:
                        print traceback.print_exc()
                        continue
                
                
                invoice.total_price=total_price
                
                invoice.sale_price=chenben_price
                invoice.save()
            
                auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_lingyongchuku


                        
                    
                if auto_confirm and request.user.has_org_perm(org,'depot.lingyongchuku_confirm'):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')

                        invoice.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        invoice.save()
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')
          
                
                


                if request.is_ajax():
                    transaction.commit()
                    return HttpResponse(simplejson.dumps({'action':'goon','url':reverse('lingyongchuku',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
    
                
            else:
                if request.is_ajax():
                   
                    form_error_dict={}
                    
                    if form.errors:
                        for error in form.errors:
                            e=form.errors[error]
                            form_error_dict[error]=unicode(e)
                   
               
                    transaction.rollback()

                    
                    return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
                    
            template_var['form']=form
        
        except:
            print traceback.print_exc()

    response=render_to_response("main/lingyongchuku_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
    return response


'''
    退料入库
'''
@page_template('main/tuiliaoruku_index.html')
def tuiliaoruku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    InvoiceConSimpleForm=make_InvoiceConSimpleForm(org,request.user)
    
    
    if request.method=="GET":
        if request.GET:
            form=InvoiceConSimpleForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&warehouse=&conDepartment="%(reverse('tuiliaoruku',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=InvoiceConSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'conDepartment':None})
            
        if form.is_valid():
            invoices=Invoice.objects.filter(org=org,invoice_type=1002,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'])
            
            if form.cleaned_data['conDepartment']:
                invoices=invoices.filter(content_type=ContentType.objects.get_for_model(form.cleaned_data['conDepartment']),object_id=form.cleaned_data['conDepartment'].pk)
            
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write','depot.warehouse_manage')):
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'])
                else:
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'],user=request.user)
            else:
                filters = [] 
                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write','depot.warehouse_manage')):
                        filters.append(Q(warehouse_root=warehouse)) 
                    else:
                        filters.append(Q(warehouse_root=warehouse,user=request.user))
                        
                q = reduce(operator.or_, filters) 

                invoices=invoices.filter(q)
                
            template_var['invoices']=invoices.distinct()
            
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            template_var['invoices_weijie']=invoices.filter(result=0).distinct().aggregate(sum=Sum('total_price'),count=Count('total_price'))
        else:
            template_var['invoices']=Invoice.objects.none() 
        
        template_var['form']=form    
        if extra_context is not None:
            template_var.update(extra_context)
    return render_to_response("main/tuiliaoruku.html",template_var,context_instance=RequestContext(request))


'''
    退料入库form
'''
@transaction.commit_manually  
def tuiliaoruku_add(request,org_id,invoice_id=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()
    
    invoice=None
    extra=1
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
        if invoice.details.all().count():
            extra=0
        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=1002)
    InvoiceTuiKuDetailForm=make_InvoiceTuiKuDetailForm(org,request.user)
    InvoicFormset=inlineformset_factory(Invoice,InvoiceDetail, form=InvoiceTuiKuDetailForm, exclude=('created_time','modify_time','status','num','warehouse','shelf_life_type','warehouse_root','last_nums','batch_code','rel_batchs','chenben_price'),extra=extra,can_delete=True)
    
    if request.method=="GET":
        template_var['form']=InvoiceForm(instance=invoice)
        template_var['formset']=InvoicFormset(instance=invoice)
    else:
        form=InvoiceForm(request.POST.copy(),instance=invoice)
        formset=InvoicFormset(request.POST.copy(),instance=invoice)
        
        if form.is_valid() and formset.is_valid():
            try:
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.result=1
                invoice.save()
                
                for _form in formset.forms:
                    if _form.changed_data:
                        detail=_form.save(commit=False)
                        if _form['DELETE'].value():
                            detail.delete()
                        else:    
                            detail.invoice=invoice
                            detail.num=_form.cleaned_data['good'].change_nums(detail.num1,detail.unit1)
                            detail.last_nums=detail.num
                            #退料入库，根据物品指定价格
                            batch_rel=_form.cleaned_data['batch_rel']
                            detail.avg_price=batch_rel and batch_rel.avg_price or detail.good.refer_price
                            detail.total_price=detail.avg_price*detail.num
                            detail.price=detail.avg_price*_form.cleaned_data['good'].change_nums(1,detail.unit1)
                            
                            detail.save()
                            
                            
                            if batch_rel:
                                #detail.rel_batchs.add(batch_rel)
                                #DetailRelBatch.objects.create(from_batch=detail,to_batch=batch_rel)
                                DetailRelBatch.objects.get_or_create(from_batch=detail,to_batch=batch_rel,level=True)
                            
                            invoice.total_price+=detail.total_price
                
                invoice.save()
                
                if request.POST.get('confirm') and form.cleaned_data['sstatus'] and user_can_confirm_invoice(invoice.warehouse_root, invoice.invoice_type, request.user):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'confirm_error':res}),mimetype='application/json')
                    except:
                        print traceback.print_exc()
                transaction.commit()        
                if request.is_ajax():
                    return HttpResponse(reverse('tuiliaoruku',args=[org.uid]))
            except:
                print traceback.print_exc()
        else:
            if request.is_ajax():
                form_error_dict={}
                formset_error_list=[]
                
                if form.errors:
                    for error in form.errors:
                        e=form.errors[error]
                        form_error_dict[error]=unicode(e)
                        
                for _form in formset.forms:
                    _form_error_dict={}
                    if _form.errors:
                        for error in _form.errors:
                            e=_form.errors[error]
                            _form_error_dict[_form.prefix+'-'+error]=unicode(e)
                            
                    formset_error_list.append(_form_error_dict)
                transaction.rollback()    
                return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,
                                    'formset_error_list':formset_error_list}),mimetype='application/json')
        
        template_var['form']=form
        template_var['formset']=formset 
    response=render_to_response("main/tuiliaoruku_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
    return response



'''
    选择退料入库
'''
@page_template('main/select_goods_tuiku_index.html') 
def select_goods_tuiku(request,org_id,template="main/select_goods_tuiku.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    SelectGoodsForm=make_SelectGoodsForm(org,request.user)
    _category=Category.objects.get(org=org,parent__isnull=True)    
    categorys=_category.get_descendants(include_self=True)
    department_id=request.GET.get('department_id',None)
    warehouse_id=request.GET.get('warehouse_id',None)
    template_var['department_id']=department_id
    template_var['warehouse_id']=warehouse_id
    
    if request.method=="GET":
        template_var['form']=SelectGoodsForm()

        form=SelectGoodsForm(request.GET.copy())
        if form.is_valid():
            category=form.cleaned_data['category']
            warehouse=form.cleaned_data['warehouse']
            keyword=form.cleaned_data['keyword']
            
            goods=Goods.objects.filter(category__in=categorys).select_related('unit')
            if warehouse:
                goods=goods.filter(details__warehouse=warehouse)
                
            if category:
                goods=goods.filter(category__in=category.get_descendants(include_self=True))
                
            
            if department_id:
                #采购退货
                template_var['department']=ConDepartment.objects.get(pk=department_id)
                content_type=ContentType.objects.get_for_model(ConDepartment)
                
                if keyword:
                    #goods=goods.filter(
                    #                Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).filter(details__invoice__invoice_type=2001,details__invoice__content_type=ContentType.objects.get_for_model(ConDepartment),
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__object_id=department_id,details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.filter(
                                    Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type=2001 and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s and depot_ininvoice.object_id=%s'%(warehouse_id,content_type.pk,department_id),when=True))
                else:
                    #goods=goods.filter(details__invoice__invoice_type=2001,details__invoice__content_type=ContentType.objects.get_for_model(ConDepartment),
                    #                details__invoice__warehouse_root_id=warehouse_id,
                    #               details__invoice__object_id=department_id,details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
                    goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type=2001 and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_ininvoice.content_type_id=%s and depot_ininvoice.object_id=%s'%(warehouse_id,content_type.pk,department_id),when=True))
                
                details=[list(good.details.filter(invoice__invoice_type=2001,invoice__content_type=content_type,invoice__object_id=department_id,
                                                  invoice__warehouse_root_id=warehouse_id,invoice__status=2,last_nums__gt=0)) for good in goods]
                    
               
            template_var['goods_details']=zip(goods,details)
            template_var['form']=form
        else:
            print form.errors
    
    if extra_context is not None:
        template_var.update(extra_context)
    
    return render_to_response(template,template_var,context_instance=RequestContext(request))




'''
    销售出库
'''
@page_template('main/xiaoshouchuku_index.html')
def xiaoshouchuku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()

    invoices = Invoice.objects.filter(org=org,invoice_type=2002,is_delete=0)
    template_var['invoices'] = invoices
    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    result = request.GET.get('result')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        customer = Customer.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=customer)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices
    
    '''
    InvoiceSaleSimpleForm=make_InvoiceSaleSimpleForm(org,request.user)
    
    
    if request.method=="GET":
        if request.GET:
            form=InvoiceSaleSimpleForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&warehouse=&customer="%(reverse('xiaoshouchuku',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=InvoiceSaleSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'customer':None})
            
        if form.is_valid():
            invoices=Invoice.objects.filter(org=org,invoice_type=2002,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'],remark__contains=form.cleaned_data['remark'])
           
            
            if form.cleaned_data['customer']:
                if form.cleaned_data['customer'].pk == -1:
                    invoices=invoices.filter(content_type=ContentType.objects.get_for_model(OrgPOS))
                else:  
                    invoices=invoices.filter(content_type=ContentType.objects.get_for_model(form.cleaned_data['customer']),object_id=form.cleaned_data['customer'].pk)
                
            
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write','depot.warehouse_manage')):
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'])
                else:
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'],user=request.user)
            else:
                filters = [] 
                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write','depot.warehouse_manage')):
                        filters.append(Q(warehouse_root=warehouse)) 
                    else:
                        filters.append(Q(warehouse_root=warehouse,user=request.user))
                        
                q = reduce(operator.or_, filters) 

                invoices=invoices.filter(q)
                
            template_var['invoices']=invoices.distinct()
            
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum'] or 0
            template_var['invoices_chenben_money']=invoices.distinct().aggregate(sum=Sum('sale_price'))['sum'] or 0
            template_var['invoices_lirun']=(template_var['invoices_money'] or 0)-(template_var['invoices_chenben_money'] or 0)
            template_var['invoices_weijie']=invoices.filter(result=0).distinct().aggregate(sum=Sum('total_price'),count=Count('total_price'))
        else:
            template_var['invoices']=Invoice.objects.none() 
        
        template_var['form']=form  
        '''  

    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/xiaoshouchuku.html",template_var,context_instance=RequestContext(request))

'''
    新增
'''
#@anti_resubmit('xiaoshouchuku_add')
@transaction.commit_manually
def xiaoshouchuku_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*15
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    #权限判断 
    if not request.user.has_org_perm(org,'depot.xiaoshouchuku_add'):
        transaction.rollback()
        return HttpResponse("你没有权限")

    invoice=None
    extra=1
    template_var['pay_details']=pay_details=[None,]
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
        try:
            template_var['pay_details']=pay_details=PayInvoice.objects.get(invoice_from=invoice).payinvoicedetail_set.all()
        except:
            template_var['pay_details']=pay_details=[None,]
        
        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=2002)
    template_var['accounts']=accounts=BankAccount.objects.filter(org=org,status=0)


    
    if request.method=="GET":

        template_var['form']=InvoiceForm(instance=invoice)
        
        try:
            if invoice.status == 2:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums+_detail.num,'') for _detail in invoice.details.all()] or [NONE_ROW])

            else:
                template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])
        except:
            template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,_detail.good.code,
                                               _detail.good.remark,_detail.num,_detail.good.standard,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.price,_detail.pk,'','',_detail.good.nums,'') for _detail in invoice.details.all()] or [NONE_ROW])

    else:
        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
                
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 1 or i) for i in [0,2,5,9] if (not detail[i] or (i!=2 and detail[i]<0))]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            #if detail[7]:
                                #exists_key.append(detail[7])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
                    
            if form.is_valid() and details_data and not details_data_error_count:
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                invoice.status = 1
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_org_next_invoice_code(org)
                invoice.total_price=0
                invoice.save()
                
                if invoice_id:
                    #先清除没有的
                    #all_key=list(invoice.details.values_list('id',flat=True))
                    #delete_key=set(all_key)-set(exists_key)
                    #invoice.details.filter(id__in=list(delete_key)).delete()
                    last_invoice=Invoice.objects.get(pk=invoice_id)
                    last_invoice.details.all().delete()

    
                total_price=0
                chenben_price=0
            
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[7] and (dd[7]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[7])[0]) or None

                        before_change_num = good.nums
                        

                        num=good.change_nums(dd[5],unit)

                        
                        '''if dd[7]:
                            detail=InvoiceDetail.objects.get(pk=dd[7])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=invoice.warehouse_root
                            detail.num1=dd[3]
                            detail.unit1=unit
                            detail.price=dd[5]
                            detail.total_price=dd[3]*dd[5]
                            detail.num=num
                            detail.last_nums=num
                        else:'''
                        detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                warehouse_root=invoice.warehouse_root,warehouse=invoice.warehouse_root,
                                num1=dd[5],unit1=unit,price=dd[9],total_price=dd[5]*dd[9],
                                num=num,last_nums=num,num_at_that_time=before_change_num
                            )
                        
                        #不知道这个chengben_price怎么来的，用预估成本做单据成本
                        #detail.chenben_price=good.chengben_price*num
                        detail.chenben_price=good.price_ori*num
                    
                        '''
                        批次计算
                        if dd[2]:
                            
                            details=InvoiceDetail.objects.filter(invoice__status=2,batch_code=dd[2])
                            if details:
                                DetailRelBatch.objects.get_or_create(from_batch=detail,to_batch=details[0],level=True)
                                detail.chenben_price=InvoiceDetail.objects.get(good=good,batch_code=dd[2]).avg_price*num
                        '''    
                            
                        if unit and unit.good:
                            unit.sale_price=dd[9]
                            unit.save()
                        else:
                            good.sale_price=dd[9]
                            good.save()
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                        
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price
                        
                    except:
                        print traceback.print_exc()
                        continue
                
                
                invoice.total_price=total_price
                
                invoice.sale_price=chenben_price
                invoice.save()
            
                
          
                
                

                #生成收款单
                if request.POST.get('pay'):

                    if request.POST.get('date') == '':
                        pay_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
                    else:
                        pay_date = request.POST.get('date')

                    if request.POST.get('pay_id'):

                        pay_invoice = PayInvoice.objects.get(pk=request.POST.get('pay_id'))
                        pay_invoice.payinvoicedetail_set.all().delete()
                        pay_invoice.content_object=form.cleaned_data['rels']
                        pay_invoice.invoice_type=3001
                        pay_invoice.already_pay = 0
                        pay_invoice.rest_pay = pay_invoice.total_pay
                        pay_invoice.save()
                        already_pay = request.POST.get('pay')

                        try:
                            already_pay = float(already_pay)
                        except:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额填寫不正確'
                            return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))
                        if already_pay == 0:
                            pass
                        elif abs(already_pay - invoice.total_price) < 0.0000001:
                            #权限判断
                            if not request.user.has_org_perm(org,'depot.shoukuandan_modify'):
                                template_var['error_title'] = '你没有权限新增收款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=pay_date)
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay
                            if abs(already_pay - invoice.total_price) < 0.0000001:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save() 
                            pay_invoice.save()

                        elif already_pay > invoice.total_price:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额超过应付金额'
                            return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))


                    else:
                        pay_invoice = PayInvoice.objects.create(org=org,invoice_code=PayInvoice.get_next_invoice_code(),charger=invoice.charger,user=invoice.user,total_pay=invoice.total_price,warehouse_root=invoice.warehouse_root,event_date=request.POST.get('event_date'),invoice_from=invoice,content_object=form.cleaned_data['rels'],invoice_type=3001)
                        already_pay = request.POST.get('pay')
                        pay_invoice.save()
                        try:
                            already_pay = float(already_pay)
                        except:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额填寫不正確'
                            return render_to_response("main/xiaoshouchuku_add.html",template_var,context_instance=RequestContext(request))
                        if already_pay == 0:
                            pass
                            
                        elif abs(already_pay - invoice.total_price) < 0.0000001:
                            #权限判断
                            if not request.user.has_org_perm(org,'depot.shoukuandan_add'):
                                pay_invoice.delete()
                                template_var['error_title'] = '你没有权限新增收款单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
                            account = BankAccount.objects.get(pk=request.POST.get('account'))
                            PayInvoiceDetail.objects.create(invoice=pay_invoice,account=account,pay=request.POST.get('pay'),pay_type=request.POST.get('pay_type'),remark=request.POST.get('detail_remark'),org=org,event_date=pay_date)
                            pay_invoice.already_pay = already_pay
                            pay_invoice.rest_pay = pay_invoice.total_pay - already_pay
                            if abs(already_pay - invoice.total_price) < 0.0000001:
                                pay_invoice.result = True
                                invoice.result = True
                                invoice.save()
                            pay_invoice.save()

                        elif already_pay > invoice.total_price:
                            pay_invoice.delete()
                            invoice.delete()
                            template_var['error_msg'] = '收款金额超过应付金额'
                            return render_to_response("main/xiaoshouchuku_add.html",template_var,context_instance=RequestContext(request))
                
                auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_xiaoshouchuku


                        
                    
                if auto_confirm and request.user.has_org_perm(org,'depot.xiaoshouchuku_confirm'):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')

                        invoice.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        invoice.save()
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')


                transaction.commit()

                if request.is_ajax():

                    return HttpResponse(simplejson.dumps({'action':'goon','url':reverse('xiaoshouchuku',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
    
                
            else:
                if request.is_ajax():
                   
                    form_error_dict={}
                    
                    if form.errors:
                        for error in form.errors:
                            e=form.errors[error]
                            form_error_dict[error]=unicode(e)
                   
               
                    transaction.rollback()
                    
                    return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
                    
            template_var['form']=form
        
        except:
            print traceback.print_exc()

    response=render_to_response("main/xiaoshouchuku_add.html",template_var,context_instance=RequestContext(request))
    transaction.commit()
    return response

'''
    仓库盘点,如果有多个仓库，列出可选的，如果只有一个，则直接进入
'''
def pandian(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if not request.user.has_org_perm(org,'depot.pandian_add'):
                                template_var['error_title'] = '你没有权限新增盘点单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    
    warehouses=request.user.get_warehouses(org,['warehouse_write'])
    if warehouses.count()==1:
        return HttpResponseRedirect(reverse('cangkupandian',args=[org.pk,warehouses[0].pk]))
    
    template_var['warehouses']=warehouses
    return render_to_response("main/pandian.html",template_var,context_instance=RequestContext(request))


'''
    即时库存,如果有多个仓库，列出可选的，如果只有一个，则直接进入
'''
def jishikucun(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    
    request.session['org_id']=org.pk
    request.session['org']=org
    #warehouses=request.user.get_warehouses(org,['warehouse_pandian_read','warehouse_pandian_write','warehouse_manage'])
    warehouses=request.user.get_warehouses(org)
    if warehouses.count()==1:
        return HttpResponseRedirect(reverse('jishikucun_view',args=[org.pk,warehouses[0].pk]))
    childcount=0
    goodscount=0
    amountcount=0
    for wh in warehouses:
        childcount+=wh.get_children().count()
        wv=wh.warehouse_value()
  
        goodscount+=wv[1]
        amountcount+=wv[0]
        
   
    template_var['wh_all']=[childcount,goodscount,amountcount]
    template_var['warehouses']=warehouses
    
    '''
     '加载一些全局数据
    '''
    warehouses=request.user.get_warehouses(org)
    benyue_date=datetime.date.today().replace(day=1)
    caigou_invoices=Invoice.objects.filter(org=org,invoice_type=1001,status=2,warehouse_root__in=warehouses)
    xiaoshou_invoices=Invoice.objects.filter(org=org,invoice_type=2002,status=2,warehouse_root__in=warehouses)
    
    '''
    '仓库数据
    '''
    childcount=0
    goodscount=0
    amountcount=0
    for wh in warehouses:
        childcount+=wh.get_children().count()
        wv=wh.warehouse_value()
    
        goodscount+=wv[1]
        amountcount+=wv[0]
    
    
    template_var['wh_all']=[childcount,goodscount,amountcount]
    
    
    '''
    '未结单据数据
    '''
    weijie_caigou=caigou_invoices.filter(result=0)
    weijie_xiaoshou=xiaoshou_invoices.filter(result=0)
    template_var['weijie']={'caigou':weijie_caigou.count(),'xiaoshou':weijie_xiaoshou.count()}
    
    '''
    '本月单据数据
    '''
    benyue_caigou_invoices=caigou_invoices.filter(event_date__gte=benyue_date)
    benyue_xiaoshou_invoices=xiaoshou_invoices.filter(event_date__gte=benyue_date)
    template_var['benyue']={'caigou':benyue_caigou_invoices.aggregate(sum=Sum('total_price'))['sum'],'xiaoshou':benyue_xiaoshou_invoices.aggregate(sum=Sum('total_price'))['sum']}
    
    '''
    '物品警告
    '''
    template_var['min_warning']=Goods.objects.filter(org=org,min_warning__gte=0).filter(min_warning__gte=F('nums'))
    try:
        org.profile
    except:
        OrgProfile.objects.get_or_create(org=org)
    warn_day=org.profile.warn_day
    today=datetime.datetime.now()
    life_warnings=[]
    life_serious=[]
    batch_avail=InvoiceDetail.objects.select_related('good').filter(invoice__org=org,invoice__status=2,invoice__invoice_type=1001,last_nums__gt=0,good__is_batchs=1)
    for batch in batch_avail:
        
        day=batch.good.warning_day or warn_day
        if day>0 and batch.end_shelf_life:#如果该批次输入了过期时间
            if rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()==0:
                life_serious.append(batch)
            elif rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()<day:
                life_warnings.append(batch)
               
    template_var['life_warnings']=life_warnings
    template_var['life_serious']=life_serious
    
    '''
    '公告
    '''
    template_var['announces']=Announce.objects.filter(Q(org=org)|Q(org__isnull=True),expired_date__gte=datetime.date.today(),status=1).select_related('org')


    return render_to_response("main/jishikucun.html",template_var,context_instance=RequestContext(request))

'''
    查看仓库的物品列表
'''
def jishikucun_view(request,org_id,warehouse_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    if warehouse_id:
        template_var['warehouse']=Warehouse.objects.get(pk=warehouse_id)
        template_var['can_write']=request.user.has_org_warehouse_perm(warehouse_id,['depot.warehouse_write'])
        
        template_var['warehouses']=Warehouse.objects.filter(pk=warehouse_id)
    else:
        template_var['warehouses']=request.user.get_warehouses(org)
        
    
    return render_to_response("main/jishikucun_view.html",template_var,context_instance=RequestContext(request))

'''
    查看某个物品的列表
'''

@page_template('main/goods_detail_invoice_index.html')
def goods_detail(request,org_id,goods_id,warehouse_id=None,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['goods']=goods=Goods.objects.get(pk=goods_id)
    
    
    if warehouse_id:
        template_var['invoice_details']=invoice_details=InvoiceDetail.objects.filter(invoice__warehouse_root_id=warehouse_id,good=goods,invoice__status=2)
       
        template_var['invoices']=Invoice.objects.exclude(invoice_type=10000).filter(details__good=goods,warehouse_root_id=warehouse_id,status=2).distinct().extra(select={
                                'goods_sum':'SELECT SUM(num) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id,
                                'goods_price':'SELECT MAX(price) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id
                            })
       
    else:
        warehouses=request.user.get_warehouses(org,['pandian','warehouse_manage'])
        template_var['invoice_details']=invoice_details=InvoiceDetail.objects.filter(invoice__warehouse_root__in=warehouses,good=goods,invoice__status=2)
        template_var['invoices']=Invoice.objects.exclude(invoice_type=10000).filter(details__good=goods,warehouse_root__in=warehouses,status=2).distinct().extra(select={
                                'goods_sum':'SELECT SUM(num) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id,
                                'goods_price':'SELECT MAX(price) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id
                            })
    tmp=invoice_details.filter(invoice__invoice_type__in=IN_BASE_TYPE,invoice__status=2)
    #最大最小值
    price_tmp=tmp.filter(price__gt=0).order_by('avg_price')
    template_var['min_price']=price_tmp.exists() and price_tmp[0] or None
    template_var['max_price']=price_tmp.exists() and price_tmp[price_tmp.count()-1] or None
    
    template_var['batches']=invoice_details_jinhuo=tmp.filter(~Q(last_nums=0)).order_by('warehouse_root')    
    in_base_type_sum=invoice_details_jinhuo.aggregate(sum=Sum('last_nums'))['sum']

    pankui_invoices = invoice_details.filter(invoice__invoice_type=9001,invoice__status=2)
    pankui_sum = pankui_invoices.aggregate(sum=Sum('num'))['sum'] or 0
    template_var['sum'] = in_base_type_sum - pankui_sum
    
    if extra_context is not None:
        template_var.update(extra_context)
            
    return render_to_response("main/goods_detail.html",template_var,context_instance=RequestContext(request))


'''
    列出盘盈盘亏单表
'''

@page_template('main/panyinpankui_index.html')
def panyinpankui(request,org_id,template="main/panyinpankui.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoiceSelectSimpleForm=make_InvoiceSelectSimpleForm(org,request.user)
    
    if request.method=="GET":
        if request.GET:
            form=invoiceSelectSimpleForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s&warehouse=&status=10"%(reverse('panyinpankui',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
            #form=invoiceSelectSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
            #                              'warehouse':None,'status':10})
        
       
        if form.is_valid():
            
            invoices=Invoice.objects.filter(org=org,invoice_type=9999,event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'])
            
            if not form.cleaned_data['status']==10:
                invoices=invoices.filter(status=form.cleaned_data['status'])
                
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write','depot.warehouse_manage')):
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'])
                else:
                    invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse'],user=request.user)
            else:
                filters = [] 
                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write','depot.warehouse_manage')):
                        filters.append(Q(warehouse_root=warehouse)) 
                    else:
                        filters.append(Q(warehouse_root=warehouse,user=request.user))
                        
                q = reduce(operator.or_, filters) 
                invoices=invoices.filter(q)

                
            template_var['invoices']=invoices.distinct()
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            template_var['invoices_weijie']=invoices.filter(result=0).distinct().aggregate(sum=Sum('total_price'),count=Count('total_price'))
        else:
            template_var['invoices']=Invoice.objects.none()            
        template_var['form']=form

        if extra_context is not None:
            template_var.update(extra_context)
    return render_to_response(template,template_var,context_instance=RequestContext(request))


'''
    列出盘点单的列表
'''
@page_template('main/pandian_list_index.html')
def pandian_view(request,org_id,template="main/pandian_list.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if not (request.user.has_org_perm(org,'depot.pandian_modify') or request.user.has_org_perm(org,'depot.pandian_add') or request.user.has_org_perm(org,'depot.pandian_query')):
                                template_var['error_title'] = '你没有权限修改盘点单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    
    snapshotWarehouses = SnapshotWarehouse.objects.filter(org=org,is_delete=False)



        
    SnapshotWarehouse.objects.filter(org=org,status=0).delete()


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    confirm_user = request.GET.get('confirm_user')
    status = request.GET.get('status')
    invoice_code = request.GET.get('invoice_code')

    if startdate:
        snapshotWarehouses = snapshotWarehouses.filter(created_time__gte=startdate)
    if enddate:
        snapshotWarehouses = snapshotWarehouses.filter(created_time__lte=enddate)
    if charger:
        snapshotWarehouses = snapshotWarehouses.filter(created_user__username__icontains=charger)
    if confirm_user:
        snapshotWarehouses = snapshotWarehouses.filter(confirm_user__username__icontains=confirm_user)
    if status:
        snapshotWarehouses = snapshotWarehouses.filter(status=status)
    if invoice_code:
        snapshotWarehouses = snapshotWarehouses.filter(pk=invoice_code)

    template_var['snapshotWarehouses'] = snapshotWarehouses


    
    '''
    invoiceSelectSimpleForm=make_InvoiceSelectSimpleForm(org,request.user)
    
    if request.method=="GET":
        if request.GET:
            form=invoiceSelectSimpleForm(request.GET.copy())
        else:
            form=invoiceSelectSimpleForm({'date_from':datetime.date.today().replace(day=1),'date_to':datetime.date.today(),
                                          'warehouse':None,'status':10})
        
        #删除标记为已删除的盘点单
        SnapshotWarehouse.objects.filter(org=org,status=0).delete()
        
        if form.is_valid():
            
            snapshotWarehouses=SnapshotWarehouse.objects.filter(org=org,status__gte=1,created_time__gte=form.cleaned_data['date_from'],created_time__lte=form.cleaned_data['date_to']).order_by('-created_time','-id')
            if not form.cleaned_data['status']==10:
                snapshotWarehouses=snapshotWarehouses.filter(status=form.cleaned_data['status'])    
       
                            
                
            warehouses=request.user.get_warehouses(org)
            if form.cleaned_data['warehouse']:
                if request.user.has_org_warehouse_perm(form.cleaned_data['warehouse'].pk,('depot.warehouse_write',)):
                    snapshotWarehouses=snapshotWarehouses.filter(warehouse=form.cleaned_data['warehouse'])
                else:
                    snapshotWarehouses=snapshotWarehouses.filter(warehouse=form.cleaned_data['warehouse'],created_user=request.user)
            else:
                filters = [] 
                for warehouse in warehouses:
                    if request.user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write')):
                        filters.append(Q(warehouse=warehouse)) 
                    else:
                        filters.append(Q(warehouse=warehouse,created_user=request.user))
                
                if filters:        
                    q = reduce(operator.or_, filters) 
                    snapshotWarehouses=snapshotWarehouses.filter(q)
                
            template_var['snapshotWarehouses']=snapshotWarehouses.distinct()
            
        else:
            template_var['snapshotWarehouses']=SnapshotWarehouse.objects.none()            
        template_var['form']=form
    '''

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response(template,template_var,context_instance=RequestContext(request))

'''
'    进入准备生成盘点数据
'''
def cangkupandian(request,org_id,warehouse_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['warehouse']=Warehouse.objects.get(pk=warehouse_id)
    
    return render_to_response("main/cangkupandian.html",template_var,context_instance=RequestContext(request))

'''
'    生成仓库盘点数据excel
'''
def download_goods_pandian_table(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        keyword=request.GET.get('keyword','')
        warehouse_id=request.GET.get('warehouse_id',None)
        category_id=request.GET.get('category_id','')
        categorys=Category.objects.filter(id__in=category_id.split(','))
        
        warehouse=warehouse_id and Warehouse.objects.get(pk=warehouse_id) or None
        
        #goods=Goods.objects.all().select_related('unit')
        #只导出汇总管理的物品，分批的不导出
        goods=Goods.objects.filter(category__in=categorys,is_batchs=0).select_related('unit')
                    
        if keyword:
            goods=goods.filter(
                            Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
        else:
            goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
            
        
        if not goods:
            return HttpResponseBadRequest(_(u'没有找到物品供盘点'))
                
        #
        wb=_Wookbook()
        ws=wb.add_sheet(u'%s'%org.org_name)       
        
        ws.col(0).width=4000
        #wcs.col(0).width=4000
        font=Font()
        font.name="Arial"
        font.bold=True
        font.shadow=True
        font.height=300
        style=XFStyle()
        style.font=font
        
        font2=Font()
        font2.name="Arial"
        font2.bold=True
        font2.shadow=True
        style2=XFStyle()
        style2.font=font2
        
        ws.write_merge(0,0,0,50,_(u'盘点'),style)
        #wcs.write_merge(0,0,0,50,u'%s%s检测分表'%(paper.name,cclass.classes_name),style)
        
        i=0        
                
        i=i+1
        ws.write(i,0,_(u'编号'),style2)
        ws.write(i,1,_(u'名称'),style2)
        ws.write(i,2,_(u'编码'),style2)
        ws.write(i,3,_(u'类别'),style2)
        ws.write(i,4,_(u'规格'),style2)
        ws.write(i,5,_(u'单位'),style2)
        ws.write(i,6,_(u'库存数量'),style2)
        ws.write(i,7,_(u'盘点数量'),style2)
        #ws.write(i,8,_(u'备注'),style2)

        
        i=i+1

        for good in goods:
            ws.write(i,0,unicode(good.pk),style2)
            ws.write(i,1,unicode(good.name),style2)
            ws.write(i,2,unicode(good.code),style2)
            ws.write(i,3,unicode(good.category),style2)
            ws.write(i,4,unicode(good.standard),style2)
            if good.unit:
                ws.write(i,5,unicode(good.unit),style2)
            ws.write(i,6,good.sum,style2)            
            ws.write(i,7,'',style2)#不输入盘点数量
            #ws.write(i,8,'',style2)
                                       
            
            i=i+1
         

               
        #datetime.date.today().strftime('%Y-%m-%d')
        response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
        fname=(u"%s_%s"%(_(u'盘点'),datetime.date.today().strftime('%Y-%m-%d'))).encode('gbk')
        #print '11111','attachment; filename=\"%s.xls\"'% fname
        response['Content-Disposition'] = 'attachment; filename=\"%s.xls\"'% fname

        return response
    except:
        print traceback.print_exc()
        
        
        
#导入盘点单
def upload_goods_pandian_table(request,org_id):
    try:
        org=Organization.objects.get(slug=org_id)
    except:
        org=Organization.objects.get(pk=org_id) 
    warehouse_id=request.REQUEST.get('warehouse_id')
    warehouse=Warehouse.objects.get(pk=warehouse_id)
    #file=u'c:\\users\\huang\\Desktop\\物料信息表.xls'
    try:
        upfile=request.FILES['upfile']
        file="%s/%s"%(TMP_DIR,upfile.name)
        if os.path.exists(file):
            os.remove(file)
            
        handle_uploaded_file(TMP_DIR,upfile,None)
    
        sheets=parse_xls(file)
        sheet=sheets[0]
        #if sheet[0]!=_(u'物品列表'):
            #return HttpResponse(_(u'表格式有误'))
    except:
        print traceback.print_exc()
        return HttpResponse(_(u'读取文件格式错误'))
    
    msg=[]
    def process():
        info=""
        rows,cols=max(sheet[1].keys())
        i=1
        goods_list=[]
        goodid_list=[]

        while i<rows:
            i+=1
            j=0
            try:
                
                goodid=int(sheet[1][(i,0)])  #物品ID
                
                j=7
                #是否输入了盘点数量
                isinput=0
                try:
                    goodnum=float(sheet[1][(i,7)])  #物品库存
                    isinput=1
                except:
                    pass
                #j=8
                ramark=''
                #ramark=sheet[1].has_key((i,8)) and sheet[1][(i,8)] or '', #备注
                goods_list.append([goodid,goodnum,ramark,isinput])
                goodid_list.append(goodid)

            except:
                print traceback.print_exc()
                try:
                    msg.append(u'%s第%s行第%s列错误'%((sheet[1].has_key((i,1)) and sheet[1][(i,1)] or ''),i,j))
                except:
                    print traceback.print_exc()
                continue
        
        #将所有的物品录入
        succeesd=0
        goods=Goods.objects.filter(pk__in=goodid_list).select_related('unit')           
        goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
            

        if not goods:
            return HttpResponseBadRequest(_(u'没有找到物品供盘点'))
        details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,
                                          invoice__warehouse_root_id=warehouse_id,invoice__status=2).order_by('-last_nums')) for good in goods]
       
        goods_details=zip(goods,details)
        
        '''
        '    将获取的数据存入盘点历史表
        '''
        snapshotWarehouse=SnapshotWarehouse.objects.create(warehouse=warehouse,created_user=request.user,org=org,shelf=warehouse)
        
        for good,details in goods_details:
            #print '---',unicode(good.name)
            good_cur_num=good.sum
            #good_remark=''
            good_pancha=0
            #找到上传的数量
            isfind=False
            for goodtmp in goods_list:
                if good.pk == goodtmp[0]:
                    #如果输入了盘点数量
                    if goodtmp[3]:
                        good_cur_num=goodtmp[1]
                    #good_remark=goodtmp[2]
                    good_pancha=good_cur_num-good.sum
                    isfind=True
                    
            if not isfind:
                continue
            snapshotWarehouseGood=SnapshotWarehouseGood.objects.create(snapshotWarehouse=snapshotWarehouse,good=good,
                                    code=good.code,name=good.name,category_name=good.category.name,standard=good.standard,
                                    unit=good.unit,last_nums=good.sum,total_price=0,abbreviation=good.abbreviation,
                                    refer_price=good.refer_price,add_nums=good.add_nums,is_batchs=good.is_batchs,
                                    shiji=good_cur_num,pancha=good_pancha)
            
            for detail in details:
                
                SnapshotWarehouseDetail.objects.create(snapshotWarehouseGood=snapshotWarehouseGood,good=good,batch_code=detail.batch_code,price=detail.price,
                                                       total_price=detail.total_price,num1=detail.num1,unit1=detail.unit1,unit=detail.good.unit,last_nums=detail.last_nums,
                                                       warehouse=detail.warehouse,shiji=good_cur_num,pancha=good_pancha,detail_id=detail.id)
            succeesd+=1
                   
        
        snapshotWarehouse.status=1
        snapshotWarehouse.save()
        msg.append(u'已处理%s个物品'%succeesd)               
        return "%s"%("\n".join(msg))
            
    try:
        response=process()
        
    except:
        print traceback.print_exc()
    return HttpResponse(response)
'''
'    生成仓库盘点数据
'''
def create_goods_pandian_table(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        keyword=request.GET.get('keyword','')
       
        warehouse_id=request.GET.get('warehouse_id',None)
        category_id=request.GET.get('category_id','')
        categorys=Category.objects.filter(id__in=category_id.split(','))
        warehouse=warehouse_id and Warehouse.objects.get(pk=warehouse_id) or None
        
        shelf_id=request.GET.get('shelf_id',0)
        shelf=Warehouse.objects.get(pk=shelf_id)
        
        #goods=Goods.objects.all().select_related('unit')
        goods=Goods.objects.filter(category__in=categorys).select_related('unit')

        
        if warehouse_id==shelf_id:
            print "equal"
            '''
            ' 如果是仓库，则列出所有该货架下的东西
            '''
            if keyword:
                goods=goods.filter(
                                Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s '%(IN_BASE_TYPE_STR,warehouse_id),when=True))
            else:
                goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s '%(IN_BASE_TYPE_STR,warehouse_id),when=True))

        else:
            '''
            ’ 如果是假货，仅列出货架的东西
            '''
            if keyword:
                goods=goods.filter(
                                Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword)).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_invoicedetail.warehouse_id in (%s) '%(IN_BASE_TYPE_STR,warehouse_id,shelf_id),when=True))
            else:
                goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s and depot_invoicedetail.warehouse_id in (%s) '%(IN_BASE_TYPE_STR,warehouse_id,shelf_id),when=True))
  
        
        if not goods:
            return HttpResponseBadRequest(_(u'没有找到物品供盘点'))
        
        
        if shelf_id:
            details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,warehouse__in=shelf.get_descendants(include_self=True),
                                          invoice__warehouse_root_id=warehouse_id,invoice__status=2,status=1).order_by('-last_nums')) for good in goods]
        else:
            details=[list(good.details.filter(invoice__invoice_type__in=IN_BASE_TYPE,
                                          invoice__warehouse_root_id=warehouse_id,invoice__status=2,status=1).order_by('-last_nums')) for good in goods]
       
        template_var['goods_details']=goods_details=zip(goods,details)
        
        '''
        '    将获取的数据存入盘点历史表
        '''
        snapshotWarehouse=SnapshotWarehouse.objects.create(warehouse=warehouse,created_user=request.user,org=org,shelf=shelf)
        for good,details in goods_details:
            snapshotWarehouseGood=SnapshotWarehouseGood.objects.create(snapshotWarehouse=snapshotWarehouse,good=good,
                                    code=good.code,name=good.name,category_name=good.category.name,standard=good.standard,
                                    unit=good.unit,last_nums=good.nums,total_price=0,abbreviation=good.abbreviation,
                                    refer_price=good.refer_price,add_nums=good.add_nums,is_batchs=good.is_batchs)
            for detail in details:
                SnapshotWarehouseDetail.objects.create(snapshotWarehouseGood=snapshotWarehouseGood,detail_id=detail.pk,good=good,batch_code=detail.batch_code,price=detail.price,
                                                       total_price=detail.total_price,num1=detail.num1,unit1=detail.unit1,unit=detail.good.unit,last_nums=detail.last_nums,
                                                       warehouse=detail.warehouse)
    
        return HttpResponseRedirect("%s?edit=%s"%(reverse('list_goods_pandian_preview',args=[org_id,snapshotWarehouse.pk]),request.GET.get('edit','')))
    except:
        print traceback.print_exc()

'''
    列出仓库盘点表预览
'''
@page_template('main/list_goods_pandian_index.html')
def list_goods_pandian_preview(request,org_id,snap_id,template='main/list_goods_pandian_preview.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['edit']=request.GET.get('edit','')
    template_var['snapshotWarehouse']=snapshotWarehouse=SnapshotWarehouse.objects.get(pk=snap_id)
    template_var['warehouse']=warehouse=snapshotWarehouse.warehouse
    
    goods=[]    
    batchs=SnapshotWarehouseDetail.objects.filter(snapshotWarehouseGood__snapshotWarehouse=snapshotWarehouse)
    
    b_goods=SnapshotWarehouseGood.objects.filter(snapshotWarehouse=snapshotWarehouse).values('total_price','is_batchs','good_id','name','unit__unit',
                                                    'code','last_nums','abbreviation','standard','category_name','refer_price','shiji','pancha')

    good_name = request.GET.get('good_name')
    if good_name:
        b_goods=b_goods.filter(name__icontains=good_name)
        
    template_var['b_goods_count']=len(b_goods)    
    template_var['b_goods']=b_goods=[[b_g,batchs.filter(good_id=b_g['good_id'])] for b_g in b_goods]
        
    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response(template,template_var,context_instance=RequestContext(request))

'''
    打印盘点单
'''
def pandian_view_print(request,org_id,snap_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    template_var['snapshotWarehouse']=snapshotWarehouse=SnapshotWarehouse.objects.get(pk=snap_id)
    template_var['warehouse']=warehouse=snapshotWarehouse.warehouse
    
    goods=[]    
    batchs=SnapshotWarehouseDetail.objects.filter(snapshotWarehouseGood__snapshotWarehouse=snapshotWarehouse)
    
    b_goods=SnapshotWarehouseGood.objects.filter(snapshotWarehouse=snapshotWarehouse).values('total_price','is_batchs','good_id','name','unit__unit',
                                                    'code','last_nums','abbreviation','standard','category_name','refer_price','shiji','pancha')
        
    template_var['b_goods_count']=len(b_goods)    
    template_var['b_goods']=b_goods=[[b_g,batchs.filter(good_id=b_g['good_id'])] for b_g in b_goods]
         
    return render_to_response("main/pandian_view_print.html",template_var,context_instance=RequestContext(request))
'''
    同步盘点数据
'''
@transaction.commit_manually
def sync_good_count(request,org_id):      
    try:
        v=request.POST['v']
        #top_remark=request.POST['remark']
        snapshotWarehouse=SnapshotWarehouse.objects.get(pk=request.POST['snapshotWarehouse_id'])
        warehouse=Warehouse.objects.get(pk=request.POST['warehouse_id'])
        try:
            org=Organization.objects.get(slug=org_id)
        except:
            org=Organization.objects.get(pk=org_id)
        
        json_data=simplejson.loads(v)
 
        try:
            invoice=Invoice.objects.get(content_type=ContentType.objects.get_for_model(snapshotWarehouse),object_id=snapshotWarehouse.pk)
        except:
            invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),status=1,org=org,warehouse_root=warehouse,result=1,
                                            event_date=snapshotWarehouse.created_time,invoice_type=9999,content_object=snapshotWarehouse,charger=request.user,
                                            user=request.user,confirm_user=request.user,remark=None)
        
        for jd in json_data:
            
            good_id=jd['good_id']
            good=Goods.objects.get(pk=good_id)
            InvoiceDetail.objects.filter(invoice=invoice,good=good).delete()
            remark=jd.get('remark','')
            if jd['batchs']:
                for batch in jd['batchs']:
                    _pancha=float(batch['pancha'])
                    _batch_code=batch['batch_code']
                    _nums=float(batch['nums'])

                    if not _pancha:
                        continue
                    
                    try:
                        detail=InvoiceDetail.objects.filter(batch_code=_batch_code,invoice__status=2,invoice__invoice_type__in=IN_BASE_TYPE)[0]
                        rel_batch=True
                        num=good.change_nums(_pancha,detail.unit1)
                    except:
                        rel_batch=False
                        num=_pancha
                        
                    #detail=InvoiceDetail.objects.filter(batch_code=_batch_code,invoice__status=2,invoice__invoice_type__in=(1001,1000,1009))[0]
                    #num=good.change_nums(_pancha,detail.unit1)
                    if rel_batch:
                        #InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code="P_%s_%s_pd"%(invoice.pk,detail.pk),warehouse=detail.warehouse,warehouse_root=detail.warehouse_root,remark=_batch_code,
                        #                             status=-1,num1=_pancha,unit1=detail.good.unit,price=detail.avg_price,num=num,avg_price=detail.avg_price,last_nums=0,total_price=detail.avg_price*num)
                        InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code="P_%s_%s_pd"%(invoice.pk,detail.pk),warehouse=detail.warehouse,warehouse_root=detail.warehouse_root,remark=_batch_code,
                                                     num1=_pancha,unit1=detail.good.unit,price=detail.avg_price,num=num,avg_price=detail.avg_price,last_nums=num,total_price=detail.avg_price*num)
                    else:
                        InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code=InvoiceDetail.get_next_detail_code(),warehouse=snapshotWarehouse.shelf,warehouse_root=snapshotWarehouse.warehouse,
                                                     num1=_pancha,unit1=good.unit,price=good.refer_price,num=num,avg_price=good.refer_price,last_nums=num,total_price=good.refer_price*num)
                    
                    
                    sd=SnapshotWarehouseDetail.objects.get(snapshotWarehouseGood__snapshotWarehouse=snapshotWarehouse,batch_code=_batch_code)
                    sd.shiji=_nums
                    sd.pancha=_pancha
                    sd.save()
                    
            else:
                try:
                    _pancha=float(jd['pancha'])
                    _nums=float(jd['nums'])
                    if not _pancha:
                        continue
                except:
                    continue
                        
                InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=snapshotWarehouse.shelf,warehouse_root=warehouse,
                                                 num1=_pancha,unit1=good.unit,price=good.refer_price,num=_pancha,avg_price=good.refer_price,last_nums=_pancha,total_price=good.refer_price*_pancha,
                                                 remark=None)
                
                
                sd=SnapshotWarehouseGood.objects.get(snapshotWarehouse=snapshotWarehouse,good=good)
                sd.shiji=_nums
                sd.pancha=_pancha
                sd.save()
            
                
                
        invoice.total_price=invoice.details.all().aggregate(sum_total_price=Sum('total_price'))['sum_total_price'] or 0                
        invoice.save()
        

        #如果设定了自动审核盘点单，将自动审核
        #auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_pandian
        #if auto_confirm and request.user.has_org_perm(org,'depot.pandian_confirm'):
            #snapshotWarehouse.confirm(request.user)

        transaction.commit()

        return HttpResponse('%s'%warehouse.pk)
                
    except:
        transaction.rollback()
        print traceback.print_exc()
        
        
        
'''
    确认同步盘点数据
'''
@transaction.commit_manually
def confirm_pandian_dan(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    snapshotWarehouse=SnapshotWarehouse.objects.get(pk=invoice_id)

    if not request.user.has_org_perm(org,'depot.pandian_confirm'):
                                template_var['error_title'] = '你没有权限审核盘点单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    
    try:
        snapshotWarehouse.confirm(request.user)
                
        transaction.commit()        
        return HttpResponseRedirect(reverse("pandian_view",args=[org.uid]))
    
    except:
        transaction.rollback()
        print traceback.print_exc()
        
'''
    设置盘点单状态为1
'''
def set_pandian_dan(request,org_id):
    snapshotWarehouse=SnapshotWarehouse.objects.get(org=org_id,pk=request.POST['snapshotWarehouse_id'])
    try:
        snapshotWarehouse.status=1
        snapshotWarehouse.save()   
        return HttpResponse('%s'%snapshotWarehouse.pk)
    
    except:
        print traceback.print_exc()
        
'''
    删除盘点单条目
'''
@transaction.commit_manually
def del_snapshot_good(request,org_id):
    snapshotWarehouse=SnapshotWarehouse.objects.get(org=org_id,pk=request.POST['snapshotWarehouse_id'])
    
    try:
        good_id=request.POST['good_id']
        
        SnapshotWarehouseDetail.objects.filter(good_id=good_id,snapshotWarehouseGood__snapshotWarehouse=snapshotWarehouse).delete()
        SnapshotWarehouseGood.objects.filter(good_id=good_id,snapshotWarehouse=snapshotWarehouse).delete()
        #Invoice.objects.get(content_type=ContentType.objects.get_for_model(snapshotWarehouse),object_id=snapshotWarehouse.pk).delete()
                
        transaction.commit()        
        return HttpResponse('%s'%good_id)
    
    except:
        transaction.rollback()
        print traceback.print_exc()
        
'''
    撤销同步盘点数据
'''
@transaction.commit_manually
def cancel_pandian_dan(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    snapshotWarehouse=SnapshotWarehouse.objects.get(pk=invoice_id)

    if not request.user.has_org_perm(org,'depot.pandian_confirm'):
                                template_var['error_title'] = '你没有权限审核盘点单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    
    
    try:
        snapshotWarehouse.unconfirm()
        print 'unconfirm'
                
        transaction.commit()        
        return HttpResponseRedirect(reverse("pandian_view",args=[org.uid]))
    
    except:
        transaction.rollback()
        print traceback.print_exc()
   
'''
    删除盘点单
''' 
def delete_pandian_dan(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    if not request.user.has_org_perm(org,'depot.pandian_delete'):
                                template_var['error_title'] = '你没有权限删除盘点单'
                                return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    try:
        snapshotWarehouse=SnapshotWarehouse.objects.get(pk=invoice_id)
        
        if not snapshotWarehouse.status==2:
            snapshotWarehouse.is_delete = True
            snapshotWarehouse.save()
        return HttpResponseRedirect(reverse("pandian_view",args=[org.uid]))

    except:
        print traceback.print_exc()
    
    
'''
    查看物品警告
'''
def goods_warnings(request,org_id):
    try:
        
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        
        template_var['min_warning']=Goods.objects.filter(org=org,min_warning__gte=0).filter(min_warning__gte=F('nums'))
        template_var['max_warning']=Goods.objects.filter(org=org,max_warning__gte=0).filter(max_warning__lte=F('nums'))
        warn_day=org.profile.warn_day
        today=datetime.datetime.now()
        life_warnings=[]
        life_serious=[]
        
        
        batch_avail=InvoiceDetail.objects.select_related('good').filter(invoice__org=org,invoice__status=2,invoice__invoice_type=1001,last_nums__gt=0,good__is_batchs=1)
        for batch in batch_avail:
            
            day=batch.good.warning_day or warn_day
            if day>0 and batch.end_shelf_life:#如果该批次输入了过期时间
                if rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()==0:
                    life_serious.append(batch)
                elif rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()<day:
                    life_warnings.append(batch)
                   
        template_var['life_warnings']=life_warnings
        template_var['life_serious']=life_serious
    except:
        print traceback.print_exc()
    
    return render_to_response("main/goods_warnings.html",template_var,context_instance=RequestContext(request))
    


'''
    下载批量物品上传表
'''
def download_good_template(request):
    wb=_Wookbook()
    font=Font()
    font.name="Arial"
    font.bold=True
    font.shadow=True
    style=XFStyle()
    style.font=font
    
    heads=[_(u'物品名称【必填】'),_(u'物品编码'),_(u'物品分类【必填】'),_(u'上级分类'),_(u'单位'),_(u'助查码'),_(u'初始成本价格'),_(u'初始销售价格'),_(u'下限数量'),_(u'上限数量'),_(u'初始库存'),_(u'仓库')]
    ws=wb.add_sheet(_(u'物品列表'))
    j=0
    while j<len(heads):
        ws.write(0,j,heads[j],style)
        j+=1
        
    org_id = request.REQUEST.get('org_id',1)
    #下载的物品
    org=Organization.objects.get(pk=org_id)

    root_org=org.get_root_org()
    
    category_id=request.REQUEST.get('category_id',None)
    if category_id:
        category=Category.objects.get(pk=category_id)
    else:
        category=Category.objects.get(org=root_org,parent__isnull=True)
        
    categorys=category.get_descendants(include_self=True)
    goods=Goods.objects.filter(Q(category__in=categorys)|Q(category=category))
    
    
    keyword=request.GET.get('keyword','')
    if keyword:
        goods=goods.filter(Q(code__icontains=keyword)|Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)).filter(status=True,category__status=True)
    #如果带有仓库参数，则按仓库来
    warehouse_id=''
    if request.GET.has_key('warehouse_id'):
        warehouse_id=request.GET.get('warehouse_id','')
        if warehouse_id:
            goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouse_id),when=True))
                               
            #测试是否对该仓库有可写权限
            warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read','warehouse_mamage']).values_list('id',flat=True)
      
            
        else:
            warehouses=request.user.get_warehouses(org,['warehouse_write','warehouse_read','warehouse_mamage'])
            
            #goods=goods.filter(details__invoice__invoice_type__in=[1001,1000,1009],details__invoice__warehouse_root__in=warehouses,
            #                   details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
            
            if len(warehouses)==1:
                goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id=%s'%(IN_BASE_TYPE_STR,warehouses[0]),when=True))
            else:
                goods=goods.annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2 and depot_ininvoice.warehouse_root_id in %s'%(IN_BASE_TYPE_STR,tuple(warehouses)),when=True))
            
                               
            
    warehouse_obj=None
    if warehouse_id:
        warehouse_obj=Warehouse.objects.get(pk=warehouse_id)
    else:
        warehouse_objs=Warehouse.objects.filter(parent__isnull=True)
        if warehouse_objs:
            warehouse_obj=warehouse_objs[0]
            
    contains_data=request.GET.has_key('data')
    
    if not contains_data:
        heads=[_(u'示例物品'),_(u'00000001'),_(u'示例分类'),_(u'总分类'),_(u'单位1'),_(u'SLWP'),10,20,50,100,50,_(u'总仓')]
        j=0
        while j<len(heads):
            ws.write(1,j,heads[j],style)
            j+=1
    else:
        i=1#第1行
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
            
            if good.unit:
                ws.write(i,j,unicode(good.unit),style)
            j+=1
            ws.write(i,j,unicode(good.abbreviation),style)
            j+=1
            ws.write(i,j,(good.price),style)
            j+=1
            ws.write(i,j,(good.sale_price),style)
            j+=1
            ws.write(i,j,(good.min_warning),style)
            j+=1
            ws.write(i,j,(good.max_warning),style)
            j+=1
            ws.write(i,j,(good.nums),style)
            j+=1
            if warehouse_objs:
                ws.write(i,j,unicode(warehouse_obj.name),style)
            j+=1
            i+=1
    
    ws.col(0).width=0x1300
    ws.col(2).width=0x1300
    
    font1=Font()
    font1.height=180 
    font1.name="Arial"
    font1.shadow=True
    style1=XFStyle()
    style1.font=font1   
    ws=wb.add_sheet(_(u'说明'))
    ws.write(1,1,_(u'''从第二行开始解析，上级分类是物品分类的父分类,建议不要留空，都放在默认分类下'''),style1)
    ws.write(3,1,_(u'''助查码如果不填写，将由系统自动按拼音生成一个，有多音字的情况下可能会出现不匹配的问题'''),style1)
    ws.write(5,1,_(u'''如果在解析的过程中出现问题，将忽略错误继续进行'''),style1)
    ws.write(7,1,_(u'''其中物品名称，物品分类是必填项'''),style1)
    
    #ws.write(9,1,_(u'''分批管理：请填入0或1，0为汇总管理，1为批量管理，仅汇总管理的物品可以和收银系统完成自动出库'''),style1)
    #ws.write(10,1,_(u'''SN管理：请填入0或1，0为不适用SN，1为适用'''),style1)
    #ws.write(11,1,_(u'''ABC分类，填入A/B/C 为设定ABC类，其余为不分类'''),style1)
    
    ws.write(12,1,_(u'''仓库，填入仓库路径，有货架时使用'->'连接,如总仓下的一号货架，填写'总仓->一号货架' '''),style1)
    
        
    response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
    #response['Content-Disposition'] = u'attachment; filename=%s.xls'%(urlquote(u'物品信息表'))
    response['Content-Disposition'] = 'attachment; filename="%s.xls"'%(_(u'物品信息表').encode('gbk'))
    return response



'''
    解析上传的Excel
'''
@transaction.autocommit
def upload_good_template(request,org_id):
    try:
        org=Organization.objects.get(slug=org_id)
    except:
        org=Organization.objects.get(pk=org_id)
    #file=u'c:\\users\\huang\\Desktop\\物料信息表.xls'
    try:
        upfile=request.FILES['upfile']
        file="%s/%s"%(TMP_DIR,upfile.name)
        if os.path.exists(file):
            os.remove(file)
            
        handle_uploaded_file(TMP_DIR,upfile,None)
    
        sheets=parse_xls(file)
        sheet=sheets[0]
        if sheet[0]!=_(u'物品列表'):
            return HttpResponse(_(u'表格式有误'))
    except:
        print traceback.print_exc()
        return HttpResponse(_(u'读取文件格式错误'))
        
    ABC_DIC={'A':1,'B':2,'C':3}
    class _GoodHelp():
        def __init__(self,name,code,category,parent_category,unit,abbreviation,refer_price,sale_price,min_warning,max_warning,nums,warehouse_str):
            self.name=name
            self.code=code or ''
            self.category=category
            self.parent_category=parent_category 
            self.unit=unit and Unit.objects.get_or_create(org=org,unit=unit,good__isnull=True)[0] or None
            self.abbreviation=abbreviation
            self.refer_price=refer_price
            self.sale_price=sale_price
            self.min_warning=min_warning
            self.max_warning=max_warning
            self.nums=nums
            self.warehouse_str=warehouse_str
            self.price_ori=refer_price
            self.sale_price_ori=sale_price
            #self.profile=sale_price-refer_price
            #self.percent2=self.profile/sale_price
            
            if self.code:
                try:
                    self.code="%s"%self.code
                except:
                    pass
            
        def save(self,invoice):
            try:
                parent_category=self.parent_category or _(u'全部分类') 
                c=Category.objects.filter(org=org,name=u'%s'%self.category)
                if c.count()>1:
                    c=c.filter(parent__name=u'%s'%parent_category)
  
                if c.exists() and c.count()==1:
                    pass
                else:
                    print u'(%s)mult category or none,pass[%s,%s]'%(self.name,c.exists(),c.count())
                    msg.append(u'(%s)找到了%s个分类，忽略'%(self.name,c.count()))
                    return None,None
                
                #print 'xxxxxxxxxxxxxxxx',c[0],c[0].parent
                obj,created=Goods.objects.get_or_create(name=self.name,org=org,category=c[0],defaults={'code':self.code,
                                        'unit':self.unit,'abbreviation':self.abbreviation,'refer_price':self.refer_price,
                                        'price':self.refer_price,'sale_price':self.sale_price,
                                        'price_ori':self.refer_price,'sale_price_ori':self.sale_price,
                                        'min_warning':self.min_warning,'max_warning':self.max_warning,'last_modify_user':request.user,
                                        'nums':0,'add_nums':0,'profit':self.sale_price-self.refer_price,'percent2':(self.sale_price-self.refer_price)/self.sale_price*100})
                #更新已存在的信息
                if True:
                    if self.unit:
                        obj.unit=self.unit
                    if self.abbreviation:
                        obj.abbreviation=self.abbreviation
                    if self.refer_price:
                        obj.refer_price=self.refer_price
                        obj.price=self.refer_price
                    if self.min_warning:
                        obj.min_warning=self.min_warning
                    if self.max_warning:
                        obj.max_warning=self.max_warning
                        
                    #当切仅当没有其他类型的单据时，创建入库单,1000的单据为初始入库单
                    #仓库使用仓库->货架-》货架的形式 
                    
                    warehouse=Warehouse.get_warehouse_path(org,self.warehouse_str,request.session.get('sites',2))
  
                    if warehouse and self.nums:
                        invoice,created=Invoice.objects.get_or_create(pk=golbal_invoice_id,defaults={'org':org,'result':True,
                                            'invoice_code':(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(datetime.datetime.today(),'%Y%m%d'),'seq':golbal_invoice_id}).replace(' ','0'),
                                            'warehouse_root':warehouse.get_root(),'event_date':datetime.date.today(),
                                            'invoice_type':1000,'charger':request.user,'user':request.user,
                                            'confirm_user':request.user,'content_object':request.user})
                        
                        
                        invoiceDetail=InvoiceDetail.objects.create(invoice=invoice,good=obj,batch_code=InvoiceDetail.get_next_detail_code(),
                                                    warehouse=warehouse,warehouse_root=warehouse.get_root(),num1=self.nums,unit1=self.unit,
                                                    price=self.refer_price,avg_price=self.refer_price,num=self.nums,last_nums=self.nums,
                                                    total_price=self.nums*self.refer_price)
                        
                        invoice.total_price+=invoiceDetail.total_price
                        invoice.save()
                        
                        
                        
                    
                    #if self.remark:
                    #    obj.remark=self.remark
                    obj.status=1
                    obj.last_modify_user=request.user
                    obj.save()
                '''
                    只有初始导入的时候做一些动作
                '''

                return obj,invoice
            except:
                print traceback.print_exc()
                print u'except,pass'
                return None,None
    goods=[] 
    categorys={}
    child_categorys={}
    categorys_tree=tree()
    msg=[]
    ines=Invoice.objects.filter(org=org,id__lte=2000).order_by('-id')
    golbal_invoice_id=ines.exists() and (ines[0].pk+1) or 1000
    while True:
        try:
            Invoice.objects.get(pk=golbal_invoice_id)
            golbal_invoice_id+=1
        except:
            break
    invoice=None
            
    def process(invoice):
        info=""
        rows,cols=max(sheet[1].keys())
        i=0
        ws=set()
        while i<rows:
            i+=1
            j=0
            try:
                j+=1
                sheet[1][(i,0)],  #物品名称
                j+=1
                sheet[1].has_key((i,1)) and sheet[1][(i,1)] or None, #编码
                j+=1
                sheet[1][(i,2)],  #物品分类
                j+=1
                sheet[1].has_key((i,3)) and sheet[1][(i,3)] or None  #上级分类
                j+=1
                sheet[1].has_key((i,4)) and sheet[1][(i,4)] or None,  #单位
                j+=1
                sheet[1].has_key((i,5)) and sheet[1].has_key((i,5)) or get_abbreviation(sheet[1][(i,0)]) #goods_abbr
                j+=1
                sheet[1].has_key((i,6)) and float(sheet[1][(i,6)]) or 0   #goods_price
                j+=1
                sheet[1].has_key((i,7)) and float(sheet[1][(i,7)]) or 0   #sale_price
                j+=1
                sheet[1].has_key((i,8)) and float(sheet[1][(i,8)]) or -1 #goods_min_warning
                j+=1
                sheet[1].has_key((i,9)) and float(sheet[1][(i,9)]) or -1 #goods_max_warning
                j+=1
                
                sheet[1].has_key((i,10)) and float(sheet[1][(i,10)]) or 0   #初始库存
                j+=1
                w=(sheet[1].has_key((i,11)) and sheet[1][(i,11)] or None)   #初始库存

                if w:
                    ws.add(w.split('->')[0])
                    if len(ws)>1:
                        return HttpResponse(_(u'第%(i)s行第%(j)s列错误:一次只允许同一仓库的物品'%{'i':i,'j':j})),None
                    
                _good=_GoodHelp(
                    sheet[1][(i,0)],  #物品名称
                    sheet[1].has_key((i,1)) and sheet[1][(i,1)] or None, #编码
                    sheet[1][(i,2)],  #物品分类
                    sheet[1].has_key((i,3)) and sheet[1][(i,3)] or None,  #上级分类
                    sheet[1].has_key((i,4)) and sheet[1][(i,4)] or None,  #单位

                    sheet[1].has_key((i,5)) and sheet[1][(i,5)] or get_abbreviation(sheet[1][(i,0)]), #goods_abbr
                    sheet[1].has_key((i,6)) and float(sheet[1][(i,6)]) or 0,   #goods_price
                    sheet[1].has_key((i,7)) and float(sheet[1][(i,7)]) or 0,   #sale_price
                    sheet[1].has_key((i,8)) and float(sheet[1][(i,8)]) or -1, #goods_min_warning
                    sheet[1].has_key((i,9)) and float(sheet[1][(i,9)]) or -1, #goods_max_warning
                    
                    sheet[1].has_key((i,10)) and float(sheet[1][(i,10)]) or 0,   #初始库存
                    sheet[1].has_key((i,11)) and sheet[1][(i,11)] or None, #初始货架
                )
                
                
                #num=sheet[1].has_key((i,10)) and sheet[1][(i,10)] or 0
                '''
                    测试数量和货架填写是否正确
                '''
               
                    
                goods.append(_good)
                #log.debug(u'append good %s to good list'%_good.name)
                
                
                parent=sheet[1].has_key((i,3)) and sheet[1][(i,3)] or None
                parent=parent!=_(u'全部分类') and parent or None
                child=sheet[1][(i,2)]
                
                categorys.update({child:True})
                if parent:
                    categorys.update({parent:True})
                    child_categorys.update({child:True})
                    categorys_tree[parent][child]=True
                else:
                    pass
                    #categorys_tree[child]=True
            except:
                print traceback.print_exc()
                try:
                    msg.append(u'%s第%s行第%s列错误'%((sheet[1].has_key((i,1)) and sheet[1][(i,1)] or ''),i,j))
                except:
                    print traceback.print_exc()
                continue
       
        
        #根据目录结构建立分类     
  
        for key in child_categorys.keys():
            categorys.pop(key)
        import json
        from collections import defaultdict
        def print_key(key,parent_key): 
            '''
                                新建分类信息，如果有，则忽略
            '''
            parent_key=parent_key or _(u'全部分类')

                
            ps=Category.objects.filter(org=org,name=parent_key)
            if ps.count()==1:
                category,created=Category.objects.get_or_create(name=key,parent=ps[0],org=org,defaults={'user':request.user})
                if not created:
                    category.parent=ps[0]
                    category.save()
                    
            else:
                info=u"\n分类%s有多个，忽略"%(parent_key)
                msg.append(info)
         
            
            if type(categorys_tree[key])==defaultdict:
                for k in categorys_tree[key].keys():
                    print_key(k,key)
            
        for key in categorys.keys(): 
            print_key(key,_(u'全部分类'))
            
        #将所有的物品录入
        succeesd=0
        '''
        '    重新rebuild分类树
        '''
        Category.objects.partial_rebuild(Category.objects.filter(org=org_id)[0].tree_id)
        for good in goods:
            #log.debug(u'save good %s'%_good.name)
            try: 
                s,invoice=good.save(invoice)
            except:
                print traceback.print_exc()
            if s:
                succeesd+=1

        
        msg.append(u'已处理%s个物品'%succeesd)               
        return "%s"%("\n".join(msg)),invoice
            
    try:
        response,invoice=process(invoice)
        if invoice:
        
            invoice.confirm(request.user)
    except:
        print traceback.print_exc()
        
    try:
        stv,created=SyncTableVer.objects.get_or_create(org=org)
        stv.good_ver=int(time.time())
        stv.save()
    except:
        print traceback.print_exc()
        ids=list(SyncTableVer.objects.filter(org=org).order_by('-id').values_list('id',flat=True))[1:]
        SyncTableVer.objects.filter(id__in=ids).delete()
        SyncTableVer.objects.get_or_create(org=org,good_ver=int(time.time()))
    return HttpResponse(response)

'''
    设置结款状态为cancel
'''
def result_cancel(request,org_id):
    invoice_id=request.POST.get('invoice_id','0')
    try:
        org=Organization.objects.get(slug=org_id)
    except:
        org=Organization.objects.get(pk=org_id)
    
    invoice=Invoice.objects.get(org=org,pk=invoice_id)
    invoice.result=False
    invoice.save()
    
    return HttpResponse(invoice_id)

'''
    设置结款状态为ok
'''
def result_ok(request,org_id):
    invoice_id=request.POST.get('invoice_id','0')
    org=Organization.objects.get(pk=org_id)
    
    invoice=Invoice.objects.get(org=org,pk=invoice_id)
    invoice.result=True
    invoice.save()
    
    return HttpResponse(invoice_id)

'''
    增加直接显示物品的界面
'''
def goods(request,org_id):
    pass

'''
    打印单据模板
'''
def print_template(request,org_id,invoice_id,common_template_id):
    template_var={}
    try:
        org=Organization.objects.get(slug=org_id)
    except:
        org=Organization.objects.get(pk=org_id)

    common_template=CommonPrintTemplate.objects.get(pk=common_template_id)
    common_template_list=CommonPrintTemplate.objects.all()

    
    invoice=Invoice.objects.select_related().get(org=org,pk=invoice_id)

    print_template_list=PrintTemplate.objects.filter(org=org,common_template=common_template_id)

    now_time=datetime.datetime.now()

    template_var['common_template']=common_template
    template_var['common_template_list']=common_template_list
    template_var['print_template_list']=print_template_list
    template_var['invoice']=invoice
    template_var['now_time']=now_time
    template_var['org']=org
    
    #不同的通用模板return不同的html文件
    if int(common_template_id) == 1:
        return render_to_response('print_template/print_template.html',template_var,context_instance=RequestContext(request))
    else:
        return HttpResponse("通用模板不存在")


def save_print_template(request,org_id,common_template_id):
    template_name=request.POST.get('template_name')
    content=request.POST.get('content')
    template_type=request.POST.get('template_type')
    unit=request.POST.get('unit')

    PrintTemplate.objects.create(template_name=template_name,org_id=org_id,common_template_id=common_template_id,content=content,currency_unit=unit,print_template_type=template_type)
    
    return HttpResponse("保存模板成功!")

def get_print_template(request):
    template_id=request.POST.get('template_id')
    template=PrintTemplate.objects.get(pk=int(template_id))
    content=template.content
    unit=template.currency_unit
    data = {"unit":unit,"content":content,"invoice_type":template.print_template_type}
    return HttpResponse(simplejson.dumps(data))

def delete_print_template(request):
    template_id=request.POST.get('template_id')

    PrintTemplate.objects.get(pk=int(template_id)).delete()
    return HttpResponse("删除成功")

#采购申请单
@page_template('main/caigoushenqing_index.html')
def caigoushenqing_view(request,org_id,template="main/caigoushenqing.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['invoices']=invoices = Invoice.objects.filter(invoice_type=1004,org=org,is_delete=0)

    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    supplier = request.GET.get('supplier')
    invoice_code = request.GET.get('invoice_code')
    status = request.GET.get('status')
    remark = request.GET.get('remark')
    good_name = request.GET.get('good_name')
    category = request.GET.get('category')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if supplier:
        supplier = Supplier.objects.filter(name__icontains=supplier).values_list("id",flat=True)
        invoices = invoices.filter(object_id__in=supplier)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if status:
        invoices = invoices.filter(status=status)
    if remark:
        invoices = invoices.filter(remark__contains=remark)
    if good_name:
        invoices = invoices.filter(details__good__name__icontains=good_name)
    if category:
        invoices = invoices.filter(details__good__category__name__icontains=category)

    template_var['invoices'] = invoices
        
    unconfirmed_invoice = invoices.filter(Q(status=0)|Q(status=1))
    template_var['unconfirmed_invoice'] =unconfirmed_invoice.count()
    template_var['unconfirmed_price']=unconfirmed_invoice.aggregate(Sum('total_price'))

    if extra_context is not None:
            template_var.update(extra_context)

    
    return render_to_response(template,template_var,context_instance=RequestContext(request))

    




#@transaction.commit_manually
#@anti_resubmit('caigoushenqing_add')
def caigoushenqing_add(request,org_id,invoice_id=None):
    template_var={}
    NONE_ROW=[None]*12
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    invoice=None
    extra=1
    if invoice_id:
        template_var['invoice']=invoice=Invoice.objects.get(pk=invoice_id)
        
        
    InvoiceForm=make_InvoiceForm(org,request.user,invoice_type=1004)
    
    if request.method=="GET":

        #权限判断
        if not request.user.has_org_perm(org,'depot.caigoushenqing_add'):
            transaction.rollback()
            return HttpResponse("你没有权限新增采购单")

        template_var['form']=InvoiceForm(instance=invoice)
        
        template_var['datas']=simplejson.dumps(invoice_id and [(_detail.good_id,_detail.good.name,
                                               _detail.num1,_detail.unit1 and _detail.unit1.unit or None,_detail.price,
                                               _detail.total_price,_detail.pk,_detail.good.nums,_detail.good.min_warning,_detail.good.category.name or '',_detail.good.remark) for _detail in invoice.details.all()] or [NONE_ROW])
    else:


        #权限判断
        if not request.user.has_org_perm(org,'depot.caigoushenqing_modify'):
            transaction.rollback()
            template_var['error_title'] = '你没有权限修改采购单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))

        try:
            form=InvoiceForm(request.POST.copy(),instance=invoice)
            
            details_data=[]
            details_data_error=[]
            details_data_error_count=0
            exists_key=[]
                
            formset_data_str=request.POST.get('data')
            
            if formset_data_str:
                formset_data=simplejson.loads(formset_data_str)
                i=0
                for detail in formset_data:
                    if detail[2] == 'null':
                        detail[2] = None
                    detail_data_error=[]
                    if detail!=NONE_ROW:
                        detail_data_error=[(i==0 and 2 or i) for i in [0,3,5] if (not detail[i] or (i!=3 and detail[i]<0))]
                        
                        
                        if not detail_data_error:
                            details_data.append(detail)
                            if detail[7]:
                                exists_key.append(detail[7])
                        else:
                            details_data_error_count+=1
                       
                    details_data_error.append(detail_data_error)
                    
            if form.is_valid() and details_data and not details_data_error_count:
                invoice=form.save(commit=False)
                invoice.org=org
                invoice.charger=request.user
                invoice.content_object=form.cleaned_data['rels']
                #避免单号重复，先提交一次
                if not invoice.invoice_code:
                    invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.save()

                
                if invoice_id:
                    #先清除没有的
                    all_key=list(invoice.details.values_list('id',flat=True))
                    delete_key=set(all_key)-set(exists_key)
                    invoice.details.filter(id__in=list(delete_key)).delete()
    
                total_price=0
                chenben_price=0
                print details_data
                for dd in details_data:
                    try:
                        good=Goods.objects.get(pk=dd[0])
                        unit=dd[4] and (dd[4]==good.unit.unit and good.unit or Unit.objects.filter(good_id=dd[0],unit=dd[4])[0]) or None
                        
                        num=good.change_nums(dd[3],unit)
                        
                        if dd[7]:
                            detail=InvoiceDetail.objects.get(pk=dd[7])
                            detail.good=good
                            #detail.batch_code=InvoiceDetail.get_next_detail_code()
                            detail.warehouse_root=invoice.warehouse_root
                            detail.warehouse=invoice.warehouse_root
                            detail.num1=dd[3]
                            detail.unit1=unit
                            detail.price=dd[5]
                            detail.total_price=dd[3]*dd[5]
                            detail.num=num
                            detail.last_nums=num
                        else:
                            detail=InvoiceDetail.objects.create(invoice=invoice,good=good,
                                    warehouse_root=invoice.warehouse_root,warehouse=invoice.warehouse_root,
                                    num1=dd[3],unit1=unit,price=dd[5],total_price=dd[5]*dd[3],
                                    num=num,last_nums=num
                                )
                        
                        #detail.chenben_price=good.chengben_price*num
                        detail.chenben_price=good.price_ori*num
                        #if dd[2]:
                            
                            #details=InvoiceDetail.objects.filter(invoice__status=2,batch_code=dd[2])
                            #if details:
                                #DetailRelBatch.objects.get_or_create(from_batch=detail,to_batch=details[0],level=True)
                                #detail.chenben_price=InvoiceDetail.objects.get(good=good,batch_code=dd[2]).avg_price*num
                            
                            
                        if unit and unit.good:
                            unit.sale_price=dd[5]
                            unit.save()
                        else:
                            good.sale_price=dd[5]
                            good.save()
                            
                        detail.avg_price=detail.num and detail.total_price/detail.num or 0
                        detail.save()
                        
                        total_price+=detail.total_price
                        chenben_price+=detail.chenben_price
                        
                    except:
                        print traceback.print_exc()
                        continue
                
                
                invoice.total_price=total_price
                
                invoice.sale_price=chenben_price
                invoice.save()
            
                   
                        
                    
                '''if form.cleaned_data['sstatus'] and user_can_confirm_invoice(invoice.warehouse_root, invoice.invoice_type, request.user):
                    try:
                        res=invoice.confirm(request.user)
                        if res!=2:
                            transaction.rollback()
                            return HttpResponseBadRequest(simplejson.dumps({'error':res}),mimetype='application/json')
                    except:
                        transaction.rollback()
                        print traceback.print_exc()
                        return HttpResponseBadRequest(simplejson.dumps({'error':traceback.print_exc()}),mimetype='application/json')
          
                '''
                content = _(u"修改了单据%s") %invoice.invoice_code.encode('utf8')
                OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

                transaction.commit()

                #根据参数配置，是否自动审核申请单

                auto_confirm = OrgProfile.objects.get(org=org).auto_confirm_caigoushenqing
                if auto_confirm is True and request.user.has_org_perm(org,'depot.caigoushenqing_confirm'):
                    transaction.commit()
                    print reverse("confirm_invoice",args=[org.uid,invoice.id])
                    return HttpResponse(simplejson.dumps({'action':'goon','url':reverse("confirm_invoice",args=[org.uid,invoice.id])} or {'action':'stay'}),mimetype='application/json')

                if request.is_ajax():

                    return HttpResponse(simplejson.dumps({'action':'goon','url':reverse('caigoushenqing_view',args=[org.uid])} or {'action':'stay'}),mimetype='application/json')
            else:
                if request.is_ajax():
                   
                    form_error_dict={}
                    
                    if form.errors:
                        for error in form.errors:
                            e=form.errors[error]
                            form_error_dict[error]=unicode(e)
                   
               
                    transaction.rollback()
                    return HttpResponseBadRequest(simplejson.dumps({'form_error_dict':form_error_dict,'details_data_error':details_data_error}),mimetype='application/json')
                    
            template_var['form']=form
        
        except:
            transaction.rollback()
            print traceback.print_exc()
    transaction.commit()
    response=render_to_response("main/caigoushenqing_add.html",template_var,context_instance=RequestContext(request))

    return response

#导出单据列表
def export_invoice(request,org_id,invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = Invoice.objects.filter(org=org,is_delete=0,invoice_type=invoice_type)

    workbook = xlwt.Workbook(encoding="utf8")
    sheet = workbook.add_sheet('sheet_1')
    if int(invoice_type) == 1004:
        sheet.write(0,0,'采购申请单列表')
    elif int(invoice_type) == 1001:
        sheet.write(0,0,'采购入库单列表')
    elif int(invoice_type) == 1000:
        sheet.write(0,0,'初始入库单列表')
    elif int(invoice_type) == 2002:
        sheet.write(0,0,'销售出库单列表')
    elif int(invoice_type) == 2001:
        sheet.write(0,0,'领用出库列表')
    elif int(invoice_type) == 2000:
        sheet.write(0,0,'采购退货列表')
    elif int(invoice_type) == 9000:
        sheet.write(0,0,'盘盈入库列表')
    elif int(invoice_type) == 9001:
        sheet.write(0,0,'盘亏出库列表')

    sheet.write(1,0,'单据号')
    sheet.write(1,1,'制单人')
    sheet.write(1,2,'经办人')
    sheet.write(1,3,'审核人')
    sheet.write(1,4,'时间')
    if int(invoice_type) in (1004,1001,1000,2000):
        sheet.write(1,5,'供应商')
    elif int(invoice_type) == 2001:
        sheet.write(1,5,'领用部门')
    elif int(invoice_type) in (9000,9001):
        pass
    else:
        sheet.write(1,5,"客户")
    if int(invoice_type) in (9000,9001):
        sheet.write(1,6,'单据来源')
    else:
        sheet.write(1,6,'申请金额')
        sheet.write(1,7,'单据状态')
    row = 2
    for invoice in invoices:
        sheet.write(row,0,invoice.invoice_code)
        sheet.write(row,1,invoice.charger.username)
        sheet.write(row,2,invoice.user.username)
        if invoice.confirm_user:
            sheet.write(row,3,invoice.confirm_user.username)
        else:
            sheet.write(row,3,"无")
        dt = invoice.modify_time.strftime("%Y-%m-%d %H:%M:%S")
        sheet.write(row,4,dt)
        if not invoice.invoice_type in (9000,9001,1000): 
            sheet.write(row,5,invoice.content_object.name)
        elif invoice.invoice_type == 1000:
            sheet.write(row,5,invoice.content_object.username)
        if invoice.invoice_type in (9000,9001):
            sheet.write(row,6,invoice.pandian_relate.id)
        else:
            sheet.write(row,6,invoice.total_price)
            if invoice.status == 1:    
                sheet.write(row,7,"申请中")
            elif invoice.status == 2:
                sheet.write(row,7,"已审核")
            else:
                sheet.write(row,7,"草稿")
        row = row+1

    response = HttpResponse(content_type='application/vnd.ms-excel')

    if int(invoice_type) == 1004:
        response['Content-Disposition'] = 'attachment; filename=采购申请单列表.xls'
    elif int(invoice_type) == 1001:
        response['Content-Disposition'] = 'attachment; filename=采购入库单列表.xls'
    elif int(invoice_type) == 1000:
        response['Content-Disposition'] = 'attachment; filename=初始入库单列表.xls'
    elif int(invoice_type) == 2002:
        response['Content-Disposition'] = 'attachment; filename=销售出库单列表.xls'
    elif int(invoice_type) == 2001:
        response['Content-Disposition'] = 'attachment; filename=领用出库单列表.xls'
    elif int(invoice_type) == 2000:
        response['Content-Disposition'] = 'attachment; filename=采购退货单列表.xls'
    elif int(invoice_type) == 9000:
        response['Content-Disposition'] = 'attachment; filename=盘盈入库单列表.xls'
    elif int(invoice_type) == 9001:
        response['Content-Disposition'] = 'attachment; filename=盘亏出库单列表.xls'
    
    workbook.save(response)



    return response

#导出单据详情
def export_invoice_detail(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoice = Invoice.objects.get(org=org,pk=invoice_id)

    workbook = xlwt.Workbook(encoding="utf8")
    sheet = workbook.add_sheet('sheet_1')
    sheet.write(0,0,"单据类型：%s" %invoice.get_invoice_type_name)
    sheet.write(0,2,"单据编号：%s" %invoice.invoice_code.encode("utf8"))
    sheet.write(0,4,"修改日期：%s" %invoice.modify_time.strftime("%Y-%m-%d"))
    if invoice.invoice_type in (1004,1001,2000):
        sheet.write(0,6,"供货商：%s" %invoice.content_object.name.encode("utf8"))
    elif invoice.invoice_type == 2002:
        sheet.write(0,6,"客户：%s" %invoice.content_object.name.encode("utf8"))
    elif invoice.invoice_type == 2001:
        sheet.write(0,6,"领用部门：%s" %invoice.content_object.name.encode("utf8"))
    sheet.write(0,8,"仓库：%s" %invoice.warehouse_root.name.encode("utf8"))
    sheet.write(1,0,"物品名称")
    sheet.write(1,1,"批次编号")
    sheet.write(1,2,"单位")
    sheet.write(1,3,"数量")
    sheet.write(1,4,"单价")
    sheet.write(1,5,"金额")
    row=2

    for item in invoice.details.select_related():
        sheet.write(row,0,item.good.name)
        sheet.write(row,1,item.batch_code)
        try:
            sheet.write(row,2,item.unit1.unit)
        except AttributeError:
            sheet.write(row,2,'')

        sheet.write(row,3,item.num)
        sheet.write(row,4,item.price)
        sheet.write(row,5,item.num*item.price)
        row = row + 1

    response = HttpResponse(content_type='application/vnd.ms-excel') 
    response['Content-Disposition'] = 'attachment; filename=invoice_%s.xls' %invoice.invoice_code.replace(' ','0')
    workbook.save(response)

    return response


#查看回收站
@page_template("main/huishouzhan_index.html")
def huishouzhan(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = Invoice.objects.filter(org=org,is_delete=1)
    template_var['invoices'] = invoices


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    invoice_code = request.GET.get('invoice_code')
    invoice_type = request.GET.get('invoice_type')
    remark = request.GET.get('remark')

    if startdate:
        invoices = invoices.filter(modify_time__gte=startdate)
    if enddate:
        invoices = invoices.filter(modify_time__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if invoice_type:
        invoices = invoices.filter(invoice_type=invoice_type)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if remark:
        invoices = invoices.filter(remark__contains=remark)

    template_var['invoices'] = invoices


    if extra_context is not None:
            template_var.update(extra_context)


    return render_to_response("main/huishouzhan.html",template_var,context_instance=RequestContext(request))

def delete_huishouzhan(request,org_id,invoice_id,invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_delete'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    if int(invoice_type) == 0:
        invoice = Invoice.objects.get(pk=invoice_id)
        content = _(u"删除了回收站单据%s") %invoice.invoice_code.encode('utf8')
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        invoice.delete()

        return HttpResponseRedirect(reverse("huishouzhan",args=[org.uid]))
    elif int(invoice_type) == 1:
        invoice = PayInvoice.objects.get(pk=invoice_id)

        content = _(u"删除了回收站单据%s") %invoice.invoice_code.encode('utf8')
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        invoice.delete()

        return HttpResponseRedirect(reverse("pay_huishouzhan",args=[org.uid]))

def clear_huishouzhan(request,org_id,invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_delete'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    if int(invoice_type) == 0:
        Invoice.objects.filter(org=org,is_delete=1).delete()
        content = _(u"清空了回收站库存单据")
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("huishouzhan",args=[org.uid]))
    elif int(invoice_type) == 1:
        PayInvoice.objects.filter(org=org,is_delete=1).delete()
        content = _(u"清空了回收站付款单据")
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("pay_huishouzhan",args=[org.uid]))


def restore_huishouzhan(request,org_id,invoice_id,invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_restore'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    if int(invoice_type) == 0:
        invoice = Invoice.objects.get(pk=invoice_id)
        invoice.is_delete = 0
        invoice.save()

        content = _(u"还原了单据%s") %invoice.invoice_code.encode('utf8')
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("huishouzhan",args=[org.uid]))

    elif int(invoice_type) == 1:
        invoice = PayInvoice.objects.get(pk=invoice_id)
        invoice.is_delete = 0
        invoice.save()

        content = _(u"还原了单据%s") %invoice.invoice_code.encode('utf8')
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("pay_huishouzhan",args=[org.uid]))

def restore_all_huishouzhan(request,org_id,invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_restore'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))
    if int(invoice_type) == 0:
        invoices = Invoice.objects.filter(org=org,is_delete=1).update(is_delete=0)
        content = _(u"还原了所有回收站库存单据")
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("huishouzhan",args=[org.uid]))
    elif int(invoice_type) == 1:
        invoices = PayInvoice.objects.filter(org=org,is_delete=1).update(is_delete=0)
        content = _(u"还原了所有回收站付款单据")
        OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

        return HttpResponseRedirect(reverse("pay_huishouzhan",args=[org.uid]))



#付款单
@page_template("main/fukuandan_index.html")
def fukuandan_view(request,org_id,template="main/fukuandan_view.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = PayInvoice.objects.filter(org=org,is_delete=0,invoice_type=3000)


    template_var['invoices'] = invoices


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    invoice_code = request.GET.get('invoice_code')
    result = request.GET.get('result')
    remark = request.GET.get('remark')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)

    template_var['invoices'] = invoices

    
    unpay_invoice = invoices.filter(result=0)
    template_var['unpay_invoice'] =unpay_invoice.count()
    template_var['unpay_total_price']=unpay_invoice.aggregate(Sum('total_pay'))
    template_var['unpay_rest_price']=unpay_invoice.aggregate(Sum('rest_pay'))

    if extra_context is not None:
            template_var.update(extra_context)

    return render_to_response(template,template_var,context_instance=RequestContext(request))

#@transaction.commit_manually
@anti_resubmit('fukuandan_add')
def fukuandan_add(request,org_id,invoice_id=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoice=None

    if invoice_id:
        invoice = PayInvoice.objects.get(pk=invoice_id)

        template_var['details'] = details = invoice.payinvoicedetail_set.all()
        template_var['invoice'] = invoice
    else:
        template_var['invoice'] = -1

    template_var['accounts']=accounts=BankAccount.objects.filter(org=org,status=0)


    if request.method == "GET":

        #权限判断
        if not request.user.has_org_perm(org,'depot.fukuandan_add'):
            template_var['error_title'] = '你没有权限新增付款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))

        template_var['form']=form=FukuandanAddForm(org,request.user,3000,instance=invoice)

    else:
        #权限判断
        if not request.user.has_org_perm(org,'depot.fukuandan_add') or not request.user.has_org_perm(org,'depot.fukuandan_modify'):
            template_var['error_title'] = '你没有权限修改付款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))

        template_var['form']=form=FukuandanAddForm(org,request.user,3000,request.POST.copy(),instance=invoice)
        detail=simplejson.loads(request.POST.get("detail"))

        if form.is_valid():
            if request.POST.get('invoice'):
                pay_invoice = PayInvoice.objects.get(pk=request.POST.get('invoice'))
                pay_invoice.charger = request.user
                pay_invoice.org = org
                pay_invoice.invoice_type = 3000
                pay_invoice.content_object=form.cleaned_data['rels']
                pay_invoice.total_pay = form.cleaned_data['total_pay']
                pay_invoice.invoice_code = form.cleaned_data['invoice_code']
                pay_invoice.warehouse_root = form.cleaned_data['warehouse_root']
                pay_invoice.remark = form.cleaned_data['remark']
                pay_invoice.save()

                already_pay = float(form.cleaned_data['already_pay'])

                if detail:

                    for item in detail['detail']:
                        try:
                            pay = float(item['pay'])
                        except:
                            pay_invoice.delete()
                            template_var['error_msg'] = "未填寫正確的已付金額"
                            return render_to_response("main/fukuandan_add.html",template_var,context_instance=RequestContext(request))

                        account = BankAccount.objects.get(pk=item['account'])

                        detail_event_date = datetime.datetime.now().strftime('%Y-%m-%d') if item['event_date'] == '' else item['event_date']

                        pay_detail = PayInvoiceDetail.objects.create(org=org,invoice=pay_invoice,pay=pay,pay_type=item['pay_type'],account=account,remark=item['remark'],event_date=detail_event_date)

                        already_pay = already_pay + pay

                    if pay_invoice.total_pay < already_pay:
                        pay_invoice.delete()
                        template_var['error_msg'] = "付款金额超过应付金额"
                        return render_to_response("main/fukuandan_add.html",template_var,context_instance=RequestContext(request))
                    elif pay_invoice.total_pay == already_pay:
                        pay_invoice.result = True

                        try:
                            invoice_from = pay_invoice.invoice_from
                            invoice_from.result = 2
                            invoice_from.save()
                        except:
                            pass


                    pay_invoice.already_pay = already_pay

                    pay_invoice.rest_pay = pay_invoice.total_pay - already_pay

                    pay_invoice.save()

                return HttpResponseRedirect(reverse("fukuandan_view",args=[org.uid]))

                

            else:
                pay_invoice = form.save(commit=False)
                pay_invoice.charger = request.user
                pay_invoice.org = org
                pay_invoice.invoice_type = 3000

                pay_invoice.content_object=form.cleaned_data['rels']
                if not pay_invoice.invoice_code:
                        pay_invoice.invoice_code=PayInvoice.get_next_invoice_code()
                pay_invoice.save()

                already_pay = 0

                if detail:

                    for item in detail['detail']:
                        try:
                            pay = float(item['pay'])
                        except:
                            pay_invoice.delete()
                            template_var['error_msg'] = "未填寫正確的已付金額"
                            return render_to_response("main/fukuandan_add.html",template_var,context_instance=RequestContext(request))

                        account = BankAccount.objects.get(pk=item['account'])

                        detail_event_date = datetime.datetime.now().strftime('%Y-%m-%d') if item['event_date'] == '' else item['event_date']

                        PayInvoiceDetail.objects.create(org=org,invoice=pay_invoice,pay=pay,pay_type=item['pay_type'],account=account,remark=item['remark'],event_date=detail_event_date)

                        already_pay = already_pay + pay

                    if pay_invoice.total_pay < already_pay:
                        pay_invoice.delete()
                        template_var['error_msg'] = "付款金额超过应付金额"
                        return render_to_response("main/fukuandan_add.html",template_var,context_instance=RequestContext(request))
                    elif pay_invoice.total_pay == already_pay:
                        pay_invoice.result = True

                        try:
                            invoice_from = pay_invoice.invoice_from
                            invoice_from.result = 2
                            invoice_from.save()
                        except:
                            pass

                    pay_invoice.already_pay = already_pay

                    pay_invoice.rest_pay = pay_invoice.total_pay - already_pay

                    pay_invoice.save()

                return HttpResponseRedirect(reverse("fukuandan_view",args=[org.uid]))
        else:
            print form.errors

    return render_to_response("main/fukuandan_add.html",template_var,context_instance=RequestContext(request))


#删除付款单详情
def delete_paydetail(request,org_id,detail_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    detail = PayInvoiceDetail.objects.get(pk=detail_id)
    invoice = detail.invoice
    
    invoice.already_pay = invoice.already_pay - detail.pay
    invoice.rest_pay = invoice.total_pay - invoice.already_pay

    if invoice.total_pay != invoice.already_pay:
        invoice.result = False
    invoice.save()
    detail.delete()

    if invoice.invoice_type == 3000:

        return HttpResponseRedirect(reverse("fukuandan_modify",args=[org.uid,invoice.id]))

    else:
        return HttpResponseRedirect(reverse("shoukuandan_modify",args=[org.uid,invoice.id]))

#删除付款单
def delete_pay_invoice(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoice = PayInvoice.objects.get(pk=invoice_id)

    if invoice.invoice_type == 3000:

        #权限判断
        if not request.user.has_org_perm(org,'depot.fukuandan_delete'):
            template_var['error_title'] = '你没有权限删除付款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))
        if invoice.result == 1:
            return HttpResponse("已付清单据无法删除")

        invoice.is_delete = 1

        invoice.save()
            
        content=_(u"删除了付款单%s") %invoice.invoice_code.encode("utf8")
        OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

        return HttpResponseRedirect(reverse("fukuandan_view",args=[org.uid]))

    else:
        #权限判断
        if not request.user.has_org_perm(org,'depot.shoukuandan_delete'):
            template_var['error_title'] = '你没有权限删除收款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))
        if invoice.result == 1:
            return HttpResponse("已收完单据无法删除")

        invoice.is_delete = 1

        invoice.save()
            
        content=_(u"删除了收款单%s") %invoice.invoice_code.encode("utf8")
        OperateLog.objects.create(org=org,created_user=request.user.username,content=content)

        return HttpResponseRedirect(reverse("shoukuandan_view",args=[org.uid]))

def export_pay_invoice(request,org_id,pay_invoice_type):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = PayInvoice.objects.filter(org=org,is_delete=0,invoice_type=pay_invoice_type)

    workbook = xlwt.Workbook(encoding="utf8")
    sheet = workbook.add_sheet('sheet_1')
    sheet.write(0,0,'付款单列表')

    sheet.write(1,0,'单据号')
    sheet.write(1,1,'制单人')
    sheet.write(1,2,'经办人')
    sheet.write(1,3,'时间')
    sheet.write(1,4,'应付金额')
    sheet.write(1,5,'已付金额')
    sheet.write(1,6,'未付金额')
    sheet.write(1,7,'单据状态')
    row = 2
    for invoice in invoices:
        sheet.write(row,0,invoice.invoice_code)
        sheet.write(row,1,invoice.charger.username)
        sheet.write(row,2,invoice.user.username)
        dt = invoice.event_date.strftime("%Y-%m-%d")
        sheet.write(row,3,dt)
        sheet.write(row,4,invoice.total_pay)
        sheet.write(row,5,invoice.already_pay)
        sheet.write(row,6,invoice.rest_pay)
        if invoice.result == 0:    
            sheet.write(row,7,"未付清")
        elif invoice.result == 1:
            sheet.write(row,7,"已付清")
        row = row+1

    response = HttpResponse(content_type='application/vnd.ms-excel') 
    response['Content-Disposition'] = 'attachment; filename=invoice_list.xls'
    workbook.save(response)



    return response

def export_pay_invoice_detail(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoice = PayInvoice.objects.get(org=org,pk=invoice_id)

    workbook = xlwt.Workbook(encoding="utf8")
    sheet = workbook.add_sheet('sheet_1')
    sheet.write(0,0,"单据类型：付款单")
    sheet.write(0,2,"单据编号：%s" %invoice.invoice_code.encode("utf8"))
    sheet.write(0,4,"单据日期：%s" %invoice.event_date.strftime("%Y-%m-%d"))
    sheet.write(0,6,"制单人：%s" %invoice.charger.username.encode("utf8"))
    sheet.write(0,8,"经办人：%s" %invoice.user.username.encode("utf8"))
    if invoice.invoice_type == 3000:
        sheet.write(0,10,"应付款：%d" %invoice.total_pay)
        sheet.write(0,12,"未付款：%d" %invoice.rest_pay)
        sheet.write(0,14,"已付款：%d" %invoice.already_pay)
    else:
        sheet.write(0,10,"应收款：%d" %invoice.total_pay)
        sheet.write(0,12,"未收款：%d" %invoice.rest_pay)
        sheet.write(0,14,"已收款：%d" %invoice.already_pay)
    sheet.write(1,0,"付款明细：")
    sheet.write(2,0,"序号")
    sheet.write(2,1,"账户")
    sheet.write(2,2,"金额")
    sheet.write(2,3,"支付方式")
    if invoice.invoice_type == 3000:
        sheet.write(2,4,"付款日期")
    else:
        sheet.write(2,4,"收款日期")
    sheet.write(2,5,"备注")
    row=3

    for item in invoice.payinvoicedetail_set.select_related():
        sheet.write(row,0,row-2)
        sheet.write(row,1,item.account.account_name)
        sheet.write(row,2,item.pay)

        sheet.write(row,3,item.pay_type)
        sheet.write(row,4,item.modify_time.strftime("%Y-%m-%d"))
        sheet.write(row,5,item.remark)
        row = row + 1

    response = HttpResponse(content_type='application/vnd.ms-excel') 
    response['Content-Disposition'] = 'attachment; filename=invoice_%s.xls' %invoice.invoice_code
    workbook.save(response)

    return response
@page_template("main/pay_huishouzhan_index.html")
def pay_huishouzhan(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = PayInvoice.objects.filter(org=org,is_delete=1)
    template_var['invoices'] = invoices


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    invoice_code = request.GET.get('invoice_code')
    result = request.GET.get('result')
    remark = request.GET.get('remark')

    if startdate:
        invoices = invoices.filter(modify_time__gte=startdate)
    if enddate:
        invoices = invoices.filter(modify_time__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if result:
        invoices = invoices.filter(result=result)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if remark:
        invoices = invoices.filter(remark__contains=remark)

    template_var['invoices'] = invoices

    if extra_context is not None:
            template_var.update(extra_context)


    return render_to_response("main/pay_huishouzhan.html",template_var,context_instance=RequestContext(request))


def pay_invoice_view(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['invoice']=invoice=PayInvoice.objects.get(pk=invoice_id)


    return render_to_response("main/pay_invoice_view.html",template_var,context_instance=RequestContext(request))

def print_pay_invoice(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    template_var['invoice']=invoice=PayInvoice.objects.get(pk=invoice_id)
    now_time=datetime.datetime.now()
    template_var['now_time']=now_time


    return render_to_response("print_template/pay_invoice.html",template_var,context_instance=RequestContext(request))


#付款单
@page_template("main/shoukuandan_index.html")
def shoukuandan_view(request,org_id,template="main/shoukuandan_view.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = PayInvoice.objects.filter(org=org,is_delete=0,invoice_type=3001)


    template_var['invoices'] = invoices

 
    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    invoice_code = request.GET.get('invoice_code')
    result = request.GET.get('result')
    remark = request.GET.get('remark')

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)
    if result:
        invoices = invoices.filter(result=result)
    if remark:
        invoices = invoices.filter(remark__contains=remark)

    template_var['invoices'] = invoices

    unpay_invoice = invoices.filter(result=0)
    template_var['unpay_invoice'] =unpay_invoice.count()
    template_var['unpay_total_price']=unpay_invoice.aggregate(Sum('total_pay'))
    template_var['unpay_rest_price']=unpay_invoice.aggregate(Sum('rest_pay'))

    if extra_context is not None:
            template_var.update(extra_context)

    return render_to_response(template,template_var,context_instance=RequestContext(request))

@anti_resubmit('shoukuandan_add')
def shoukuandan_add(request,org_id,invoice_id=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoice=None

    if invoice_id:
        invoice = PayInvoice.objects.get(pk=invoice_id)

        template_var['details'] = details = invoice.payinvoicedetail_set.all()
        template_var['invoice'] = invoice
    else:
        template_var['invoice'] = -1

    template_var['accounts']=accounts=BankAccount.objects.filter(org=org,status=0)


    if request.method == "GET":

        #权限判断
        if not request.user.has_org_perm(org,'depot.shoukuandan_add'):
            template_var['error_title'] = '你没有权限新增收款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))

        template_var['form']=form=FukuandanAddForm(org,request.user,3001,instance=invoice)

    else:
        #权限判断
        if not request.user.has_org_perm(org,'depot.shoukuandan_add') or not request.user.has_org_perm(org,'depot.fukuandan_modify'):
            template_var['error_title'] = '你没有权限修改收款单'
            return render_to_response("500.html",template_var,context_instance=RequestContext(request))

        template_var['form']=form=FukuandanAddForm(org,request.user,3001,request.POST.copy(),instance=invoice)
        detail=simplejson.loads(request.POST.get("detail"))

        if form.is_valid():
            if request.POST.get('invoice'):
                pay_invoice = PayInvoice.objects.get(pk=request.POST.get('invoice'))
                pay_invoice.charger = request.user
                pay_invoice.org = org
                pay_invoice.invoice_type = 3001
                pay_invoice.content_object=form.cleaned_data['rels']
                pay_invoice.total_pay = form.cleaned_data['total_pay']
                pay_invoice.invoice_code = form.cleaned_data['invoice_code']
                pay_invoice.warehouse_root = form.cleaned_data['warehouse_root']
                pay_invoice.remark = form.cleaned_data['remark']
                pay_invoice.save()

                already_pay = float(form.cleaned_data['already_pay'])

                if detail:

                    for item in detail['detail']:
                        try:
                            pay = float(item['pay'])
                        except:
                            pay_invoice.delete()
                            template_var['error_msg'] = "未填寫正確的已收金額"
                            return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))
                        try:
                            account = BankAccount.objects.get(pk=item['account'])
                        except:
                            account = None

                        detail_event_date = datetime.datetime.now().strftime('%Y-%m-%d') if item['event_date'] == '' else item['event_date']

                        pay_detail = PayInvoiceDetail.objects.create(org=org,invoice=pay_invoice,pay=pay,pay_type=item['pay_type'],account=account,remark=item['remark'],event_date=detail_event_date)

                        already_pay = already_pay + pay

                    if pay_invoice.total_pay < already_pay:
                        pay_invoice.delete()
                        template_var['error_msg'] = "收款金额超过应收金额"
                        return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))
                    elif pay_invoice.total_pay == already_pay:
                        pay_invoice.result = True

                        try:
                            invoice_from = pay_invoice.invoice_from
                            invoice_from.result = 2
                            invoice_from.save()
                        except:
                            pass

                    pay_invoice.already_pay = already_pay

                    pay_invoice.rest_pay = pay_invoice.total_pay - already_pay

                    pay_invoice.save()

                return HttpResponseRedirect(reverse("shoukuandan_view",args=[org.uid]))

                

            else:
                pay_invoice = form.save(commit=False)
                pay_invoice.charger = request.user
                pay_invoice.org = org
                pay_invoice.invoice_type = 3001

                pay_invoice.content_object=form.cleaned_data['rels']
                if not pay_invoice.invoice_code:
                        pay_invoice.invoice_code=PayInvoice.get_next_invoice_code()
                pay_invoice.save()

                already_pay = 0

                if detail:

                    for item in detail['detail']:
                        try:
                            pay = float(item['pay'])
                        except:
                            pay_invoice.delete()
                            template_var['error_msg'] = "未填寫正確的已收金額"
                            return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))
                        try:
                            account = BankAccount.objects.get(pk=item['account'])
                        except:
                            account = None

                        detail_event_date = datetime.datetime.now().strftime('%Y-%m-%d') if item['event_date'] == '' else item['event_date']

                        PayInvoiceDetail.objects.create(org=org,invoice=pay_invoice,pay=pay,pay_type=item['pay_type'],account=account,remark=item['remark'],event_date=detail_event_date)

                        already_pay = already_pay + pay

                    if pay_invoice.total_pay < already_pay:
                        pay_invoice.delete()
                        template_var['error_msg'] = "收款金额超过应付金额"
                        return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))
                    elif pay_invoice.total_pay == already_pay:
                        pay_invoice.result = True

                        try:
                            invoice_from = pay_invoice.invoice_from
                            invoice_from.result = 2
                            invoice_from.save()
                        except:
                            pass

                    pay_invoice.already_pay = already_pay

                    pay_invoice.rest_pay = pay_invoice.total_pay - already_pay

                    pay_invoice.save()

                return HttpResponseRedirect(reverse("shoukuandan_view",args=[org.uid]))
        else:
            print form.errors

    return render_to_response("main/shoukuandan_add.html",template_var,context_instance=RequestContext(request))

@page_template("main/select_invoices_use_index.html")
def select_invoices_use(request,org_id,template="main/select_invoices_use.html",extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices=Invoice.objects.filter(invoice_type=1001,is_delete=0,status=2,org=org)
    template_var['form']=form=SelectInvoicesForm()

    if request.method == "GET":

        template_var['invoices']=invoices

        form=SelectInvoicesForm(request.GET.copy())


    if form.is_valid():
        keyword = form.cleaned_data['keyword']
        event_date = form.cleaned_data['event_date']

        if event_date:
            invoices = invoices.filter(event_date=event_date)

        if keyword:

            invoices = invoices.filter(Q(invoice_code__icontains=keyword)|Q(voucher_code__icontains=keyword)|Q(remark__icontains=keyword)|Q(charger__username__icontains=keyword)|Q(user__username__icontains=keyword)|Q(confirm_user__username__icontains=keyword))
            
        template_var['invoices']=invoices
    else:
        print form.errors

    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response(template,template_var,context_instance=RequestContext(request))

@page_template('main/panyingruku_index.html')
def panyingruku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()

    invoices = Invoice.objects.filter(org=org,invoice_type=9000,is_delete=0)
    template_var['invoices'] = invoices
    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    invoice_code = request.GET.get('invoice_code')


    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)

    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)


    template_var['invoices'] = invoices

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/panyingruku.html",template_var,context_instance=RequestContext(request))


@page_template('main/pankuichuku_index.html')
def pankuichuku(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    root_org=org.get_root_org()

    invoices = Invoice.objects.filter(org=org,invoice_type=9001,is_delete=0)

    template_var['invoices'] = invoices

    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    confirm_user = request.GET.get('confirm_user')
    invoice_code = request.GET.get('invoice_code')
        
        
       

    if startdate:
        invoices = invoices.filter(event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(event_date__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if confirm_user:
        invoices = invoices.filter(confirm_user__username__icontains=confirm_user)
    if invoice_code:
        invoices = invoices.filter(invoice_code__icontains=invoice_code)

    template_var['invoices'] = invoices

    if extra_context is not None:
        template_var.update(extra_context)
    return render_to_response("main/pankuichuku.html",template_var,context_instance=RequestContext(request))


#导出盘点数据
def export_pandian(request,org_id,snap_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    reload(sys)
    sys.setdefaultencoding('utf-8')  
    snap = SnapshotWarehouse.objects.get(org=org,pk=snap_id)

    workbook = xlwt.Workbook(encoding="utf8")
    sheet = workbook.add_sheet('sheet_1')

    sheet.write(0,0,"盘点单")
    sheet.write(1,0,"物品名称")
    sheet.write(1,1,"编码")
    sheet.write(1,2,"类别")
    sheet.write(1,3,"规格")
    sheet.write(1,4,"单位")
    sheet.write(1,5,"库存数量")
    sheet.write(1,6,"盘点数量")
    sheet.write(1,7,"盘差")
    row = 2

    for good in snap.goods.select_related():
        sheet.write(row,0,good.name)
        sheet.write(row,1,good.code)
        sheet.write(row,2,good.category_name)
        sheet.write(row,3,good.standard)
        try:
            sheet.write(row,4,good.unit.unit.encode("utf8"))
        except:
            pass
        sheet.write(row,5,good.last_nums)
        sheet.write(row,6,good.shiji)
        sheet.write(row,7,good.pancha)
        row += 1



    response = HttpResponse(content_type='application/vnd.ms-excel') 
    response['Content-Disposition'] = 'attachment; filename=pandian:%s.xls'%snap_id
    workbook.save(response)



    return response

@page_template("main/pandian_huishouzhan_index.html")
def pandian_huishouzhan(request,org_id,extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = SnapshotWarehouse.objects.filter(org=org,is_delete=1)
    template_var['invoices'] = invoices


    startdate = request.GET.get('startdate')
    enddate = request.GET.get('enddate')
    charger = request.GET.get('charger')
    user = request.GET.get('user')
    invoice_code = request.GET.get('invoice_code')


    if startdate:
        invoices = invoices.filter(modify_time__gte=startdate)
    if enddate:
        invoices = invoices.filter(modify_time__lte=enddate)
    if charger:
        invoices = invoices.filter(charger__username__icontains=charger)
    if user:
        invoices = invoices.filter(user__username__icontains=user)
    if invoice_code:
        invoices = invoices.filter(pk__icontains=invoice_code)


    template_var['invoices'] = invoices

    if extra_context is not None:
            template_var.update(extra_context)


    return render_to_response("main/pandian_huishouzhan.html",template_var,context_instance=RequestContext(request))

def delete_pandian_huishouzhan(request,org_id,invoice_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_delete'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    invoice = SnapshotWarehouse.objects.get(pk=invoice_id)
    content = _(u"删除了回收站盘点单据%s") %invoice.id
    OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

    invoice.delete()

    return HttpResponseRedirect(reverse("pandian_huishouzhan",args=[org.uid]))


def clear_pandian_huishouzhan(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_delete'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    SnapshotWarehouse.objects.filter(org=org,is_delete=1).delete()
    content = _(u"清空了回收站盘点单据")
    OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

    return HttpResponseRedirect(reverse("pandian_huishouzhan",args=[org.uid]))


def restore_pandian_huishouzhan(request,org_id,snap_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_restore'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    invoice = SnapshotWarehouse.objects.get(pk=snap_id)
    invoice.is_delete = 0
    invoice.save()

    content = _(u"还原了盘点单据%s") %invoice.pk
    OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

    return HttpResponseRedirect(reverse("pandian_huishouzhan",args=[org.uid]))


def restore_all_pandian_huishouzhan(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    #权限判断
    if not request.user.has_org_perm(org,'depot.huishouzhan_restore'):
        template_var['error_title'] = '你没有权限'
        return render_to_response("500.html",template_var,context_instance=RequestContext(request))

    invoices = SnapshotWarehouse.objects.filter(org=org,is_delete=1).update(is_delete=0)
    content = _(u"还原了所有回收站盘点单据")
    OperateLog.objects.create(created_user=request.user.username,org=org,content=content)

    return HttpResponseRedirect(reverse("pandian_huishouzhan",args=[org.uid]))
