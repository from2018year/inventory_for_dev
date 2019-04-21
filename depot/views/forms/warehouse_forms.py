# -*- coding: utf-8 -*- 
from django import forms
from depot.models import Unit,Brand, Category, Goods, ConDepartment, Supplier,\
    Customer, Organization, Warehouse, InvoiceDetail, Invoice, DetailRelBatch, \
    PayInvoice, SaleType
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import translation
from depot.views.forms import TreeSelect
from django.db.models import Q
from inventory.MACROS import INVOICE_STATUS
import datetime
import traceback

disday = datetime.timedelta(days=0)

'''
    调拨选择
'''
def make_InvoiceSelectDiaoboForm(org,user):
    class InvoiceSelectDiaoboForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(InvoiceSelectDiaoboForm, self).__init__(*args, **kwargs)
            queryset=user.get_warehouses(org)
            self.fields['from_warehouse'].queryset=self.fields['to_warehouse'].queryset=queryset
            if queryset.count()>1:
                self.fields['from_warehouse'].empty_label=_(u'所有仓库')
                self.fields['to_warehouse'].empty_label=_(u'所有仓库')
            
                
        date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        from_warehouse=forms.ModelChoiceField(label=_(u'源仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        to_warehouse=forms.ModelChoiceField(label=_(u'目标仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        
        
        def clean_date_to(self):
            return self.cleaned_data['date_to']+disday
    
    return InvoiceSelectDiaoboForm

'''
    一般单据选择
'''
def make_InvoiceSelectSimpleForm(org,user):
    class InvoiceSelectSimpleForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(InvoiceSelectSimpleForm, self).__init__(*args, **kwargs)
            queryset=user.get_warehouses(org)
            self.fields['warehouse'].queryset=queryset
            if queryset.count()>1:
                self.fields['warehouse'].empty_label=_(u'所有仓库')
                
                
        date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        warehouse=forms.ModelChoiceField(label=_(u'选择仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        status=forms.IntegerField(label=_(u'单据状态'),required=False,widget=forms.Select(choices=((10,_(u'全部')),(1,_(u'申请中')),(2,_(u'已审核')))))
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)

        
        def clean_date_to(self):
            return self.cleaned_data['date_to']+disday
    
    return InvoiceSelectSimpleForm


def make_InvoiceForm(org,user,invoice_type=0):
    class InvoiceForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):         
            super(InvoiceForm, self).__init__(*args, **kwargs)    
            self.fields['rels'].initial=self.instance.object_id
            if invoice_type==1001:
                self.fields['rels'].queryset=Supplier.objects.filter(org=org,status=1,pk__gt=0)
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="caigouruku_add")|Q(user_levels__permissions__codename="caigouruku_modify")|Q(om_orgs__superior=True)).distinct()
            elif invoice_type==1004:
                self.fields['rels'].queryset=Supplier.objects.filter(org=org,status=1,pk__gt=0)
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="caigoushenqing_add")|Q(user_levels__permissions__codename="caigoushenqing_modify")|Q(om_orgs__superior=True)).distinct()
            elif invoice_type==1000:
                del self.fields['rels']
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="chushiruku_add")|Q(user_levels__permissions__codename="chushiruku_modify")|Q(om_orgs__superior=True)).distinct()
            elif invoice_type==2000:
                self.fields['rels'].queryset=Supplier.objects.filter(org=org,status=1,pk__gt=0)
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="caigoutuihuo_add")|Q(user_levels__permissions__codename="caigoutuihuo_modify")|Q(om_orgs__superior=True)).distinct()

            elif invoice_type==2001:

                self.fields['rels'].queryset=ConDepartment.objects.filter(org=org,status=1,pk__gt=0)
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="lingyongchuku_add")|Q(user_levels__permissions__codename="lingyongchuku_modify")|Q(om_orgs__superior=True)).distinct()
                del self.fields['result']
            elif invoice_type==1002:   
                self.fields['rels'].queryset=ConDepartment.objects.filter(org=org,status=1,pk__gt=0)
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename='warehouse_write')|Q(user_levels__permissions__codename='warehouse_mamage')|Q(om_orgs__superior=True)).distinct()
                del self.fields['result']
            elif invoice_type==2002:
                self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
         
                pos_user=User.objects.get_or_create(username="pos-%s"%org.pk,password="!",email="no@this.user",defaults={'is_active':False})[0]
                pos_customer=Customer.objects.get_or_create(abbreviation='POS',org=org,defaults={'remark':_(u'自动生成'),'status':1,'name':_(u'自动出库')})[0]

                self.fields['sale_type'].label=_(u'销售类型')
                self.fields['sale_type'].queryset=SaleType.objects.filter(org=org)
                self.fields['sale_type'].empty_label=None
                
                if self.instance.pk and self.instance.user==pos_user:
                    self.fields['user'].queryset=User.objects.filter(id__in=[pos_user.pk])
                    self.fields['rels'].queryset=Customer.objects.filter(id__in=[pos_customer.pk])
                else:
                    self.fields['rels'].queryset=Customer.objects.filter(org=org,status=1,pk__gt=0)
                    self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="xiaoshouchuku_add")|Q(user_levels__permissions__codename="xiaoshouchuku_modify")|Q(om_orgs__superior=True)).distinct()
       
            elif invoice_type==10000:
                _queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
     
                self.fields['rels'].queryset=_queryset
                self.fields['rels'].initial=self.instance.object_id
                self.fields['rels'].label=_(u'目标仓库')
                self.fields['warehouse_root'].queryset=_queryset
                self.fields['warehouse_root'].label=_(u'源仓库')
                self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename='warehouse_write')|Q(user_levels__permissions__codename='warehouse_mamage')|Q(om_orgs__superior=True)).distinct()
            
 
            self.fields['user'].empty_label=None
            self.fields['user'].initial=user.pk
            self.fields['event_date'].initial=datetime.date.today()
            self.data.update({'invoice_type':invoice_type})
            self.fields['remark'].initial=self.instance.remark
     
        rels=forms.ModelChoiceField(queryset=[],widget=forms.Select(attrs={'class':'span12'}),empty_label=None,label=_(u'相关单位'))
        sstatus=forms.BooleanField(label=_(u'开始申请'),initial=True,required=False,help_text=_(u'不勾选可存为草稿'))
        warehouse_root=forms.ModelChoiceField(label=_(u'仓库'),empty_label=None,widget=forms.Select(attrs={'class':'span12'}),queryset=[])
        remark=forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'span12'}))
        
        status=forms.IntegerField(required=False)
        
        class Meta:
            model=Invoice
            exclude=('charger','content_type','object_id','total_price','org','sale_price','invoice_from')
            widgets={
               'invoice_code':forms.TextInput(attrs={'class':'span12','placeholder':_(u'自动生成')}),
               'voucher_code':forms.TextInput(attrs={'class':'span12'}),
               'event_date':forms.TextInput(attrs={'class':'span12','onClick':"WdatePicker()"}),
               'user':forms.Select(attrs={'class':'span12'}),
               'sale_type':forms.Select(attrs={'class':'span12'}),      
            }
            
        def clean_status(self):
            try:
                return self.data['sstatus'] and 1 or 0
            except:
                return 0
            
    return InvoiceForm
        
