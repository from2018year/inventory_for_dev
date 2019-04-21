# -*- coding: utf-8 -*- 
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect,\
    HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from endless_pagination.decorators import page_template
from depot.models import Organization, Supplier, ConDepartment, Customer,\
    Warehouse, Invoice, InvoiceDetail, Goods, GoodHisSnap, GoodHisSnapDetail
from inventory.common import *
from inventory.common import  _Wookbook
from pyExcelerator.Formatting import Font
from pyExcelerator.Style import XFStyle
from django.db.models import Q,Sum,Count,Min,Max,Avg
from django.db.models.query import QuerySet
from django.forms.models import modelformset_factory, inlineformset_factory
from django.utils import simplejson
from django.contrib.auth.models import User
from depot.views.forms.tongji_forms import make_SearchDanjuForm,\
    make_LingyongDanjuForm, make_GonghuoshangDanjuForm, make_InoutDanjuForm,\
    make_InoutDanjuDetailForm
from django.contrib.contenttypes.models import ContentType
import logging
import traceback
from depot.views.base import require_pos_config
from django.db.models import F
from cost.forms import DateRangeForm
from cost.models import SyncHis
from django.db import transaction, connection
import sys


@login_required
@require_pos_config
def tongji_main(request,org_id):
    try:
        template_var={}
        
        try:
            template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
        
        request.session['org_id']=org_id
        request.session['org']=org
        request.session['root_org']=org.get_root_org()
        
        warehouses=request.user.get_warehouses(org)
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
   
        return render_to_response("tongji/tongji_main.html",template_var,context_instance=RequestContext(request))
        #return render_to_response("org_backstage.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()
        
        
'''
    单据查询
'''
@page_template('tongji/search_danju_index_page.html') 
def tongji_search_danju(request,org_id,template='tongji/search_danju.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
    SearchDanjuForm=make_SearchDanjuForm(org.pk)
    
    if not request.GET.copy():
        template_var['form']=SearchDanjuForm()
    else:
        form=SearchDanjuForm(request.GET.copy())
        if form.is_valid():
            template_var['post']=True
            invoices=Invoice.objects.filter(org=org,status=2)
            
            if form.cleaned_data['date_from']:
                invoices=invoices.filter(event_date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                invoices=invoices.filter(event_date__lte=form.cleaned_data['date_to'])
        
            if form.cleaned_data['invoice_code']:
                invoices=invoices.filter(invoice_code__icontains=form.cleaned_data['invoice_code'])
            if form.cleaned_data['voucher_code']:
                invoices=invoices.filter(voucher_code__icontains=form.cleaned_data['voucher_code'])
            
            if form.cleaned_data['result']:
                invoices=invoices.filter(result=form.cleaned_data['result'])
            
            if form.cleaned_data['warehouse_root']:
                invoices=invoices.filter(warehouse_root=form.cleaned_data['warehouse_root'])
            
            if form.cleaned_data['invoice_type']:
                invoices=invoices.filter(invoice_type=form.cleaned_data['invoice_type'])
     
            if form.cleaned_data['refer']:
                invoices=invoices.filter(object_id=form.cleaned_data['refer'])
            if form.cleaned_data['remark']:
                invoices=invoices.filter(remark__icontains=form.cleaned_data['remark'])
            
            if form.cleaned_data['min_price']:
                invoices=invoices.filter(total_price__gte=form.cleaned_data['min_price'])
            if form.cleaned_data['max_price']:
                invoices=invoices.filter(total_price__lte=form.cleaned_data['max_price'])
            
            template_var['invoices']=invoices
            template_var['invoices_count']=invoices.count() 
            template_var['invoices_money']=invoices.distinct().aggregate(sum=Sum('total_price'))['sum']
            template_var['invoices_weijie']=invoices.filter(result=0).distinct().aggregate(sum=Sum('total_price'),count=Count('total_price'))    
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'单据号'),_(u'物品名称'),_(u'物品编号'),_(u'规格'),_(u'单位'),_(u'数量'),_(u'单价'),_(u'总价'),_(u'时间')]
                ws=wb.add_sheet(_(u'单据详细数据'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for invoice in invoices.order_by('event_date'):
                    for detail in invoice.details.all():
                        ws.write(i,0,invoice.invoice_code,style1)
                        ws.write(i,1,detail.good.name,style1)
                        ws.write(i,3,detail.good.standard or '-',style1)
                        ws.write(i,4,detail.good.unit and detail.good.unit.unit or '-',style1)
                        ws.write(i,5,round(detail.num,2),style1)
                        ws.write(i,6,round(detail.price,2),style1)
                        ws.write(i,7,round(detail.total_price,2),style1)
                        ws.write(i,8,invoice.event_date.strftime('%Y-%m-%d'),style1)
                        i+=1
                
                ws.col(0).width=0x1300
                ws.col(1).width=0x1000
                ws.col(2).width=0x1400
                ws.col(8).width=0x1000
                ws.col(9).width=0x1600
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'单据数据表').encode('gbk'))
                return response
        template_var['form']=form
    
        if extra_context is not None:
            template_var.update(extra_context)
            
    return render_to_response(template,template_var,context_instance=RequestContext(request))


