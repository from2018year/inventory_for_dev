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
from depot.models import Organization, InvoiceDetail
from inventory.common import *
from django.db.models import Q,Sum,Count
from django.forms.models import modelformset_factory, inlineformset_factory
from caiwu.models import FundsDayHis, FundsCategory
from caiwu.views.forms.chengben_form import make_FundsDayHisForm,make_FundsCategoryForm
from django.utils import simplejson
from django.contrib.auth.models import User
from depot.views.base import require_pos_config
import logging
import traceback
from inventory.common import  _Wookbook
from pyExcelerator.Formatting import Font
from pyExcelerator.Style import XFStyle

@login_required(login_url="/")
@require_pos_config
def caiwu_main(request,org_id):
    try:
        template_var={}
        try:
            template_var['org']=org=Organization.objects.get(slug=org_id)
        except:
            template_var['org']=org=Organization.objects.get(pk=org_id)
        template_var['org']=org
        
        #om=OrgsMembers.objects.get(user=request.user,org=org)
        request.session['org_id']=org_id
        request.session['org']=org
        request.session['root_org']=org.get_root_org()
        
        return render_to_response("caiwu_main.html",template_var,context_instance=RequestContext(request))
        #return render_to_response("org_backstage.html",template_var,context_instance=RequestContext(request))
    except:
        print traceback.print_exc()
        
        