'''
    出入库清单
'''
def make_InvoiceDetailForm(org,user):
    class InvoiceDetailForm(forms.ModelForm):
        def __init__(self,*args,**kwargs):
            super(InvoiceDetailForm, self).__init__(*args, **kwargs)
            self.fields['warehouse'].empty_label=None
            queryset=Warehouse.get_queryset_descendants(user.get_warehouses(org),include_self=True)
            self.fields['warehouse'].queryset=queryset
            self.fields['warehouse'].initial=queryset.exists() and queryset[0].pk or None
            self.fields['total_price'].required=False
            
            if self.instance.pk:
                self.fields['good_text'].initial=self.instance.good.name
                
                if self.instance.good.unit_id:
                    choices=[]
                    choices.append((self.instance.good.unit_id,'%s'%self.instance.good.unit))
                    for unit in self.instance.good.units():
                        choices.append((unit.pk,'%s'%unit))
                    self.fields['unit1'].widget.choices=choices
                
            
            
        good_text=forms.CharField(max_length=100,widget=forms.TextInput(attrs={'class':'good_text','style':'width:95%','placeholder':_(u'点击这里添加物品')}))
        #total_price=forms.FloatField(widget=forms.HiddenInput(attrs={'class':'good_total'}),required=False)
        unit1=forms.IntegerField(required=False,label=_(u'单位'),widget=forms.Select(attrs={'style':'width:70px'},choices=(('',_(u'单位')),)))
        
        class Meta:
            model=InvoiceDetail
            widgets={
                'good':forms.HiddenInput(attrs={'class':'good_rel'}),
                'warehouse':TreeSelect(attrs={'style':'width:95%'}),
                'shelf_life':forms.TextInput(attrs={'style':'width:60px'}),
                'shelf_life_type':forms.Select(attrs={'style':'width:80px'}),
                'price':forms.TextInput(attrs={'style':'width:60px','class':'price'}),
                'num1':forms.TextInput(attrs={'style':'width:60px','class':'num'}),
                'total_price':forms.TextInput(attrs={'style':'width:60px','readonly':'readonly','class':'good_total'}),
            }
            
        def clean_num1(self):
            if self.cleaned_data['num1']>0:
                return self.cleaned_data['num1']
            raise forms.ValidationError(_(u'请填写正确的数值'))
        
        def clean_unit1(self):
            try:
                return Unit.objects.get(pk=self.cleaned_data['unit1'])
            except:
                return None
        
        
    return InvoiceDetailForm



