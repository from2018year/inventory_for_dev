# -*- coding: utf-8 -*- 
from django import forms
from depot.models import Unit,Brand, Category, Goods, ConDepartment, Supplier,\
    Customer, SupplierGroup
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import translation
from depot.views.forms import TreeSelect
import traceback
      
'''
    物品单位
'''
class UnitForm(forms.ModelForm):
    
    class Meta:
        model=Unit
        widgets={
            'unit':forms.TextInput(attrs={'class':'input-small'}),
        }
        
'''
    辅助单位
'''
def make_AuxiliaryUnitForm(org,unit):
    class AuxiliaryUnitForm(forms.ModelForm):
        def __init__(self, *args, **kwargs): 
            super(AuxiliaryUnitForm, self).__init__(*args, **kwargs)
            self.fields['org'].initial=org.pk
            self.fields['org'].widget=forms.HiddenInput()
            self.fields['parent'].initial=unit.pk
            self.fields['parent'].widget=forms.HiddenInput()
        class Meta:
            model=Unit
            
        def clean(self):
            cleaned_data=super(AuxiliaryUnitForm,self).clean()
            #cleaned_data=self.cleaned_data
            if self.errors:
                return cleaned_data
            try:
                if not self.cleaned_data['unit']:
                    self._errors['unit']=self.error_class([_(u'请填写辅助单位')])
                    del cleaned_data['unit']
                
                if not self.cleaned_data['rate']:
                    self._errors['rate']=self.error_class([_(u'请填写转换率')])
                    del cleaned_data['rate']
            except:
                print traceback.print_exc()
                
            return cleaned_data
        
    return AuxiliaryUnitForm
'''
    物品品牌
'''
class BrandForm(forms.ModelForm):
    
    class Meta:
        model=Brand
        widgets={
            'brand':forms.TextInput(attrs={'class':'input-small'}),
        }


'''
'    物品分类
'''
class CategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs): 
        super(CategoryForm, self).__init__(*args, **kwargs)      
        self.data.update({'org':kwargs['initial'].get('org',None)})
        self.data.update({'parent':kwargs['initial'].get('parent',None)})
        if self.instance.pk:
            self.fields['parent'].queryset=Category.objects.filter(org=self.data['org'].get_root_org(),is_global=True).exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset=Category.objects.filter(org=self.data['org'].get_root_org(),is_global=True)
        
    description=forms.CharField(label=_(u'分类描述'),required=False,widget=forms.Textarea({'rows':2,'style':'width:100%'}))
    #parent=forms.ModelChoiceField(label=_(u'上级分类'),queryset=[],required=False,widget=forms.widgets.Select(),empty_label=None)
    parent=forms.ModelChoiceField(label=_(u'上级分类'),queryset=[],required=False,widget=TreeSelect(),empty_label=None)
    
    class Meta:
        model=Category
        fields=('parent','name','index','cover','description','status','user','code')
        
    def clean_code(self):
        code=self.cleaned_data['code']
        if self.instance.code==code or (not code):
            return code
        try:
            Category.objects.get(code=code)
        except:
            return code
        
        raise forms.ValidationError(_(u'已经存在分类有相同的编码值'))
        
    def clean(self):
        cleaned_data=super(CategoryForm,self).clean()
        #cleaned_data=self.cleaned_data
        if self.errors:
            return cleaned_data
        try:
            category=Category.objects.get(org=self.data['org'],parent=self.data['parent'],name=cleaned_data['name'])
            if self.instance and self.instance==category:
                raise
            self._errors['name']=self.error_class([_(u'分类名称重复')])
            del cleaned_data['name']
        except:
            print traceback.print_exc()
            
        return cleaned_data
    
'''
'    物品
'''
class GoodsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs): 
        super(GoodsForm, self).__init__(*args, **kwargs)
        self.data.update({'org':kwargs['initial'].get('org',None)})
        #self.data.update({'category':kwargs['initial'].get('category',None)})
        if not Category.objects.filter(org=self.data['org'].get_root_org()).count():
            Category.objects.get_or_create(parent__isnull=True,org=self.data['org'].get_root_org(),defaults={'name':_(u'全部分类')})
        self.fields['category'].queryset=Category.objects.filter(org=self.data['org'].get_root_org(),is_global=True)
        self.fields['shelf_life_type'].empty_label=None
        self.fields['unit'].queryset=Unit.objects.filter(org=self.data['org'].get_root_org(),parent__isnull=True)
            
        
    category=forms.ModelChoiceField(label=_(u'物品分类'),queryset=[],required=False,widget=TreeSelect(),empty_label=None)
    
        
    class Meta:
        model=Goods
        fields=('code','name','category','brand','cover','price_ori','sale_price_ori','standard','unit','abbreviation','shelf_life','shelf_life_type',
                'min_warning','max_warning','remark','status','warning_day','item_type')
        widgets={
            'remark':forms.Textarea(attrs={'rows':2,'style':'width:97%'}),
        }
        
    def clean_customer_price_life(self):
        if int(self.data['chengben_type'])==3 and not self.cleaned_data['customer_price_life']:
            raise forms.ValidationError(_(u'请填入自定义成本的计算时间'))
        
        return self.cleaned_data['customer_price_life']
        
    def clean_code(self):
        code=self.cleaned_data['code']
        if self.instance.code==code or (not code):
            return code
        try:
            Goods.objects.get(code=code,org=self.data['org'])
            raise forms.ValidationError(_(u'已经存在物品有相同的编码值'))
        except:
            return code
        
        
        
'''
    领料部门
'''
class ConDepartmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs): 
        super(ConDepartmentForm, self).__init__(*args, **kwargs)
        self.data.update({'org':kwargs['initial'].get('org',None)})
        
    class Meta:
        model=ConDepartment
        exclude=('count','money')
        widgets={
            'address':forms.TextInput(attrs={'style':'width:100%'}),
        }
        
        
'''
    供货商
'''
class SupplierForm(forms.ModelForm):
    def __init__(self, *args, **kwargs): 
        super(SupplierForm, self).__init__(*args, **kwargs)
        self.data.update({'org':kwargs['initial'].get('org',None)})
        if kwargs['initial'].get('org',None):
            self.fields['group'].queryset=SupplierGroup.objects.filter(org=kwargs['initial']['org'])
        self.fields['group'].empty_label=_(u'不分组')
        
        
    class Meta:
        model=Supplier
        exclude=('count','money','status')
        widgets={
            'address':forms.TextInput(attrs={'style':'width:98%','placeholder':_(u'详细街道地址')}),
            'invoice_address':forms.TextInput(attrs={'style':'width:98%'}),
        }
        
        
'''
    客户
'''
class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs): 
        super(CustomerForm, self).__init__(*args, **kwargs)
        self.data.update({'org':kwargs['initial'].get('org',None)})
        
    class Meta:
        model=Customer
        exclude=('count','money')
        widgets={
            'address':forms.TextInput(attrs={'style':'width:100%'}),
        }