'''
    返回单据类型的列表
'''
def tongji_get_refer(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
        
        refer_type=int(request.GET.get('refer_type',0) or 0)
        objects=None
        if refer_type==1001:
            objects=Supplier.objects.filter(org=org,status=1)
        elif refer_type==1002:
            objects=ConDepartment.objects.filter(org=org,status=1)
        elif refer_type==2000:
            objects=Supplier.objects.filter(org=org,status=1)
        elif refer_type==2001:
            objects=ConDepartment.objects.filter(org=org,status=1)
        elif refer_type==2002:
            objects=Customer.objects.filter(org=org,status=1)
        elif refer_type in [9999,10000]:
            objects=Warehouse.objects.filter(org=org,parent__isnull=True,status=True)
        if objects:
            refers=list(objects.values_list('id','name'))
        else:
            refers=[]
        refers.insert(0, ('',_(u'所有单位')))
        
        return HttpResponse(simplejson.dumps(refers), mimetype="'application/json'")
    except:
        print traceback.print_exc()
        
        
'''
    领用物品查询
'''
def tongji_lingyong_danju(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
    LingyongDanjuForm=make_LingyongDanjuForm(org)
    
    if not request.GET.copy():
        template_var['form']=LingyongDanjuForm()
    else:
        form=LingyongDanjuForm(request.GET.copy())
        if form.is_valid():
            template_var['post']=True
            details=InvoiceDetail.objects.select_related('good').filter(invoice__org=org,invoice__invoice_type=2001,invoice__status=2)
            if form.cleaned_data['date_from']:
                details=details.filter(invoice__event_date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                details=details.filter(invoice__event_date__lte=form.cleaned_data['date_to'])
                
            if form.cleaned_data['category']:
                categorys=form.cleaned_data['category'].get_descendants(include_self=True)
                details=details.filter(good__category__in=categorys)
                
            if form.cleaned_data['conDepartment']:
                template_var['conDepartment_type']=conDepartment_type=1
                details=details.filter(invoice__content_type=ContentType.objects.get_for_model(form.cleaned_data['conDepartment']) ,
                                       invoice__object_id=form.cleaned_data['conDepartment'].pk)
            if form.cleaned_data['remark']:
                details = details.filter(remark__icontains=form.cleaned_data['remark'])    
            else:
                template_var['conDepartment_type']=conDepartment_type=0
                
                
            totals=details.values('good','good__name','good__unit__unit').annotate(num=Sum('num'),sum=Sum('total_price'))
            template_var['goods_count']=len(details.values('good').distinct())
            template_var['goods_money']=details.aggregate(sum=Sum('total_price'))['sum']
            details=list(details.filter(good=total['good']).values('good','good__unit__unit','invoice__object_id').annotate(num=Sum('num'),sum=Sum('total_price')) for total in totals)
            
            template_var['con_dict']=con_dict=dict([(x['id'],x['name']) for x in ConDepartment.objects.filter(org=org).values('id','name')])
            
            template_var['total_detail']=total_detail=zip(totals,details)
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'物品'),_(u'部门'),_(u'领用数量'),_(u'物品单位'),_(u'总价')]
                ws=wb.add_sheet(_(u'领用详细数据'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for total,details in total_detail:
                    ws.write(i,0,total['good__name'],style1)
                    ws.write(i,2,total['num'],style1)
                    ws.write(i,3,total['good__unit__unit'] or '',style1)
                    ws.write(i,4,total['sum'],style1)
                    i+=1
                    if not conDepartment_type:
                        for detail in details:
                            ws.write(i,1,con_dict.get(detail['invoice__object_id']),style1)
                            ws.write(i,2,detail['num'],style1)
                            ws.write(i,3,detail['good__unit__unit'] or '',style1)
                            ws.write(i,4,detail['sum'],style1)
                            i+=1
            
                    
                
                ws.col(0).width=0x1300
                ws.col(1).width=0x1300
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'领用数据表').encode('gbk'))
                return response
    
        template_var['form']=form
    return render_to_response("tongji/lingyong_danju.html",template_var,context_instance=RequestContext(request))



'''
    供货商物品查看
'''
def tongji_gonghuoshang_danju(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
    GonghuoshangDanjuForm=make_GonghuoshangDanjuForm(org)
    
    if not request.GET.copy():
        template_var['form']=GonghuoshangDanjuForm()
    else:
        form=GonghuoshangDanjuForm(request.GET.copy())
        if form.is_valid():
            template_var['post']=True
            details=InvoiceDetail.objects.select_related('good').filter(invoice__org=org,invoice__invoice_type=1001,invoice__status=2)
            if form.cleaned_data['date_from']:
                details=details.filter(invoice__event_date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                details=details.filter(invoice__event_date__lte=form.cleaned_data['date_to'])
                
            if form.cleaned_data['category']:
                categorys=form.cleaned_data['category'].get_descendants(include_self=True)
                details=details.filter(good__category__in=categorys)
                
            if form.cleaned_data['supplier']:
                template_var['supplier_type']=supplier_type=1
                details=details.filter(invoice__content_type=ContentType.objects.get_for_model(form.cleaned_data['supplier']) ,
                                       invoice__object_id=form.cleaned_data['supplier'].pk)
            if form.cleaned_data['remark']:
                details=details.filter(remark__icontains=form.cleaned_data['remark'])   
            else:
                template_var['supplier_type']=supplier_type=0
                
                
            totals=details.values('good','good__name','good__unit__unit').annotate(max_price=Max('avg_price'),min_price=Min('avg_price'),num=Sum('num'),sum=Sum('total_price'))
            template_var['goods_count']=len(details.values('good').distinct())
            template_var['goods_money']=details.aggregate(sum=Sum('total_price'))['sum']
            details=list(details.filter(good=total['good']).values('good','good__unit__unit','invoice__object_id').annotate(max_price=Max('avg_price'),min_price=Min('avg_price'),num=Sum('num'),sum=Sum('total_price')) for total in totals)
            
            template_var['con_dict']=con_dict=dict([(x['id'],x['name']) for x in Supplier.objects.filter(org=org).values('id','name')])
            
            template_var['total_detail']=total_detail=zip(totals,details)
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'物品'),_(u'供货商'),_(u'采购数量'),_(u'物品单位'),_(u'最低单价'),_(u'最高单价'),_(u'平均价格'),_(u'总价')]
                ws=wb.add_sheet(_(u'采购详细数据'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for total,details in total_detail:
                    ws.write(i,0,total['good__name'],style1)
                    ws.write(i,2,total['num'],style1)
                    ws.write(i,3,total['good__unit__unit'] or '',style1)
                    ws.write(i,4,total['min_price'],style1)
                    ws.write(i,5,total['max_price'],style1)
                    ws.write(i,6,round(total['num'] and total['sum']/total['num'] or total['num'],2),style1)
                    ws.write(i,7,total['sum'],style1)
                    i+=1
                    if not supplier_type:
                        for detail in details:
                            ws.write(i,1,con_dict.get(detail['invoice__object_id']),style1)
                            ws.write(i,2,detail['num'],style1)
                            ws.write(i,3,detail['good__unit__unit'] or '',style1)
                            ws.write(i,4,detail['min_price'],style1)
                            ws.write(i,5,detail['max_price'],style1)
                            ws.write(i,6,round(detail['num'] and detail['sum']/detail['num'] or detail['num'],2),style1)
                            ws.write(i,7,detail['sum'],style1)
                            i+=1
            
                    
                
                ws.col(0).width=0x1300
                ws.col(1).width=0x1300
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'领用数据表').encode('gbk'))
                return response
    
        template_var['form']=form
    return render_to_response("tongji/gonghuoshang_danju.html",template_var,context_instance=RequestContext(request))

'''
    物品出入明细
'''
@page_template('tongji/goods_inout_detail_index.html')
def tongji_goods_inout_detail(request,org_id,template='tongji/goods_inout_detail.html',extra_context=None):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
    InoutDanjuDetailForm=make_InoutDanjuDetailForm(org)
    
    if request.GET.has_key('keyword'):
        try:
            keyword=request.GET.get('keyword')
            lst=[{'name':goods.name,'category':goods.category.name,'id':goods.id} for goods in Goods.objects.filter(Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword),org=org)[:5]]
            if extra_context is not None:
                template_var.update(extra_context)
            return HttpResponse(simplejson.dumps(lst), mimetype='application/json')
        except:
            print traceback.print_exc()
                
    if not request.GET.copy():
        template_var['form']=InoutDanjuDetailForm()
    else:
        datas=request.GET.copy()
        if not datas.get('inout'):
            datas.setlist('inout',[1000,1001,2000,2001,2002])
        if not datas.get('date_from'):
            datas['date_from']=datetime.date.today().replace(day=1)
        if not datas.get('date_to'):
            datas['date_to']=datetime.date.today()
        form=InoutDanjuDetailForm(datas)
        if form.is_valid():
            
            template_var['post']=True
            goods_id=form.cleaned_data['goods_id']
            template_var['goods']=Goods.objects.get(org=org,pk=goods_id)
            template_var['invoices']=invoices=Invoice.objects.filter(invoice_type__in=form.cleaned_data['inout']).filter(event_date__gte=form.cleaned_data['date_from'],event_date__lte=form.cleaned_data['date_to'],details__good_id=goods_id,org=org,status=2).distinct().extra(select={
                                    'goods_sum':'SELECT SUM(num) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id,
                                    'goods_sum_price':'SELECT SUM(total_price) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id,
                                    'goods_price':'SELECT MAX(price) FROM depot_invoicedetail where depot_invoicedetail.invoice_id=depot_ininvoice.id and depot_invoicedetail.good_id=%s'%goods_id
                                })
            
            template_var['from_snap']=GoodHisSnap.objects.filter(good_id=goods_id,snap_date=form.cleaned_data['date_from'],from_type=1)
            template_var['to_snap']=GoodHisSnap.objects.filter(good_id=goods_id,snap_date=(form.cleaned_data['date_to']+datetime.timedelta(days=1)),from_type=1)
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'单据类型'),_(u'数量'),_(u'原单价'),_(u'相关单位'),_(u'经办人'),_(u'审核人'),_(u'日期'),_(u'总价'),_(u'仓库'),_(u'单据号')]
                ws=wb.add_sheet(_(u'物品出入明细'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for invoice in invoices:
                    ws.write(i,0,invoice.get_invoice_type_display(),style1)
                    ws.write(i,1,(invoice.get_num_prefix == '-') and (0-invoice.goods_sum) or invoice.goods_sum,style1)
                    ws.write(i,2,invoice.goods_price,style1)
                    ws.write(i,3,u"%s"%invoice.get_invoice_rel,style1)
                    ws.write(i,4,invoice.user.username,style1)
                    ws.write(i,5,invoice.confirm_user.username,style1)
                    ws.write(i,6,invoice.event_date.strftime('%Y-%m-%d'),style1)
                    ws.write(i,7,invoice.goods_sum_price,style1)
                    ws.write(i,8,invoice.warehouse_root.name,style1)
                    ws.write(i,9,invoice.invoice_code or '-',style1)
                    i+=1
                    
            
                    
                
                ws.col(0).width=0x1300
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'物品进出数据表').encode('gbk'))
                return response
        
        template_var['form']=form
        
    if extra_context is not None:
        template_var.update(extra_context)
        
    return render_to_response(template,template_var,context_instance=RequestContext(request))
