# -*- coding: utf-8 -*- 
from django.db import models
from depot.models import Organization,Warehouse,User,Invoice
from django.db.models.signals import post_save
from mptt.models import MPTTModel
from mptt.fields import TreeForeignKey
from django.utils.translation import ugettext_lazy as _


class CategoryPos(MPTTModel):
    parent=TreeForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='children')
    name=models.CharField(_(u'分类名称'),max_length=50)
    description=models.CharField(_(u'分类描述'),max_length=200,blank=True,null=True)
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)
    org=models.ForeignKey(Organization,null=True,blank=True)
    index=models.IntegerField(_(u'分类索引'),default=1000,help_text=_(u'分类索引越小,在排序的时候越靠前'))
    
    slu_id=models.IntegerField(_(u'收银分类slu'),null=True,blank=True)
    processing=models.IntegerField(_(u'处理状态'),default=0,help_text=u'每次处理前，先将该值置为1，若有slu_id的值，则再置回0,仅显示为0的条目')

    def __unicode__(self):
        return self.name
    
    
'''
    类似收银中的菜品，取部分属性，每个规格单独一列
    菜品利润分析
    percent1---销售利润率
    percent2---成本利润率
'''
class MenuItem(models.Model):
    categoryPos=models.ForeignKey(CategoryPos,null=True,blank=True)
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    item_id=models.IntegerField()
    item_name=models.CharField(max_length=60,blank=True,null=True)
    nlu=models.CharField(max_length=20,blank=True,null=True)
    price=models.FloatField(default=0,blank=True,null=True)
    unit=models.CharField(default='',max_length=30,blank=True,null=True)
    
    cost=models.FloatField(_(u'成本'),null=True,blank=True)
    profit=models.FloatField(_(u'利润'),null=True,blank=True)
    update_time=models.DateTimeField(auto_now=True)
    percent1=models.FloatField(null=True,blank=True)
    percent2=models.FloatField(null=True,blank=True)
    processing=models.IntegerField(_(u'处理状态'),default=0,help_text=u'每次处理前，先将该值置为1，若有slu_id的值，则再置回0,仅显示为0的条目')
    
    status=models.IntegerField(default=1)
    sync_type=models.IntegerField(_(u'菜品类型'),default=1,choices=((0,_(u'一对多菜品')),(1,_(u'一对一菜品'))),help_text=_(u'一对一菜品会自动扣减库存，一对多菜品不会自动扣减库存'))
    last_sale_time=models.DateField(null=True,blank=True)
    last_sale_num=models.IntegerField(null=True,blank=True,default=0)
    
    def __unicode__(self):
        return self.item_name
    
    def save(self, *args, **kwargs):
        if self.cost and self.price and self.cost*self.price:
            self.percent1=int((self.price-self.cost)*100/self.price)
            self.percent2=int((self.price-self.cost)*100/self.cost)
        super(MenuItem,self).save(*args, **kwargs)

    class Meta:
        ordering=("-update_time",)

    
class MenuItemDetail(models.Model):
    org=models.ForeignKey('depot.Organization')
    menuItem=models.ForeignKey(MenuItem,related_name='details',on_delete=models.CASCADE)
    good=models.ForeignKey('depot.Goods',related_name='item_detail',on_delete=models.CASCADE)
    weight=models.FloatField(_(u'用到的数量  '),default=1)
    goods_unit=models.ForeignKey('depot.Unit',null=True,blank=True,on_delete=models.PROTECT,verbose_name='原材料单位')
    status=models.IntegerField(default=1)
    goods_type=models.IntegerField(_(u'原材料类型'),default=1,choices=((1,_(u'主料')),(2,_(u'辅料'))))
    
    
    class Meta:
        db_table="cost_menuitemdetail"
    
    

    
'''
    一次与收银的同步，POST格式为
    {guid:guid,datas:[
        {zdate:'2015-01-27',details:[
            {item_id:1001,item_name:'coco',
                nlu:13245532,price:10,num:10,
                total_price:95,unit:'kg'
            }]
        },...
    ]}
'''
class SyncStamp(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    last_sync_time=models.DateTimeField(null=True,blank=True)
    
    
class SyncHis(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    created_time=models.DateTimeField(auto_now_add=True)
    status=models.IntegerField(default=0)
    raw_str=models.TextField(null=True,blank=True)
    
    class Meta:
        ordering=("-created_time",)
    
'''
    传入的His,按天划分为seq
'''    
class SyncSeq(models.Model):
    his=models.ForeignKey(SyncHis,on_delete=models.CASCADE,related_name="seqs")
    zdate=models.DateField()
    status=models.IntegerField(default=0)
    raw_str=models.TextField(null=True,blank=True)
    
'''
    记录历史细节信息
'''   
class SyncSeqDetail(models.Model):
    seq=models.ForeignKey(SyncSeq,on_delete=models.CASCADE,related_name="details")
    menuItem=models.ForeignKey(MenuItem,null=True,blank=True)
    goods_text=models.CharField(max_length=100,null=True,blank=True)
    item_id=models.IntegerField()
    item_name=models.CharField(max_length=60,blank=True,null=True)
    nlu=models.CharField(max_length=20,blank=True,null=True)
    price=models.FloatField(default=0)
    num=models.FloatField(default=0)
    total_price=models.FloatField(default=0)
    unit=models.CharField(default='',max_length=30,blank=True,null=True)
    cost=models.FloatField(default=0,blank=True,null=True)
    
class SyncHisStep(models.Model):
    syncHis=models.ForeignKey(SyncHis,on_delete=models.CASCADE,related_name="steps")
    seq=models.ForeignKey(SyncSeq,blank=True,null=True,on_delete=models.CASCADE,related_name="steps")
    ztime=models.DateTimeField(auto_now=True)
    remark=models.CharField(max_length=200)


#菜品利润表
class MenuItemProfit(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    zdate=models.DateTimeField(auto_now_add=True)
    item_name=models.CharField(max_length=60,blank=True,null=True)
    item_id=models.IntegerField(blank=True,null=True)
    nlu=models.CharField(max_length=20,blank=True,null=True)
    sale_num=models.FloatField(default=0)
    price=models.FloatField(_(u'单价'),default=0)
    unit=models.CharField(default='',max_length=30,blank=True,null=True)
    cost=models.FloatField(_(u'单个成本'),null=True,blank=True)
    profit=models.FloatField(_(u'利润'),null=True,blank=True)

