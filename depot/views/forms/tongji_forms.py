# -*- coding: utf-8 -*- 
from django import forms
from depot.models import Unit,Brand, Category, Goods, ConDepartment, Supplier,\
    Customer, Organization, Warehouse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import translation
from depot.views.forms import TreeSelect
from inventory.MACROS import INVOICE_TYPES
from django.forms.widgets import SelectMultiple, CheckboxInput
from itertools import chain
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import traceback
import datetime

def make_SearchDanjuForm(org_id):
    class SearchDanjuForm(forms.Form):
        def __init__(self, *args, **kwargs): 
            super(SearchDanjuForm, self).__init__(*args, **kwargs)
        
        invoice_code=forms.CharField(label=_(u'单据编号'),required=False,widget=forms.TextInput(attrs={'class':'span12'}))
        voucher_code=forms.CharField(label=_(u'凭证号'),required=False,widget=forms.TextInput(attrs={'class':'span12'}))
        result=forms.ChoiceField(label=_(u'结款状态'),required=False,choices=(('',_(u'所有')),(0,_(u'未结款')),(1,_(u'已结款'))),widget=forms.Select(attrs={'class':'span12'}))
        
        warehouse_root=forms.ModelChoiceField(label=_(u'仓库'),required=False,empty_label=_(u'所有仓库'),queryset=Warehouse.objects.filter(org=org_id,parent__isnull=True),widget=forms.Select(attrs={'class':'span12'}))
        date_from =forms.DateField(label=_(u'起始时间'),required=False,initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),required=False,initial=datetime.date.today(),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        
        invoice_type=forms.ChoiceField(label=_(u'单据类型'),choices=[('',_(u'所有类型'))]+INVOICE_TYPES,required=False,widget=forms.Select(attrs={'class':'span12'}))
        refer=forms.IntegerField(label=_(u'关联单位'),required=False,widget=forms.Select(attrs={'class':'span12'}))
        remark=forms.CharField(label=_(u'备注包含'),required=False,widget=forms.TextInput(attrs={'class':'span12'}))
        
        max_price=forms.IntegerField(required=False,widget=forms.TextInput(attrs={'class':'span5'}))
        min_price=forms.IntegerField(required=False,widget=forms.TextInput(attrs={'class':'span5'}))
        
    return SearchDanjuForm


'''
    领用Form
'''
def make_LingyongDanjuForm(org):
    class LingyongDanjuForm(forms.Form):
        def __init__(self, *args, **kwargs): 
            super(LingyongDanjuForm, self).__init__(*args, **kwargs)
            
        category=forms.ModelChoiceField(label=_(u'物品分类'),queryset=Category.objects.filter(org=org,is_global=True),required=False,widget=TreeSelect(attrs={'class':'span12'}),empty_label=_(u'全部分类'))
        conDepartment=forms.ModelChoiceField(label=_(u'领用部门'),queryset=ConDepartment.objects.filter(org=org,status=True),required=False,empty_label=_(u'所有部门'),widget=forms.Select(attrs={'class':'span12'})) 
        date_from =forms.DateField(label=_(u'起始时间'),required=False,initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),required=False,initial=datetime.date.today(),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)
            
    return LingyongDanjuForm


'''
    供货商Form
'''
def make_GonghuoshangDanjuForm(org):
    class GonghuoshangDanjuForm(forms.Form):
        def __init__(self, *args, **kwargs): 
            super(GonghuoshangDanjuForm, self).__init__(*args, **kwargs)
            
        category=forms.ModelChoiceField(label=_(u'物品分类'),queryset=Category.objects.filter(org=org,is_global=True),required=False,widget=TreeSelect(attrs={'class':'span12'}),empty_label=_(u'全部分类'))
        supplier=forms.ModelChoiceField(label=_(u'供应商'),queryset=Supplier.objects.filter(org=org,status=True),required=False,empty_label=_(u'所有供货商'),widget=forms.Select(attrs={'class':'span12'})) 
        date_from =forms.DateField(label=_(u'起始时间'),required=False,initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),required=False,initial=datetime.date.today(),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        remark=forms.CharField(widget=forms.Textarea(attrs={'style':'width:100%','rows':2}),required=False)
            
    return GonghuoshangDanjuForm

class XCheckboxSelectMultiple(SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<ul class="%s">'%final_attrs['class']]
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<li><label%s>%s %s</label></li>' % (label_for, rendered_cb, option_label))
        output.append(u'</ul>')
        return mark_safe(u'\n'.join(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_

'''
    In out单据
'''
def make_InoutDanjuForm(org):
    class InoutDanjuForm(forms.Form):
        def __init__(self, *args, **kwargs): 
            super(InoutDanjuForm, self).__init__(*args, **kwargs)
            
        category=forms.ModelChoiceField(label=_(u'物品分类'),queryset=Category.objects.filter(org=org,is_global=True),required=False,widget=TreeSelect(attrs={'class':'span12'}),empty_label=_(u'全部分类'))
        inout=forms.MultipleChoiceField(label=_(u'进出类型'),error_messages={'required':_(u'至少选择一个条件')},required=True,choices=INVOICE_TYPES,widget=XCheckboxSelectMultiple(attrs={'class':'inline'})) 
        date_from =forms.DateField(label=_(u'起始时间'),required=False,initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),required=False,initial=datetime.date.today(),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
                 
    return InoutDanjuForm


'''
    In out详细
'''
def make_InoutDanjuDetailForm(org):
    class InoutDanjuDetailForm(forms.Form):
        def __init__(self, *args, **kwargs): 
            super(InoutDanjuDetailForm, self).__init__(*args, **kwargs)

        goods_id=forms.IntegerField(required=True,error_messages={'required':_(u'请选择要查看的物品')},widget=forms.HiddenInput())
        goods_name=forms.CharField(label=_(u'物品名称'),required=True,error_messages={'required':_(u'请选择要查看的物品')},widget=forms.TextInput())
        date_from =forms.DateField(label=_(u'起始时间'),required=False,initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        date_to = forms.DateField(label=_(u'结束时间'),required=False,initial=datetime.date.today(),widget=forms.DateInput(attrs={'class':'span12','onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
        inout=forms.MultipleChoiceField(label=_(u'进出类型'),error_messages={'required':_(u'至少选择一个条件')},required=True,choices=INVOICE_TYPES,widget=XCheckboxSelectMultiple(attrs={'class':'inline'}))
        
    return InoutDanjuDetailForm