'''
    物品出入统计
'''
def tongji_goods_inout_danju(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.select_related().get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.select_related().get(pk=org_id)
    InoutDanjuForm=make_InoutDanjuForm(org)
    
    if not request.GET.copy():
        template_var['form']=InoutDanjuForm()
    else:
        form=InoutDanjuForm(request.GET.copy())
        if form.is_valid():
            template_var['post']=True
            
            details=InvoiceDetail.objects.filter(invoice__org=org,invoice__status=2)
            if form.cleaned_data['date_from']:
                details=details.filter(invoice__event_date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                details=details.filter(invoice__event_date__lte=form.cleaned_data['date_to'])
                
            if form.cleaned_data['category']:
                categorys=form.cleaned_data['category'].get_descendants(include_self=True)
                details=details.filter(good__category__in=categorys)
                
            template_var['goods_count']=len(details.values('good').distinct())
            
            
            inout=set(request.REQUEST.getlist('inout'))
           
            in_arr=inout & set(['1000','1001','1002','1009'])
            out_arr=inout & set(['2000','2001','2002','2009'])
            
            in_str=','.join(in_arr) or 0
            out_str=','.join(out_arr) or 0

            #details.query.join(('depot_invoicedetail','depot_ininvoice','invoice_id','id'))
            #details.query.join(('depot_invoicedetail','depot_good','good_id','id'))
            to_nums_as_now=False
            if form.cleaned_data['date_to']<datetime.date.today():
                details=details.extra(
                                      select={
                                              'to_nums':"select depot_goodhissnap.nums from depot_goodhissnap where  \
                                                                                                    depot_goodhissnap.good_id=depot_invoicedetail.good_id and \
                                                                                                    depot_goodhissnap.snap_date='%s'"%(form.cleaned_data['date_to']+datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
                                              'from_nums':"select depot_goodhissnap.nums from depot_goodhissnap where  \
                                                                                                    depot_goodhissnap.good_id=depot_invoicedetail.good_id and \
                                                                                                    depot_goodhissnap.snap_date='%s'"%form.cleaned_data['date_from'].strftime('%Y-%m-%d')
                                            }
                                    )
            else:
                template_var['to_nums_as_now']=to_nums_as_now=True
                details=details.extra(
                                      select={
                                              'to_nums':"select depot_good.nums from depot_good where  \
                                                                                                    depot_good.id=depot_invoicedetail.good_id",
                                              'from_nums':"select depot_goodhissnap.nums from depot_goodhissnap where  \
                                                                                                    depot_goodhissnap.good_id=depot_invoicedetail.good_id and \
                                                                                                    depot_goodhissnap.snap_date='%s'"%form.cleaned_data['date_from'].strftime('%Y-%m-%d')
                                            }
                                    )
            
            template_var['good_details']=good_details=details.values('good','good__name','good__unit__unit','good__nums','to_nums','from_nums').annotate(
                    in_num=SumCase('num',case='depot_ininvoice.invoice_type in (%s)'%in_str,when=True),
                    in_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (%s)'%in_str,when=True),
                    out_num=SumCase('num',case='depot_ininvoice.invoice_type in (%s)'%out_str,when=True),
                    out_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (%s)'%out_str,when=True)
            )
            
            total_in = 0
            total_out = 0
            for detail in good_details:
                total_in = total_in + detail['in_price']
                total_out = total_out + detail['out_price']

            template_var['total_in'] = total_in
            template_var['total_out'] = total_out
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'物品'),_(u'物品单位'),_(u'期初库存'),_(u'入库数量'),_(u'出库数量'),_(u'期末库存'),_(u'入库总价'),_(u'入库均价'),_(u'出库总价'),_(u'出库均价')]
                ws=wb.add_sheet(_(u'物品出入查询'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for good_detail in good_details:
                    ws.write(i,0,good_detail['good__name'],style1)
                    ws.write(i,1,good_detail['good__unit__unit'] or '-',style1)
                    ws.write(i,2,good_detail['from_nums'] or '-',style1)
                    ws.write(i,3,good_detail['in_num'],style1)
                    ws.write(i,4,good_detail['out_num'],style1)
                    ws.write(i,5,good_detail['to_nums'] or '-',style1)
                    ws.write(i,6,good_detail['in_price'],style1)
                    ws.write(i,7,good_detail['in_num'] and good_detail['in_price']/good_detail['in_num'] or good_detail['in_num'],style1)
                    ws.write(i,8,good_detail['out_price'],style1)
                    ws.write(i,9,good_detail['out_num'] and good_detail['out_price']/good_detail['out_num'] or good_detail['out_num'],style1)
                    i+=1
                    
            
                    
                
                ws.col(0).width=0x1300
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'物品进出数据表').encode('gbk'))
                return response
            
        template_var['form']=form
        
    return render_to_response("tongji/goods_inout_danju.html",template_var,context_instance=RequestContext(request))
            
@page_template('tongji/auto_stock_log_index.html')            
def tongji_auto_stock_log(request,org_id,template="tongji/auto_stock_log.html",extra_context=None):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    if request.method=="GET":
        if request.GET:
            form=DateRangeForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s"%(reverse('tongji_auto_stock_log',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
       
        if form.is_valid():
            template_var['syncHis']=SyncHis.objects.filter(org=org,created_time__gt=form.cleaned_data['date_from'],created_time__lt=form.cleaned_data['date_to']).select_related()
                
        template_var['form']=form
        
        if extra_context is not None:
            template_var.update(extra_context)
        
    return render_to_response(template,template_var,context_instance=RequestContext(request))

def tongji_auto_stock_sum(request,org_id):
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
        
    if request.method=="GET":
        if request.GET:
            form=DateRangeForm(request.GET.copy())
        else:
            return HttpResponseRedirect("%s?date_from=%s&date_to=%s"%(reverse('tongji_auto_stock_sum',args=[org.uid]),datetime.date.today().replace(day=1),datetime.date.today()))
       
        if form.is_valid():
            pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]
            details=InvoiceDetail.objects.filter(invoice__org=org,invoice__status=2,invoice__content_type=ContentType.objects.get_for_model(pos_customer) ,
                                       invoice__object_id=pos_customer.pk)
            
            if form.cleaned_data['date_from']:
                details=details.filter(invoice__event_date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data['date_to']:
                details=details.filter(invoice__event_date__lte=form.cleaned_data['date_to'])
                
                
            template_var['goods_count']=len(details.values('good').distinct())
            
            template_var['good_details']=good_details=details.values('good','good__name','good__unit__unit','good__nums').annotate(
                    out_num=Sum('num'),
            )
            
            export_excel=request.GET.get('exportExcel',False)
            if export_excel:
                wb=_Wookbook()
                font=Font()
                font.name="Arial"
                font.bold=True
                font.shadow=True
                style=XFStyle()
                style.font=font
                
                heads=[_(u'物品'),_(u'物品单位'),_(u'当前库存'),_(u'出库数量')]
                ws=wb.add_sheet(_(u'自动出库物品总计'))
                j=0
                while j<len(heads):
                    ws.write(0,j,heads[j],style)
                    j+=1
                
                font1=Font()
                font1.name="Arial"
                style1=XFStyle()
                style1.font=font1
                i=1
                
                for good_detail in good_details:
                    ws.write(i,0,good_detail['good__name'],style1)
                    ws.write(i,1,good_detail['good__unit__unit'] or '-',style1)
                    ws.write(i,2,good_detail['good__nums'],style1)             
                    ws.write(i,3,good_detail['out_num'],style1)
                    i+=1
                    
                ws.col(0).width=0x1300
                
                response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'自动出库物品总计').encode('gbk'))
                return response    
        template_var['form']=form
        
    return render_to_response("tongji/tongji_auto_stock_sum.html",template_var,context_instance=RequestContext(request))

