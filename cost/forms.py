# -*- coding: utf-8 -*- 
from django import forms
from django.utils import translation
from models import MenuItemProfit
from django.utils.translation import ugettext_lazy as _
import datetime

disday = datetime.timedelta(days=1)

class DateRangeForm(forms.Form):
    def __init__(self,*args,**kwargs):
        super(DateRangeForm, self).__init__(*args, **kwargs)
        self.fields['date_from'].initial=datetime.date.today().replace(day=1)
        self.fields['date_to'].initial=datetime.date.today()
    
    date_from =forms.DateField(label=_(u'起始时间'),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    date_to = forms.DateField(label=_(u'结束时间'),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    
    def clean_date_to(self):
        return self.cleaned_data['date_to']+disday


class MenuProfitQueryForm(forms.Form):
    item_name =forms.CharField(label=_(u'菜品名称'),max_length=200,required=False)
    date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))

    def clean_date_to(self):
        return self.cleaned_data['date_to']+disday