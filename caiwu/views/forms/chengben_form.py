# -*- coding: utf-8 -*- 
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import translation
from django.db.models import Q
from caiwu.models import FundsDayHis, FundsCategory
import datetime
import traceback

def make_FundsDayHisForm(org_id,day,category_id,user=None):
    class FundsDayHisForm(forms.ModelForm):
        def __init__(self,*args,**kwargs):
            super(FundsDayHisForm, self).__init__(*args, **kwargs)
            self.fields['org'].initial=org_id
            self.fields['category'].queryset=FundsCategory.objects.filter(org_id=org_id,parent__isnull=False,status__gt=0)
            self.fields['category'].empty_label=None
            self.fields['date'].initial=day
            self.fields['category'].initial=category_id
            self.fields['amount'].required=True

            
        class Meta:
            model=FundsDayHis
            widgets={
                'org':forms.HiddenInput(attrs={'class':'org'}),
                'category':forms.Select(attrs={'style':'width:90px'}),
                'amount':forms.TextInput(attrs={'style':'width:60px'}),
                'remark':forms.TextInput(attrs={'style':'width:280px'})
            }
            
        def clean_user(self):
            return user
            
    return FundsDayHisForm
            

def make_FundsCategoryForm(org_id,level,parent=None):            
    class FundsCategoryForm(forms.ModelForm):
        def __init__(self,*args,**kwargs):
            super(FundsCategoryForm, self).__init__(*args, **kwargs)
            self.fields['org'].initial=org_id
            
            if level==1:
                self.fields['ftype'].choices=((1,_(u'收入')),(2,_(u'支出')))
            else:
                if parent and parent.ftype==1:
                    self.fields['ftype'].choices=((3,_(u'自定义')),(4,_(u'销售收入')),(6,_(u'POS销售收入')))
                elif parent and parent.ftype==2:
                    self.fields['ftype'].choices=((3,_(u'自定义')),(5,_(u'采购支出')))
                else:
                    self.fields['ftype'].choices=((3,_(u'自定义')),(4,_(u'销售收入')),(5,_(u'采购支出')),(6,_(u'POS销售收入')))
            
        class Meta:
            model=FundsCategory
            widgets={
                'ftype':forms.Select(attrs={'class':'input-small'}),
                'org':forms.HiddenInput(attrs={'class':'org'}),
            }
            
    return FundsCategoryForm