def tongji_goods_num_change(request,org_id):
    
    template_var={}
    
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['today']=datetime.date.today()
        
    if request.GET.has_key('keyword'):
        try:
            keyword=request.GET.get('keyword')
            lst=[{'name':goods.name,'category':goods.category.name,'id':goods.id} for goods in Goods.objects.filter(Q(name__icontains=keyword)|Q(abbreviation__icontains=keyword)|Q(code__icontains=keyword),org=org)[:5]]
            return HttpResponse(simplejson.dumps(lst), mimetype='application/json')
        except:
            print traceback.print_exc()    
    
    goods_id=request.GET.get('goods_id')
    if goods_id:
        template_var['goods']=Goods.objects.get(pk=goods_id,org=org)
        if request.GET.has_key('month'):
            template_var['mdate']=start=datetime.datetime.strptime(request.GET.get('month'),'%Y-%m').date()
        else:
            template_var['mdate']=start=template_var['today'].replace(day=1)
        end=datedelta(start, 1, 3)

        template_var['snaps']=GoodHisSnap.objects.filter(org=org,snap_date__range=(start,end+datetime.timedelta(-1)),good_id=goods_id,from_type=1)
        
    return render_to_response("tongji/tongji_goods_num_change.html",template_var,context_instance=RequestContext(request))