'''
    退货清单
'''
def make_InvoiceTuiDetailForm(org,user):
    class InvoiceTuiDetailForm(forms.ModelForm):
        def __init__(self,*args,**kwargs):
            super(InvoiceTuiDetailForm, self).__init__(*args, **kwargs)
            #self.fields['warehouse'].empty_label=None
            #queryset=Warehouse.get_queryset_descendants(user.get_warehouses(org),include_self=True)
            #self.fields['warehouse'].queryset=queryset
            #self.fields['warehouse'].initial=queryset.exists() and queryset[0].pk or None
            self.fields['total_price'].required=False
       
            if self.instance.pk:
                self.fields['good_text'].initial=self.instance.good.name
                
                if self.instance.good.unit_id:
                    choices=[]
                    choices.append((self.instance.good.unit_id,'%s'%self.instance.good.unit))
                    for unit in self.instance.good.units():
                        choices.append((unit.pk,'%s'%unit))
                    self.fields['unit1'].widget.choices=choices
                rels=DetailRelBatch.objects.filter(from_batch=self.instance,level=True)
                if rels.exists():
                    self.fields['batch_code'].initial=rels[0].to_batch.batch_code
                    self.fields['batch_rel'].initial=rels[0].to_batch_id
                    
           
                    
            
        good_text=forms.CharField(max_length=100,widget=forms.TextInput(attrs={'class':'good_text','style':'width:95%','placeholder':_(u'点击这里添加物品')}))
        #total_price=forms.FloatField(widget=forms.HiddenInput(attrs={'class':'good_total'}),required=False)
        unit1=forms.IntegerField(required=False,label=_(u'单位'),widget=forms.Select(attrs={'style':'width:70px'},choices=(('',_(u'单位')),)))
        batch_code=forms.CharField(label=_(u'批次编号'),required=False,widget=forms.TextInput(attrs={'style':'width:95%','readonly':'readonly','class':'good_batch'}))
        batch_rel=forms.ModelChoiceField(queryset=InvoiceDetail.objects.all(),widget=forms.HiddenInput(attrs={'class':'batch_rel'}),required=False)
        
        class Meta:
            model=InvoiceDetail
            widgets={
                'good':forms.HiddenInput(attrs={'class':'good_rel'}),
                'price':forms.TextInput(attrs={'style':'width:60px','class':'price'}),
                'num1':forms.TextInput(attrs={'style':'width:60px','class':'num'}),
                'total_price':forms.TextInput(attrs={'style':'width:60px','readonly':'readonly','class':'good_total'}),
            }
            
            
        def clean_num1(self):
            if self.cleaned_data['num1']>0:
                return self.cleaned_data['num1']
            raise forms.ValidationError(_(u'请填写正确的数值'))
        
        def clean_unit1(self):
            try:
                return Unit.objects.get(pk=self.cleaned_data['unit1'])
            except:
                return None
        
        
    return InvoiceTuiDetailForm

