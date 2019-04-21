# -*- coding: utf-8 -*- 
from django.db import models
from mptt.models import MPTTModel
from mptt.fields import TreeForeignKey
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Sum
from gicater.utils.model import update_model


'''
'    几个固定类目：
'    1-收入
'    2-支出
'    3-POS销售收入
'    4-账单采购支出
'    5-销售收入
'''
class FundsDayHis(models.Model):
    org=models.ForeignKey('depot.Organization',on_delete=models.CASCADE)
    date=models.DateField(blank=True,null=True)
    amount=models.FloatField(blank=True,null=True)
    category=models.ForeignKey('FundsCategory',blank=True,null=True,related_name='funds') 
    
    user=models.ForeignKey(User,blank=True,null=True)
    remark=models.CharField(max_length=100,blank=True,null=True,default=None)
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    
    @classmethod
    def update_day_amount(cls,org,day):
        try:
            fundsDayHis,created=FundsDayHis.objects.get_or_create(date=day,org=org,category=None,defaults={'amount':0})
        except:
            FundsDayHis.objects.filter(date=day,org=org,category=None)[1].delete()
            fundsDayHis=FundsDayHis.objects.filter(date=day,org=org,category=None)[0]
            
        in_sum=FundsDayHis.objects.filter(category__isnull=False,category__parent__ftype=1,org=org,date=day).aggregate(sum=Sum('amount'))['sum']
        out_sum=FundsDayHis.objects.filter(category__isnull=False,category__parent__ftype=2,org=org,date=day).aggregate(sum=Sum('amount'))['sum']
        
        #fundsDayHis.amount=(in_sum or 0)-(out_sum or 0)
        #fundsDayHis.save()
        update_model(fundsDayHis,amount=(in_sum or 0)-(out_sum or 0))
    
class FundsCategory(MPTTModel):
    org=models.ForeignKey('depot.Organization',on_delete=models.CASCADE)
    parent=TreeForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='children')
    name=models.CharField(_(u'分类名称'),max_length=50)
    ftype=models.IntegerField(_(u'类型'),default=1,choices=((1,_(u'收入')),(2,_(u'支出')),(3,_(u'用户自定义')),(4,_(u'销售收入')),(5,_(u'采购支出')),(6,_(u'POS销售收入'))))
    status=models.IntegerField(default=1)
    
    def __unicode__(self):
        return self.name
    