def get_snap_his(request,org_id):
    template_var={}
    
    try:
        org=Organization.objects.get(slug=org_id)
    except:
        org=Organization.objects.get(pk=org_id)
        
    start=datetime.datetime.strptime(request.GET.get('start'),'%Y-%m-%d').date()
    end=datetime.datetime.strptime(request.GET.get('end'),'%Y-%m-%d').date()
    goods_id=request.GET.get('goods_id')
        
    snaps=GoodHisSnap.objects.filter(org=org,snap_date__range=(start,end),good_id=goods_id,from_type=1)
    snap_details=GoodHisSnapDetail.objects.filter(org=org,snap_date__range=(start,end),good_id=goods_id,status=1)
    
    evnet_list=[]
    for day in daterange(start, end, include_end=False):
        day_snap=snaps.filter(snap_date=day)
        day_details=snap_details.filter(snap_date=day)
        
        for detail in day_details:
            evnet_list.append({'title':detail.description,'start':"%sT%s"%(detail.snap_date.strftime('%Y-%m-%d'),detail.snap_time.strftime('%H:%M:%S'))})
        
        if day_snap.exists():
            evnet_list.append({'title':'日自动计算数量为%s'%day_snap[0].nums,'start':'%sT04:00:00'%day_snap[0].snap_date.strftime('%Y-%m-%d')})
        
        #evnet_list.append({'title':'ddddd','start':''})
        
        
    return HttpResponse(simplejson.dumps(evnet_list), mimetype='application/json')