def zijin_fenxi(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    
    r_day=request.GET.get('r_day',None)
 
    try:
        today=datetime.datetime.strptime(r_day,'%Y-%m').date()
    except:
        try:
            today=datetime.datetime.strptime(r_day,'%Y-%m-%d').date()
        except:
            today=datetime.date.today() 
   
    first_day=today.replace(day=1)
    last_day=datedelta(first_day, 1, 3).date()
    day_array=[]
    template_var['day']=first_day
    template_var['prev']=datedelta(first_day, -1, 3).date()
    template_var['next']=last_day
    
    for day in daterange(first_day,last_day):
        day_array.append(day)
        FundsDayHis.objects.get_or_create(date=day,org=org,category=None,defaults={'amount':0})
        
    #列出1个月所有条目,根据 date和category聚合
    his=FundsDayHis.objects.filter(org=org,date__gte=first_day,date__lt=last_day).values('date','category').annotate(sum=Sum('amount'))
    
    #列出1个月内category不为空的所有条目，根据catergory聚合
    total=FundsDayHis.objects.filter(category__isnull=False,org=org,date__gte=first_day,date__lt=last_day).values('category').annotate(sum=Sum('amount')).order_by('category__parent__ftype','id')
    
    #big_categorys收入支出2个条目，以及其子分类的个数
    template_var['big_categorys']=big_categorys=FundsCategory.objects.filter(org=org,parent__isnull=True).annotate(children_count=Count('children')).order_by('id')
    
    #列出子分类
    template_var['small_categorys']=small_categorys=FundsCategory.objects.filter(org=org,parent__in=big_categorys).order_by('parent','id')
    
    template_var['in_category']=FundsCategory.objects.filter(org=org,parent__in=big_categorys,parent__ftype=1).order_by('parent','id')
    template_var['out_category']=FundsCategory.objects.filter(org=org,parent__in=big_categorys,parent__ftype=2).order_by('parent','id')
    
    small_category_ids=list(small_categorys.values_list('id',flat=True))

    '''
    '    组合数据以显示
    '''
    datas=[]
    for day in day_array:
        data=[]
        for category_id in small_category_ids:
            data.append([category_id,None])
        data.append(['',None])
        datas.append(data)
        
    for h in his:
        day_index=day_array.index(h['date'])
        try:
            category_index=small_category_ids.index(h['category'])
        except:
            category_index=len(small_category_ids)
        
        datas[day_index][category_index][1]=h['sum']
    
    #增加月底总结
    category_total_data=[]
    category_total_data.append([day,0])
    
    for category_id in small_category_ids:
        category_total_data.append([category_id,0])
    
    month_total=0
    for data in total:
        category_index=small_category_ids.index(data['category'])
        category_total_data[category_index+1][1]=data['sum']
        month_total+=(data['sum'] or 0)
    category_total_data.append([day,FundsDayHis.objects.filter(category__isnull=True,org=org,date__gte=first_day,date__lt=last_day).aggregate(sum=Sum('amount'))['sum']])
      
    template_var['day_data']=zip(day_array,datas)
    template_var['category_total_data']=category_total_data
    
    #组合图表数据
    
    
    _last_day=datedelta(last_day, -1, 1)#每月的最后一天
    #print big_categorys.values("id","name").annotate(sum=SumCase('children__funds__amount',case="`date` between '%s' and '%s'"%(first_day.strftime('%Y-%m-%d'),_last_day.strftime('%Y-%m-%d')),when=True)).query
    category_datas=[]
    for big_category in big_categorys.values("id","name").annotate(sum=SumCase('children__funds__amount',case="`date` between '%s' and '%s'"%(first_day.strftime('%Y-%m-%d'),_last_day.strftime('%Y-%m-%d')),when=True)):
        #print '0000',big_category,month_total,big_category['sum'],round(100*(big_category['sum'] or 0)/month_total or 0,2)
        category_data={'y':month_total and round(100*(big_category['sum'] or 0)/month_total or 0,2),'name':big_category['name'],
                       'categorys':small_categorys.filter(parent=big_category['id']).values_list('name',flat=True),
                       'data':[(sum and month_total) and round(sum*100/month_total,2) or 0 for sum in small_categorys.filter(parent=big_category['id']).annotate(sum=SumCase('funds__amount',case="`date` between '%s' and '%s'"%(first_day.strftime('%Y-%m-%d'),_last_day.strftime('%Y-%m-%d')),when=True)).values_list('sum',flat=True)]}
        
        category_datas.append(category_data)
        

    template_var['category_datas']=category_datas
    template_var['big_category_names']=big_categorys.values_list('name',flat=True)

    export_excel=request.GET.get('exportExcel',False)
    if export_excel:
        wb=_Wookbook()
        font=Font()
        font.name="Arial"
        font.bold=True
        font.shadow=True
        style=XFStyle()
        style.font=font
        
        
        ws=wb.add_sheet(_(u'进出账目统计'))
        j=0
        
        ws.write(0,0,_(u'日期'),style)
        j=1
        for big_c in small_categorys:
            ws.write(0,j,unicode(big_c),style)
            j+=1
        ws.write(0,j,_(u'合计'),style)
        
        font1=Font()
        font1.name="Arial"
        style1=XFStyle()
        style1.font=font1
        i=1
        
        for dayy,datas in template_var['day_data']:
            
            j=0
            ws.write(i,j,str(dayy),style)
            j+=1
            for cat,data in datas:
                if data:
                    ws.write(i,j,data,style)
                j+=1
            i+=1
        
        ws.write(i,0,_(u'合计'),style)
        j=1
        isfirst=True
        for dayy,total in category_total_data:
            if isfirst:
                isfirst=False
                continue 
            ws.write(i,j,total,style)
            j+=1
        ws.col(0).width=0x1300
        ws.col(1).width=0x1000
        ws.col(2).width=0x1400
        ws.col(8).width=0x1000
        ws.col(9).width=0x1600
        
        response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'单据数据表').encode('gbk'))
        return response
    
    return render_to_response("zijin_fenxi.html",template_var,context_instance=RequestContext(request))