'''
    查询物品form
'''
def make_SelectGoodsForm(org,user):
    class SelectGoodsForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(SelectGoodsForm,self).__init__(*args, **kwargs)
            if not Category.objects.filter(org=org.get_root_org()).count():
                Category.objects.get_or_create(parent__isnull=True,org=org.get_root_org(),defaults={'name':_(u'全部分类')})
        warehouse=forms.ModelChoiceField(label=_(u'选择货架'),empty_label=_(u'所有货架'),queryset=Warehouse.objects.none(),required=False,widget=TreeSelect(attrs={'style':'width:164px'}))    
        keyword=forms.CharField(label=_(u'关键字'),required=False,widget=forms.TextInput(attrs={"class":"input-medium",'placeholder':_(u'物品名称/助查码/编号')}))
        category=forms.ModelChoiceField(label=_(u'选择分类'),empty_label=None,queryset=Category.objects.get(org=org,parent__isnull=True).get_descendants(include_self=True).filter(status=1),required=False,widget=TreeSelect(attrs={'style':'width:164px'}))
        
    return SelectGoodsForm

'''
    查询相关采购单据
'''
class SelectInvoicesForm(forms.Form):
    event_date=forms.DateField(label=_(u'单据日期'),required=False,widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    keyword=forms.CharField(label=_(u'关键字'),required=False,widget=forms.TextInput(attrs={"class":"input-medium",'placeholder':_(u'单据编/凭证号/制单人/审核人/经办人')}))

'''
退料查询
'''
def make_InvoiceTuiSimpleForm(org,user):
    class InvoiceTuiSimpleForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(InvoiceTuiSimpleForm, self).__init__(*args, **kwargs)
            queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
            self.fields['warehouse'].queryset=queryset
            if queryset.count()>1:
                self.fields['warehouse'].empty_label=_(u'所有仓库')
   
        date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        warehouse=forms.ModelChoiceField(label=_(u'选择仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        supplier=forms.ModelChoiceField(label=_(u'供货商'),empty_label=_(u'所有供货商'),queryset=Supplier.objects.filter(org=org,status=1),required=False)
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)
        
        def clean_date_to(self):
            return self.cleaned_data['date_to']+disday
    
    return InvoiceTuiSimpleForm

'''
领用查询
'''
def make_InvoiceConSimpleForm(org,user):
    class InvoiceConSimpleForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(InvoiceConSimpleForm, self).__init__(*args, **kwargs)
            queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
            self.fields['warehouse'].queryset=queryset
            if queryset.count()>1:
                self.fields['warehouse'].empty_label=_(u'所有仓库')
   
        date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        warehouse=forms.ModelChoiceField(label=_(u'选择仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        conDepartment=forms.ModelChoiceField(label=_(u'领用部门'),empty_label=_(u'所有部门'),queryset=ConDepartment.objects.filter(org=org,status=1),required=False)
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)
        
        def clean_date_to(self):
            return self.cleaned_data['date_to']+disday
    
    return InvoiceConSimpleForm


'''
    退料入库清单
'''
def make_InvoiceTuiKuDetailForm(org,user):
    class InvoiceTuiKuDetailForm(forms.ModelForm):
        def __init__(self,*args,**kwargs):
            super(InvoiceTuiKuDetailForm, self).__init__(*args, **kwargs)
            #self.fields['warehouse'].empty_label=None
            #queryset=Warehouse.get_queryset_descendants(user.get_warehouses(org),include_self=True)
            #self.fields['warehouse'].queryset=queryset
            #self.fields['warehouse'].initial=queryset.exists() and queryset[0].pk or None
            self.fields['price'].required=False
            self.fields['total_price'].required=False
            
            
            if self.instance.pk:
                self.fields['good_text'].initial=self.instance.good.name
                
                if self.instance.good.unit_id:
                    choices=[]
                    choices.append((self.instance.good.unit_id,'%s'%self.instance.good.unit))
                    for unit in self.instance.good.units():
                        choices.append((unit.pk,'%s'%unit))
                    self.fields['unit1'].widget.choices=choices
            
        good_text=forms.CharField(max_length=100,widget=forms.TextInput(attrs={'class':'good_text','style':'width:95%','placeholder':_(u'点击这里添加物品')}))
        #total_price=forms.FloatField(widget=forms.HiddenInput(attrs={'class':'good_total'}),required=False)
        unit1=forms.IntegerField(required=False,label=_(u'单位'),widget=forms.Select(attrs={'style':'width:70px'},choices=(('',_(u'单位')),)))
        batch_rel=forms.ModelChoiceField(queryset=InvoiceDetail.objects.all(),widget=forms.HiddenInput(attrs={'class':'batch_rel'}),required=False)
        
        class Meta:
            model=InvoiceDetail
            widgets={
                'good':forms.HiddenInput(attrs={'class':'good_rel'}),
                'price':forms.TextInput(attrs={'style':'width:60px','class':'price'}),
                'num1':forms.TextInput(attrs={'style':'width:60px','class':'num'}),
                'total_price':forms.TextInput(attrs={'style':'width:60px','readonly':'readonly','class':'good_total'}),
            }
            
        def clean_num1(self):
            if self.cleaned_data['num1']>0:
                return self.cleaned_data['num1']
            raise forms.ValidationError(_(u'请填写正确的数值'))
        
        def clean_unit1(self):
            try:
                return Unit.objects.get(pk=self.cleaned_data['unit1'])
            except:
                return None
        
        
    return InvoiceTuiKuDetailForm




'''
    销售form
'''
def make_InvoiceSaleSimpleForm(org,user):
    class InvoiceSaleSimpleForm(forms.Form):
        def __init__(self,*args,**kwargs):
            super(InvoiceSaleSimpleForm, self).__init__(*args, **kwargs)
            queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
            self.fields['warehouse'].queryset=queryset
            if queryset.count()>1:
                self.fields['warehouse'].empty_label=_(u'所有仓库')
   
        date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        warehouse=forms.ModelChoiceField(label=_(u'选择仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
        customer=forms.ModelChoiceField(label=_(u'客户'),empty_label=_(u'所有客户'),queryset=Customer.objects.filter(org=org,status=1),required=False)
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)
        
        
        def clean_date_to(self):
            return self.cleaned_data['date_to']+disday
    
    return InvoiceSaleSimpleForm

class InvoiceQueryForm(forms.Form):
    def __init__(self,*args,**kwargs):
        super(InvoiceQueryForm,self).__init__(*args, **kwargs)

    date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    warehouse=forms.ModelChoiceField(label=_(u'选择仓库'),empty_label=None,required=False,queryset=Warehouse.objects.none())
    remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)


class FukuandanAddForm(forms.ModelForm):
    def __init__(self,org,user,invoice_type=0,*args, **kwargs):
        super(FukuandanAddForm, self).__init__(*args, **kwargs)    
        self.fields['user'].queryset=User.objects.filter(om_orgs__org=org).filter(Q(user_levels__permissions__codename="fukuandan_add")|Q(user_levels__permissions__codename="fukuandan_modify")|Q(om_orgs__superior=True)).distinct()
        self.fields['invoice_from'].label=_(u'单据来源')
        self.fields['already_pay'].widget.attrs['readonly'] = True
        self.fields['rest_pay'].widget.attrs['readonly'] = True
        self.fields['invoice_code'].widget.attrs['placeholder']= _(u'自动生成')
        self.fields['event_date'].initial = datetime.date.today()
        self.fields['warehouse_root'].queryset=user.get_warehouses(org,['warehouse_write','warehouse_mamage'])
        self.fields['user'].empty_label=None
        self.fields['user'].initial=user.pk
        self.fields['rels'].initial=self.instance.object_id

        if invoice_type == 3000:
            self.fields['rels'].queryset=Supplier.objects.filter(org=org,status=1,pk__gt=0)
            self.fields['rels'].label=_(u'供应商')
        elif invoice_type == 3001:
            self.fields['rels'].queryset=Customer.objects.filter(org=org,status=1,pk__gt=0)
            self.fields['rels'].label=_(u'客户')
            self.fields['already_pay'].label=_(u'已收款')
            self.fields['rest_pay'].label=_(u'未收款')
            self.fields['total_pay'].label=_(u'应收款')


    rels=forms.ModelChoiceField(queryset=[],widget=forms.Select(attrs={'class':'span12'}),empty_label=None,label=_(u'相关单位'))





    class Meta:
        model=PayInvoice
        exclude=('charger','org','content_type','object_id','invoice_type')
        widgets={
                'invoice_from':forms.TextInput(attrs={'readonly':True}),
                'event_date':forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()})
            }
    