@transaction.commit_manually
def dppd(request,org_id,goods_id):
    try:
        template_var={}
    
        try:
            org=Organization.objects.get(slug=org_id)
        except:
            org=Organization.objects.get(pk=org_id)
            
        template_var['goods']=goods=Goods.objects.get(org=org,id=goods_id)    
        
        if request.method=="POST":
            template_var
            nums=float(request.POST['nums'])
            if nums!=goods.nums:
            
                warehouse=Warehouse.objects.filter(org=org)[0]
                invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),status=1,org=org,warehouse_root=warehouse,
                                            event_date=datetime.date.today(),invoice_type=9999,content_object=request.user,charger=request.user,
                                            user=request.user,confirm_user=request.user,remark=None)
            
                pancha=nums-goods.nums
    
    
                InvoiceDetail.objects.create(invoice=invoice,good=goods,warehouse=warehouse,warehouse_root=warehouse,
                                                     num1=pancha,unit1=goods.unit,price=goods.refer_price,num=pancha,avg_price=goods.refer_price,last_nums=pancha,total_price=goods.refer_price*pancha,
                                                     remark=None)
                    
                goods.nums+=pancha
                goods.save() 
                
                invoice.total_price=invoice.details.all().aggregate(sum_total_price=Sum('total_price'))['sum_total_price'] or 0
                ret=invoice.confirm(request.user)
                
                if ret!=2:
                    transaction.rollback()
                    return HttpResponse(ret)
                transaction.commit()
            template_var['success']=True
        response=render_to_response("tongji/dppd.html",template_var,context_instance=RequestContext(request))
        transaction.commit()
        return response
    except:
        transaction.rollback()
        print traceback.print_exc() 