'''
    编辑财务
'''
def caiwu_edit_zijin(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    date_str=request.GET.get('date_str')
    day=datetime.datetime.strptime(date_str,'%Y-%m-%d').date()
    category_id=request.GET.get('category_id')
    template_var['category']=category=FundsCategory.objects.get(pk=category_id)
    

    if category.ftype==3:
        fundhis_set=modelformset_factory(FundsDayHis,form=make_FundsDayHisForm(org_id,day,category_id,request.user),exclude=('modify_time','created_time'),extra=1,can_delete=True)
    else:
        fundhis_set=modelformset_factory(FundsDayHis,form=make_FundsDayHisForm(org_id,day,category_id,request.user),exclude=('modify_time','created_time'),extra=0,can_delete=True)
    queryset=FundsDayHis.objects.filter(org=org,date=day,category_id=category_id)
    
    if request.method=="GET":
        template_var['formset']=fundhis_set(queryset=queryset)
    else:

        formset=fundhis_set(request.POST.copy(),queryset=queryset)
        if formset.is_valid():
            try:
                #formset.save()
                
                #计算总价变化
                days=[]
                for form in formset.forms:
                    if  form.changed_data:
                        h=form.save(commit=False)
                        if form['DELETE'].value():
                            h.delete()
                        else:
                            h.date=day
                            h.save()
                        
                FundsDayHis.update_day_amount(org, day)
                
                if request.is_ajax():
                    return HttpResponse("1")
            except:
                print traceback.print_exc()
    
        else:
            if request.is_ajax():
                formset_error_list=[]
                
                        
                for _form in formset.forms:
                    _form_error_dict={}
                    if _form.errors:
                        for error in _form.errors:
                            e=_form.errors[error]
                            _form_error_dict[_form.prefix+'-'+error]=unicode(e)
                            
                    formset_error_list.append(_form_error_dict)
                
                return HttpResponseBadRequest(simplejson.dumps({
                                    'formset_error_list':formset_error_list}),mimetype='application/json')
                
        template_var['formset']=formset
    return render_to_response("caiwu_edit_zijin.html",template_var,context_instance=RequestContext(request))
        
        
'''
    收支大分类
'''
def zijin_category1(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    category_set=inlineformset_factory(Organization,FundsCategory,form=make_FundsCategoryForm(org_id,level=1),extra=1,exclude=('status'),can_delete=True)
    queryset=FundsCategory.objects.select_related().filter(status__gte=0,org=org,parent__isnull=True).annotate(count=Count('children__funds'))
    
    if request.method=="GET":
        template_var['formset']=formset=category_set(instance=org,queryset=queryset)
    else:
        formset=category_set(request.POST.copy(),instance=org,queryset=queryset)
        if formset.is_valid():
            formset.save()
            template_var['formset']=category_set(instance=org,queryset=FundsCategory.objects.select_related().filter(status__gte=0,org=org,parent__isnull=True).annotate(count=Count('children__funds')))
        else:
            template_var['formset']=formset
    
    return render_to_response("zijin_category1.html",template_var,context_instance=RequestContext(request))



'''
    收支大分类
'''
def zijin_category2(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['fundsCategory']=fundsCategory=FundsCategory.objects.get(pk=request.GET.get('category_id'))
    
    category_set=inlineformset_factory(FundsCategory,FundsCategory,form=make_FundsCategoryForm(org_id,level=2,parent=fundsCategory),extra=1,exclude=('status'),can_delete=True)
    queryset=FundsCategory.objects.select_related().filter(status__gte=0,org=org,parent=fundsCategory).annotate(count=Count('funds'))
    
    if request.method=="GET":
        template_var['formset']=formset=category_set(instance=fundsCategory,queryset=queryset)
    else:
        formset=category_set(request.POST.copy(),instance=fundsCategory,queryset=queryset)
        if formset.is_valid():
            formset.save()
            template_var['formset']=category_set(instance=fundsCategory,queryset=FundsCategory.objects.select_related().filter(status__gte=0,org=org,parent=fundsCategory).annotate(count=Count('funds')))
            template_var['success']=True
        else:
            template_var['formset']=formset
    
    return render_to_response("zijin_category2.html",template_var,context_instance=RequestContext(request))


'''
    历史分析
    1，POS的日销售情况
    2，总资金的月情况
'''
def zijin_his(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    
    #找出最早的有POS销售数据的
    his=FundsDayHis.objects.filter(category=3,org=org).order_by('created_time')
    
    if his.exists():
        oldest_date=his[0].date
        day_funds=FundsDayHis.objects.filter(org=org,category=3,date__gte=oldest_date).values_list('date').annotate(sum=Sum('amount')).order_by('date')
        print day_funds
        s=[]
        for day_fund in day_funds:
            s.append([time.mktime(day_fund[0].timetuple())*1000,day_fund[1]])
        print '%s'%s    
        template_var['datas']='%s'%s
    else:
        template_var['empty']=True
    return render_to_response("zijin_his.html",template_var,context_instance=RequestContext(request))
    
    
def lirun_fenxi(request,org_id):
    template_var={}
    try:
        template_var['org']=org=Organization.objects.get(slug=org_id)
    except:
        template_var['org']=org=Organization.objects.get(pk=org_id)
    template_var['org']=org
    
    r_day=request.GET.get('r_day',None)
 
    try:
        today=datetime.datetime.strptime(r_day,'%Y-%m').date()
    except:
        try:
            today=datetime.datetime.strptime(r_day,'%Y-%m-%d').date()
        except:
            today=datetime.date.today() 
   
    first_day=today.replace(day=1)
    last_day=datedelta(first_day, 1, 3).date()

    template_var['day']=first_day
    template_var['prev']=datedelta(first_day, -1, 3).date()
    template_var['next']=last_day
    
    invoicedetails=InvoiceDetail.objects.filter(invoice__org=org,invoice__status=2,
                                         invoice__event_date__gte=first_day,invoice__event_date__lt=last_day)
    
    
    template_var['datas']=good_details=invoicedetails.values('good','good__name','good__unit__unit','good__nums').annotate(
                    in_num=SumCase('num',case='depot_ininvoice.invoice_type in (1000,1001)',when=True),
                    in_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (1000,1001)',when=True),
                    out_num=SumCase('num',case='depot_ininvoice.invoice_type in (2002)',when=True),
                    out_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (2002)',when=True),
                    chenben=SumCase('chenben_price',case='depot_ininvoice.invoice_type in (2002)',when=True)
    )
    
    template_var['agg']=agg=invoicedetails.aggregate(
                    in_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (1000,1001)',when=True),
                    out_price=SumCase('total_price',case='depot_ininvoice.invoice_type in (2002)',when=True),
                    chenben=SumCase('chenben_price',case='depot_ininvoice.invoice_type in (2002)',when=True)
    )
    if good_details:
        export_excel=request.GET.get('exportExcel',False)
        if export_excel:
            wb=_Wookbook()
            font=Font()
            font.name="Arial"
            font.bold=True
            font.shadow=True
            style=XFStyle()
            style.font=font
        
        
            heads=[_(u'物品'),_(u'物品单位'),_(u'当前库存'),_(u'入库数量'),_(u'入库总价'),_(u'入库均价'),_(u'销售数量'),_(u'销售总价'),_(u'销售均价'),_(u'销售利润')]
            ws=wb.add_sheet(_(u'物品利润分析'))
            j=0
            while j<len(heads):
                ws.write(0,j,heads[j],style)
                j+=1
        
            font1=Font()
            font1.name="Arial"
            style1=XFStyle()
            style1.font=font1
            i=1
        
            font1=Font()
            font1.name="Arial"
            style1=XFStyle()
            style1.font=font1
            i=1
        
            for good_detail in good_details:
                ws.write(i,0,good_detail['good__name'],style1)
                ws.write(i,1,good_detail['good__unit__unit'] or '-',style1)
                ws.write(i,2,good_detail['good__nums'],style1)
                ws.write(i,3,good_detail['in_num'],style1)
                ws.write(i,4,good_detail['in_price'],style1)
                ws.write(i,5,good_detail['in_num'] and good_detail['in_price']/good_detail['in_num'] or good_detail['in_num'],style1)
                ws.write(i,6,good_detail['out_num'],style1)
                ws.write(i,7,good_detail['out_price'],style1)
                ws.write(i,8,good_detail['out_num'] and good_detail['out_price']/good_detail['out_num'] or good_detail['out_num'],style1)
            
                ws.write(i,9,good_detail['out_price']-good_detail['chenben'],style1)
                i+=1
            
    
            ws.write(i,0,_(u'物品合计'),style1)  
            ws.write(i,4,agg['in_price'],style1)  
            ws.write(i,7,agg['out_price'],style1)
            ws.write(i,9,agg['out_price']-agg['chenben'],style1)
        
            ws.col(0).width=0x1300
        
            response=HttpResponse(wb.save_stream(),mimetype='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s.xls'%(_(u'物品利润分析').encode('gbk'))
            return response
    
    return render_to_response("lirun_fenxi.html",template_var,context_instance=RequestContext(request))