@page_template('tongji/search_ruku_index.html')
def search_ruku(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = InvoiceDetail.objects.filter(invoice__org=org,invoice__invoice_type__in=(1000,1001),invoice__is_delete=0,invoice__status=2)

    startdate = request.GET.get("startdate")
    enddate = request.GET.get("enddate")
    invoice_code = request.GET.get("invoice_code")
    invoice_type = request.GET.get("invoice_type")
    supplier = request.GET.get("supplier")
    warehouse = request.GET.get("warehouse")
    good_code = request.GET.get("good_code")
    good_name = request.GET.get("good_name")

    if startdate:
        invoices = invoices.filter(invoice__event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(invoice__event_date__lte=enddate)
    if invoice_code:
        invoices = invoices.filter(invoice__invoice_code__icontains=invoice_code)
    if invoice_type:
        invoices = invoices.filter(invoice__invoice_type=invoice_type)
    if supplier:
        supplier = Supplier.objects.filter(name__icontains=supplier).values_list('id',flat=True)
        invoices = invoices.filter(invoice__object_id__in=supplier)
    if warehouse:
        invoices = invoices.filter(invoice__warehouse_root__id=warehouse)
    if good_code:
        invoices = invoices.filter(good__code__icontains=good_code)
    if good_name:
        invoices = invoices.filter(good__name__icontains=good_name)


    total = invoices.aggregate(Sum('total_price'),Sum('num'))
    invoices = invoices.extra(order_by=['-invoice__event_date','-invoice__invoice_code'])
    template_var['total'] = total
    template_var['invoices'] = invoices
    template_var['warehouses'] = warehouses = Warehouse.objects.filter(org=org)
    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/search_ruku.html",template_var,context_instance=RequestContext(request))


@page_template('tongji/search_chuku_index.html')
def search_chuku(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    invoices = InvoiceDetail.objects.filter(invoice__org=org,invoice__invoice_type__in=(2000,2001,2002),invoice__is_delete=0,invoice__status=2)

    startdate = request.GET.get("startdate")
    enddate = request.GET.get("enddate")
    invoice_code = request.GET.get("invoice_code")
    invoice_type = request.GET.get("invoice_type")
    customer = request.GET.get("customer")
    warehouse = request.GET.get("warehouse")
    good_code = request.GET.get("good_code")
    good_name = request.GET.get("good_name")

    if startdate:
        invoices = invoices.filter(invoice__event_date__gte=startdate)
    if enddate:
        invoices = invoices.filter(invoice__event_date__lte=enddate)
    if invoice_code:
        invoices = invoices.filter(invoice__invoice_code__icontains=invoice_code)
    if invoice_type:
        invoices = invoices.filter(invoice__invoice_type=invoice_type)
    if customer:
        customer = Customer.objects.filter(name__icontains=customer).values_list('id',flat=True)
        invoices = invoices.filter(invoice__object_id__in=customer)
    if warehouse:
        invoices = invoices.filter(invoice__warehouse_root__id=warehouse)
    if good_code:
        invoices = invoices.filter(good__code__icontains=good_code)
    if good_name:
        invoices = invoices.filter(good__name__icontains=good_name)

    total = invoices.aggregate(Sum('total_price'),Sum('num'))
    invoices = invoices.extra(order_by=['-invoice__event_date','-invoice__invoice_code'])

    template_var['total'] = total
    template_var['invoices'] = invoices
    template_var['warehouses'] = warehouses = Warehouse.objects.filter(org=org)
    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/search_chuku.html",template_var,context_instance=RequestContext(request))


@page_template('tongji/tongji_ruku_index.html')
def tongji_ruku(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    raw_sql = "SELECT depot_supplier.name,invoice_type,depot_good.name,depot_category.name,depot_good.standard,depot_unit.unit,SUM(total_price)/SUM(num),SUM(num),SUM(total_price) FROM (SELECT invoice_type,avg_price,num,depot_invoicedetail.total_price,good_id,object_id,unit1_id,event_date,depot_ininvoice.warehouse_root_id,depot_ininvoice.invoice_code FROM depot_invoicedetail LEFT JOIN depot_ininvoice ON depot_invoicedetail.invoice_id = depot_ininvoice.id  WHERE org_id = %d AND depot_ininvoice.status=2 AND (depot_ininvoice.invoice_type = 1000 OR depot_ininvoice.invoice_type = 1001) AND depot_ininvoice.is_delete = 0) as A LEFT JOIN depot_good ON A.good_id = depot_good.id LEFT JOIN depot_supplier ON A.object_id = depot_supplier.id LEFT JOIN depot_unit ON A.unit1_id = depot_unit.id LEFT JOIN depot_category ON depot_good.category_id = depot_category.id"%(org.id,) 

    extra_sql = []

    startdate = request.GET.get("startdate")
    enddate = request.GET.get("enddate")
    invoice_code = request.GET.get("invoice_code")
    invoice_type = request.GET.get("invoice_type")
    supplier = request.GET.get("supplier")
    warehouse = request.GET.get("warehouse")
    good_code = request.GET.get("good_code")
    good_name = request.GET.get("good_name")

    if startdate:
        extra_sql.append("A.event_date >= '%s'"%(startdate,)) 
    if enddate:
        extra_sql.append("A.event_date <= '%s'"%(enddate,)) 
    if invoice_code:
        extra_sql.append("A.invoice_code LIKE '%%%%%s%%%%'"%(invoice_code,))
    if invoice_type:
        extra_sql.append("A.invoice_type = %s"%(invoice_type,))
    if supplier:
        extra_sql.append("depot_supplier.name LIKE '%%%%%s%%%%'"%(supplier,))
    if warehouse:
        extra_sql.append("A.warehouse_root_id = %s"%(warehouse,))
    if good_code:
        extra_sql.append("depot_good.code LIKE '%%%%%s%%%%'"%(good_code,))
    if good_name:
        extra_sql.append("depot_good.name LIKE '%%%%%s%%%%'"%(good_name,))

    if extra_sql:
        extra_sql = ' AND '.join(extra_sql)

        sql = raw_sql + ' WHERE ' + extra_sql + " GROUP BY depot_good.id,depot_supplier.id,A.invoice_type ORDER BY A.event_date desc"
    else:
        sql = raw_sql + " GROUP BY depot_good.id,depot_supplier.id,A.invoice_type ORDER BY A.event_date desc"


    #total = invoices.aggregate(Sum('total_price'),Sum('num'))
    #template_var['total'] = total
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()

    all_num = 0
    all_price = 0
    for row in result:
        all_num += row[7]
        all_price += row[8]
    


    template_var['all_num'] = all_num
    template_var['all_price'] = all_price
    template_var['invoices'] = result
    template_var['warehouses'] = warehouses = Warehouse.objects.filter(org=org)


    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/tongji_ruku.html",template_var,context_instance=RequestContext(request))


@page_template('tongji/tongji_chuku_index.html')
def tongji_chuku(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    raw_sql = "SELECT depot_customer.name,invoice_type,depot_good.name,depot_category.name,depot_good.standard,depot_unit.unit,SUM(total_price)/SUM(num),SUM(num),SUM(total_price) FROM (SELECT invoice_type,avg_price,num,depot_invoicedetail.total_price,good_id,object_id,unit1_id,event_date,depot_ininvoice.warehouse_root_id,depot_ininvoice.invoice_code FROM depot_invoicedetail LEFT JOIN depot_ininvoice ON depot_invoicedetail.invoice_id = depot_ininvoice.id  WHERE org_id = %d AND depot_ininvoice.status=2 AND (depot_ininvoice.invoice_type = 2000 OR depot_ininvoice.invoice_type = 2001 OR depot_ininvoice.invoice_type = 2002) AND depot_ininvoice.is_delete = 0) as A LEFT JOIN depot_good ON A.good_id = depot_good.id LEFT JOIN depot_customer ON A.object_id = depot_customer.id LEFT JOIN depot_unit ON A.unit1_id = depot_unit.id LEFT JOIN depot_category ON depot_good.category_id = depot_category.id"%(org.id,) 

    extra_sql = []

    startdate = request.GET.get("startdate")
    enddate = request.GET.get("enddate")
    invoice_code = request.GET.get("invoice_code")
    invoice_type = request.GET.get("invoice_type")
    customer = request.GET.get("customer")
    warehouse = request.GET.get("warehouse")
    good_code = request.GET.get("good_code")
    good_name = request.GET.get("good_name")

    if startdate:
        extra_sql.append("A.event_date >= '%s'"%(startdate,)) 
    if enddate:
        extra_sql.append("A.event_date <= '%s'"%(enddate,)) 
    if invoice_code:
        extra_sql.append("A.invoice_code LIKE '%%%%%s%%%%'"%(invoice_code,))
    if invoice_type:
        extra_sql.append("A.invoice_type = %s"%(invoice_type,))
    if customer:
        extra_sql.append("depot_customer.name LIKE '%%%%%s%%%%'"%(customer,))
    if warehouse:
        extra_sql.append("A.warehouse_root_id = %s"%(warehouse,))
    if good_code:
        extra_sql.append("depot_good.code LIKE '%%%%%s%%%%'"%(good_code,))
    if good_name:
        extra_sql.append("depot_good.name LIKE '%%%%%s%%%%'"%(good_name,))

    if extra_sql:
        extra_sql = ' AND '.join(extra_sql)

        sql = raw_sql + ' WHERE ' + extra_sql + " GROUP BY depot_good.id,depot_customer.id,A.invoice_type ORDER BY A.event_date desc"
    else:
        sql = raw_sql + " GROUP BY depot_good.id,depot_customer.id,A.invoice_type ORDER BY A.event_date desc"


    #total = invoices.aggregate(Sum('total_price'),Sum('num'))
    #template_var['total'] = total
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()


    all_num = 0
    all_price = 0
    for row in result:
        all_num += row[7]
        all_price += row[8]
    
    template_var['all_num'] = all_num
    template_var['all_price'] = all_price
    template_var['invoices'] = result
    template_var['warehouses'] = warehouses = Warehouse.objects.filter(org=org)


    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/tongji_chuku.html",template_var,context_instance=RequestContext(request))


@page_template('tongji/dongtai_analysis_index.html')
def dongtai_analysis(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    raw_sql = "SELECT cost_categorypos.name,item_name,A.unit,AVG(A.price),SUM(A.total_price),SUM(A.num),AVG(A.cost) FROM (SELECT menuitem_id,zdate,unit,price,total_price,num,cost FROM cost_synchis LEFT JOIN cost_syncseq ON cost_syncseq.his_id = cost_synchis.id LEFT JOIN cost_syncseqdetail ON cost_syncseqdetail.seq_id = cost_syncseq.id WHERE org_id = %s) AS A INNER JOIN cost_menuitem ON A.menuitem_id = cost_menuitem.id LEFT JOIN cost_categorypos ON cost_menuitem.categoryPos_id = cost_categorypos.id"%(org.id,)

    extra_sql = []


    startdate = request.GET.get("startdate")
    enddate = request.GET.get("enddate")
    item_name = request.GET.get("item_name")


    if startdate:
        extra_sql.append("A.zdate >= '%s'"%(startdate,)) 
    if enddate:
        extra_sql.append("A.zdate <= '%s'"%(enddate,))
    if item_name:
        extra_sql.append("cost_menuitem.item_name LIKE '%%%%%s%%%%'"%(item_name.encode('utf-8'),)) 

    if extra_sql:
        reload(sys)
        sys.setdefaultencoding('utf8')
        extra_sql = ' AND '.join(extra_sql)

        sql = raw_sql + ' WHERE ' + extra_sql + " GROUP BY cost_menuitem.id ORDER BY A.zdate desc"
    else:
        sql = raw_sql + " GROUP BY cost_menuitem.id ORDER BY A.zdate desc"


    #total = invoices.aggregate(Sum('total_price'),Sum('num'))
    #template_var['total'] = total
    cursor = connection.cursor()
    cursor.execute(sql)
    result = list(cursor.fetchall())

    all_profit = 0
    all_price = 0
    all_num = 0
    for k,row in enumerate(result):

        all_price += row[4]

        profit = row[4] - row[6] * row[5]

        all_profit += profit

        all_num += row[5]

        profit_rate = profit/float(row[4])

        extra_tuple = (profit,profit_rate)

        result[k] = row + extra_tuple

    
    

    template_var['all_price'] = all_price
    template_var['all_profit'] = all_profit
    template_var['all_num'] = all_num
    template_var['invoices'] = result
    template_var['warehouses'] = warehouses = Warehouse.objects.filter(org=org)


    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/dongtai_analysis.html",template_var,context_instance=RequestContext(request))

@page_template('tongji/minus_stock_query_index.html')
def minus_stock_query(request,org_id,extra_context=None):
    template_var = {}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)

    goods = Goods.objects.filter(org=org,nums__lt=0)

    good_code = request.GET.get("good_code")
    good_name = request.GET.get("good_name")

    if good_code:
        goods = goods.filter(code__icontains=good_code)
    if good_name:
        goods = goods.filter(name__icontains=good_name)

    template_var['goods'] = goods
    if extra_context is not None:
        template_var.update(extra_context)

    return render_to_response("tongji/minus_stock_query.html",template_var,context_instance=RequestContext(request))