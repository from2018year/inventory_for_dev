# -*- coding: utf-8 -*- 
from django.db import models
from django.db import models
from django.contrib.auth.models import User,Permission
from inventory.MACROS import *
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from mptt.models import MPTTModel
from django.utils import simplejson
from django.core.urlresolvers import reverse
from mptt.fields import TreeForeignKey
from inventory.settings import MEDIA_ROOT, LANGUAGES
from inventory.common import datedelta, get_next_increment, numtoCny, SumCase, fix_get_next_increment
from django.db.models import Q,Sum,Count
from inventory.ThumbnailFile import ThumbnailImageField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
import traceback
import datetime
import operator 
import os
from django import conf
from gicater.utils.model import update_model
import time
quanxian_debug=False


'''
    扩展Django用户定义，使其符合会员系统的格式
'''
class ProfileBase(type):
    def __new__(cls,name,bases,attrs):
        module=attrs.pop('__module__')
        parents=[b for b in bases if isinstance(b,ProfileBase)]
        if parents:
            fields=[]
            for obj_name,obj in attrs.items():
                if isinstance(obj,models.Field):fields.append(obj_name)
                User.add_to_class(obj_name,obj)
            #UserAdmin.fieldsets=list(UserAdmin.fieldsets)
            #UserAdmin.fieldsets.append((name,{'fields':fields}))
        return super(ProfileBase,cls).__new__(cls,name,bases,attrs)


class Profile(object):
    __metaclass__ = ProfileBase 


class CustomerProfile(Profile): 
    delinquent=models.DecimalField(_(u'欠费金额'),max_digits=10,decimal_places=2,default=0)
    employee_id=models.CharField(_(u'员工编号'),max_length=50,blank=True,null=True)
    position=models.CharField(_(u'职务'),max_length=100,blank=True,null=True)
    phone=models.CharField(_(u'固话'),max_length=50,blank=True,null=True)
    tel=models.CharField(_(u'手机'),max_length=20,blank=True,null=True)
    post_code=models.CharField(_(u'邮编'),max_length=20,blank=True,null=True)
    choosed_language=models.CharField(_(u'语言偏好'),max_length=10,choices=LANGUAGES,default='zh_CN')
    expiry_date=models.DateField(_(u'过期日期'),blank=True,null=True)
    sex=models.IntegerField(_(u'性别'),choices=SEX,default=1)
    
    address=models.CharField(_(u'住址'),max_length=200,blank=True,null=True)
    qq=models.CharField(_(u'QQ号码'),max_length=20,blank=True,null=True)
    school=models.CharField(_(u'毕业院校'),max_length=50,blank=True,null=True)
    birthday=models.DateField(_(u'生日'),blank=True,null=True)
    birth_type=models.IntegerField(_(u'生日类型'),default=0,choices=BIRTH_TYPES)
    nation=models.IntegerField(_(u'民族'),default=1,choices=NATIONS)
    remark=models.TextField(_(u'备注'),blank=True,null=True)
    img=models.ImageField(_(u'头像'),upload_to='UP/',blank=True,null=True)
    finger_print=models.CharField(_(u'指纹'),max_length=500,blank=True,null=True)
    credential_type=models.IntegerField(_(u'证件类型'),default=1,choices=CREDENTIAL_TYPES)
    credential_number=models.CharField(_(u'证件号码'),max_length=50,blank=True,null=True)
    user_levels=models.ManyToManyField('depot.UserLevel',blank=True)

    
    def is_org_superuser(self,org_or_id):
        return isinstance(org_or_id, Organization) and OrgsMembers.objects.filter(org=org_or_id,
                user=self,superior=True).exists() or OrgsMembers.objects.filter(org_id=org_or_id,user=self,superior=True).exists()
                
                
    def get_org_permissions(self,org_id,cache=True):
        if self.is_anonymous():
            return set()
        
        if not hasattr(self, '_org_perm_cache'):
            if cache:
                self._org_perm_cache = self.get_org_user_permissions(org_id)
                self._org_perm_cache.update(self.get_org_group_permissions(org_id))
                return self._org_perm_cache
            else:
                org_perm_cache = self.get_org_user_permissions(org_id)
                org_perm_cache.update(self.get_org_group_permissions(org_id))
                return org_perm_cache
        else:    
            return self._org_perm_cache
    
    '''
    '    员工权限，现在还没有涉及单独员工权限，都是分组管理，暂时不需要
    '''    
    def get_org_user_permissions(self,org_id):
        return set()
        ups=UserPermissions.objects.filter(user=self,org_id=org_id)
        if ups.exists():
            if ups.filter(permission__isnull=True).exists():
                perms=Permission.objects.exclude(name__startswith="Can")
                perms = perms.values_list('content_type__app_label', 'codename').order_by()
                print perms
            else:
                perms=UserPermissions.objects.filter(permission__isnull=False,user_id=self.id,org_id=org_id).select_related()
                perms = perms.values_list('permission__content_type__app_label', 'permission__codename').order_by()
            self._org_user_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
            return self._org_user_perm_cache
        else:
            return set()
            
    
    def get_org_group_permissions(self,org_id):
        #注释原因：一些权限判断contenttype不属于orgnization
        #content_type=ContentType.objects.get_for_model(Organization)
        if self.is_org_superuser(org_id):
            perms=Permission.objects.filter(content_type=content_type).exclude(name__startswith="Can")
                
        else:
            levels=UserLevel.objects.filter(user=self,org_id=org_id)
            perms=Permission.objects.filter(userlevel__in=levels)#,content_type=content_type)
            
        perms = perms.values_list('content_type__app_label', 'codename').order_by()
        self._org_group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return self._org_group_perm_cache
    
    def has_org_perm(self,org_or_id,perm,cache=True):
        org_id=org_or_id
        if isinstance(org_or_id, Organization):
            org_id=org_or_id.id
            
        if not self.is_active:
            return False
        if self.is_org_superuser(org_id):
            return True
        
        org=Organization.objects.get(pk=org_id)
        if org.parent:
            if self.is_org_superuser(org_id=org.parent.pk) or self.has_org_perm(org.parent.pk, 'depot.org_manage',cache=False):
                return True
        
        return perm in self.get_org_permissions(org_id,cache)
    
    
    def get_org_warehouse_permissions(self,warehouse_id,org_id=None,cache=True):
        if self.is_anonymous():
            if quanxian_debug:
                print 'get_org_warehouse_permissions:'+'is_anonymous'
            return set()
        
        if not org_id:
            warehouse=Warehouse.objects.get(pk=warehouse_id)
            org_id=warehouse.org_id
        
        attr_str="_org_warehouse_perm_cache_%s"%warehouse_id    
        if not hasattr(self, attr_str):
            if cache:
                setattr(self,attr_str,self.get_org_warehouse_group_permissions(warehouse_id,org_id))
                if quanxian_debug:
                    print 'get_org_warehouse_permissions: '+str(warehouse_id)+" "+str(getattr(self,attr_str))
                return getattr(self,attr_str)
            else:
                org_perm_cache = self.get_org_warehouse_group_permissions(warehouse_id,org_id)
                if quanxian_debug:
                    print 'get_org_warehouse_permissions:'+str(warehouse_id)+" "+str(org_perm_cache)
                return org_perm_cache
        else:    
            if quanxian_debug:
                print 'get_org_warehouse_permissions: use cache '+str(warehouse_id)+" "+str(getattr(self,attr_str))
            return getattr(self,attr_str)
        
    def get_org_warehouse_group_permissions(self,warehouse_id,org_id):
        content_type=ContentType.objects.get_for_model(Warehouse)
        if self.is_org_superuser(org_id):
            perms=Permission.objects.filter(content_type=content_type).exclude(name__startswith="Can")
                
        else:
            levels=UserLevel.objects.filter(user=self,org_id=org_id,warehouse=warehouse_id)
            perms=Permission.objects.filter(userlevel__in=levels,content_type=content_type)
            
        perms = perms.values_list('content_type__app_label', 'codename').order_by()
        self._org_group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return self._org_group_perm_cache
    
    '''
    '    用户是否有org下某个仓库的指定/任意权限
    '''
    def has_org_warehouse_perm(self,warehouse_id,perm=None,org_id=None,cache=True):
        if not self.is_active:
            return False
        
        if not org_id:
            warehouse=Warehouse.objects.get(pk=warehouse_id)
            org_id=warehouse.org_id
            
        org=Organization.objects.get(pk=org_id)
        
        if self.is_org_superuser(org_id) or self.has_org_perm(org_id,'depot.org_manage'):
            return True
    
        if org.parent:
            if self.is_org_superuser(org_id=org.parent_id) or self.has_org_perm(org.parent_id, 'depot.org_manage',cache=False):
                return True
        
        if isinstance(perm, (list,tuple)):
            for _perm in perm:
                
                if _perm in self.get_org_warehouse_permissions(warehouse_id,org_id,cache):
                    return True
            return False
        elif perm:
            return perm in self.get_org_warehouse_permissions(warehouse_id,org_id,cache)
        else:
            return UserLevel.objects.filter(user=self,org_id=org_id,warehouse=warehouse_id).exists()
    
    '''
    '    用户是否有org下任意仓库的指定权限
    '''
    def has_org_warehouse_the_perm(self,perm,org_id,cache=True):
        if not self.is_active:
            return False
        if self.is_org_superuser(org_id) or self.has_org_perm(org_id,'depot.org_manage'):
            return True
        
        org=org_id
        if not isinstance(org_id, Organization):   
            org=Organization.objects.get(pk=org_id)
        if org.parent:
            if self.is_org_superuser(org_id=org.parent_id) or self.has_org_perm(org.parent_id, 'depot.org_manage',cache=False):
                return True
        
        return UserLevel.objects.filter(org=org,permissions__codename=perm.split(',')[1]).exists()
    
    '''
    '    用户是否在某个org下有仓库权限
    '''
    def has_warehouse_permission(self,org_id):
        if not self.is_active:
            return False
        if self.is_org_superuser(org_id) or self.has_org_perm(org_id,'depot.org_manage'):
            return True
            
        org=Organization.objects.get(pk=org_id)
        if org.parent:
            if self.is_org_superuser(org_id=org.parent_id) or self.has_org_perm(org.parent_id, 'depot.org_manage',cache=False):
                return True
            
        return UserLevel.objects.filter(user=self,org_id=org_id,warehouse__isnull=False).exists()
    
    '''
    '    得到一家店中，用户的可用仓库数,或给定权限的仓库数
    '''
    def get_warehouses(self,org_or_id,perms=[]):
        if not isinstance(org_or_id,Organization):
            org_or_id=Organization.objects.get(pk=org_or_id)
            
        warehouses=Warehouse.objects.filter(org=org_or_id,parent__isnull=True)
        return warehouses
        '''
        @注释原因：新增用户无法得到仓库权限


        if self.is_org_superuser(org_or_id) or self.has_org_perm(org_or_id,'depot.org_manage'):
            return warehouses
        else:
            if perms:
                return warehouses.filter(user_levels__user=self,user_levels__permissions__codename__in=perms).distinct()
            else:
                return warehouses.filter(user_levels__user=self).distinct()
        '''

'''
    城市片区
    华北/华东/华南/华中/西北/西南/东北
'''
class CityArea(models.Model):
    name=models.CharField(_(u'片区名称'),max_length=20)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name=_(u'城市片区')
        verbose_name_plural=_(u"城市片区")
                 
'''
     城市地址
'''        
class City(MPTTModel):
    parent=models.ForeignKey('self',verbose_name=_(u'上级'),blank=True,null=True)
    name=models.CharField(_(u'国家/城市'),max_length=30)
    abbr=models.CharField(_(u'拼音'),max_length=100)
    
    area=models.ForeignKey(CityArea,verbose_name=(_(u'所属片区')),related_name='citys',blank=True,null=True,on_delete=models.SET_NULL)
    nc_code=models.CharField(_(u'农产品商务信息平台代码'),max_length=20,blank=True,null=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name=_(u'城市')
        verbose_name_plural=_(u"城市")
         
    
'''
    所有店家，组织明细
    所有店家分为俩种类型，总店和分店
    分店有分为直营店和加盟店
    所有总店对应一个User，此User为总店的负责人，具有所有总店的权限，并且负责维护总店和分店
    已预留分店可以再开分店的接口
    
    instance.children 即得到本店的全部分店,如果分店和总店都有短信可用，优先用自己的
'''
class Organization(MPTTModel):
    parent=TreeForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='children')
    members=models.ManyToManyField(User,through='OrgsMembers')
    org_guid=models.CharField(_(u'餐厅ID'),max_length=200,blank=True,null=True,help_text=_(u'用来和收银系统验证，不使用则不填'))
    pos_ip=models.IPAddressField(_(u'前台收银IP地址'),blank=True,null=True,help_text=_(u'用来和收银系统通信，不使用则不填'))
    
    org_name=models.CharField(_(u'公司名称'),max_length=200)
    org_group=models.ForeignKey('OrganizationGroup',blank=True,null=True,on_delete=models.SET_NULL,verbose_name=_(u'属组'))
    
    province=models.ForeignKey(City,related_name='province_orgs',verbose_name=_(u'所在省份'),blank=True,null=True)
    city=models.ForeignKey(City,related_name='city_orgs',verbose_name=_(u'所在市'),blank=True,null=True)
    district=models.ForeignKey(City,related_name='district_orgs',verbose_name=_(u'所在县/区'),blank=True,null=True)
    area=models.ForeignKey(City,related_name='area_orgs',verbose_name=_(u'所在街道'),blank=True,null=True)
    
    stores_address=models.CharField(_(u'地址'),blank=True,null=True,max_length=300)
    
    industry=models.IntegerField(_(u'行业'),choices=INDUSTRY,blank=True,null=True)
    url=models.URLField(_(u'公司主页'),max_length=50,blank=True,null=True)
    phone=models.CharField(_(u'手机'),null=True,blank=True,max_length=50,help_text=_(u'负责人手机号码，多个时以;号隔开'))
    tel=models.CharField(_(u'电话'),max_length=50,blank=True,null=True)
    fax=models.CharField(_(u'传真'),max_length=50,blank=True,null=True)
    post_code=models.CharField(_(u'邮编'),max_length=50,blank=True,null=True)
    orgs_type=models.IntegerField(_(u'经营类型'),choices=ORGS_TYPE,default=1)
    expiry_date=models.DateField(_(u'过期日期'),blank=True,null=True)
    insert_date=models.DateField(auto_now_add=True)
    update_date=models.DateField(auto_now=True)
    remark=models.TextField(_(u'备注'),blank=True,null=True)
 
    slug=models.SlugField(_(u'公司简码'),max_length=50,unique=True,null=True,blank=True)
    style=models.CharField(_(u'风格'),max_length=100,default="inventory",choices=(('gicater',_(u'聚客')),('common',_(u'通用')),('english',_(u'英文版')),('agile',_(u'安捷')),('inventory',_(u'通用')),('other',_(u'其他'))))
    
    class Meta:
        ordering=['id']
        verbose_name=_(u'公司')
        verbose_name_plural=_(u"公司")
        
        permissions=(
            ('org_chenben',_(u'成本管理')),
            ('org_caiwu',_(u'收支管理')),
            ('org_tongji',_(u'统计报表')),
            ('org_settings',_(u'系统设置')),
        )
        
    def __unicode__(self):
        return self.org_name
    
    def __init__(self, *args, **kwargs):
        super(Organization, self).__init__(*args, **kwargs)
        
        self.__important_fields = ['org_guid'] 
        for field in self.__important_fields:
            setattr(self, '__original_%s' % field, getattr(self, field))
    
    @property
    def uid(self):
        return self.slug or self.pk
    
    def get_members(self):
        return User.objects.filter(id__in=list(self.om_members.all().values_list('user_id',flat=True)))
    
    def get_root_org(self):
        return self.get_root()
    
    def get_charger(self):
        u_set=self.om_members.filter(superior=True)
        if u_set.exists():
            return u_set[0].user
        else:
            return _(u'未指定')
        
        
    #得到注册授权值
    @property   
    def webkey(self):
        from inventory.common import fetch_key_web
        
        keys=MacrosKeyWeb.objects.filter(org=self)
        if keys.exists():
            res,_date,sites=fetch_key_web(keys[0])
            return {'key':keys[0].key_str,'event_date':keys[0].event_date,'expired_date':_date,'sites':sites}
           
        return {'key':None,'event_date':None,'expired_date':None,'sites':None}
    
    
    def sync_center(self):
        import requests
        from cost.views import CENTER_URL
        '''
        ' 向用户中心服务器发送同步数据请求
        '''
        try:
            print "%s sync menu_item"%self.org_guid
            r=requests.post(CENTER_URL+"/capi/sync_menuitem_stock/",data={'guid':self.org_guid,'host':getattr(conf.settings,'DEFAUT_URL','http://stock.sandypos.com').strip('/')})
            print 'sync menu_item by save info,guid:%s,status:%s'%(self.org_guid,r.status_code)
        except:
            print traceback.print_exc()
        
def create_org_settings(sender, instance, created, **kwargs):
    from caiwu.models import FundsCategory
            
    if created:
        sr=FundsCategory.objects.create(org=instance,parent=None,name=_(u'收入'),ftype=1)
        zc=FundsCategory.objects.create(org=instance,parent=None,name=_(u'支出'),ftype=2)
        
        FundsCategory.objects.create(org=instance,parent=sr,name=_(u'手工销售'),ftype=4)
        FundsCategory.objects.create(org=instance,parent=sr,name=_(u'POS销售'),ftype=6)
        FundsCategory.objects.create(org=instance,parent=zc,name=_(u'采购支出'),ftype=5)
        
post_save.connect(create_org_settings, sender=Organization)
        
    
class OrgProfile(models.Model):
    org=models.OneToOneField(Organization,on_delete=models.CASCADE,related_name='profile')
    
    jingdu=models.FloatField(_(u'经度'),null=True,blank=True)
    weidu=models.FloatField(_(u'纬度'),null=True,blank=True)
    neg_inv=models.BooleanField(_(u'是否允许负库存'),default=True,help_text=(_(u'允许负库存时，如果出库仓库物品的数量不足，可以出库')))
    warn_day=models.IntegerField(_(u'保质期到期前提醒天数'),default=7,help_text=_(u'值小于1时不提醒，当物品没有单独设置保质期提醒天数时，则默认以此处设置的值为准'))
    
    
    cengji=models.PositiveSmallIntegerField(_(u'仓库层级数'),default=1)
    create_self_goods=models.IntegerField(_(u'是否允许分部建立自己的物品'),default=0,choices=((0,_(u'不允许')),(1,_(u'允许'))))
    
    mobile_his=models.IntegerField(_(u'移动端显示历史时间'),default=1)
    mobile_his_type=models.IntegerField(_(u'移动端显示时间类型'),choices=DATE_UNIT_TYPES,default=3) 
    mobile_confirm=models.BooleanField(_(u'是否允许移动端确认'),default=False,editable=False,help_text=(_(u'若允许确认，则需要移动端确认后，货物才实际入库')))
    
    remind_date=models.IntegerField(_(u'预定前提示'),default=3,blank=True,null=True)
    remind_content=models.CharField(_(u'提醒内容'),max_length=300,blank=True,null=True)
    
    message_share=models.BooleanField(_(u'是否公用总部短信条数'),default=False)
    send_message=models.BooleanField(_(u'短信模块'),default=False)
    send_email=models.BooleanField(_(u'邮件模块'),default=False,help_text=(_(u'启用邮件模块，系统将发送系统信息到您的邮箱')))
    email=models.CharField(_(u'管理员邮箱'),max_length=500,blank=True,null=True,help_text=_(u'负责人邮箱，多个时以;号隔开'))

    is_auto_caigouruku=models.BooleanField(_(u'申请单审核后自动生成采购入库单'),default=True)
    auto_confirm_xiaoshouchuku=models.BooleanField(_(u'创建销售出库单后自动审核'),default=True,help_text=_(u'若没有审核权限,将不会审核'))
    auto_confirm_caigoushenqing=models.BooleanField(_(u'创建申请单后自动审核'),default=True,help_text=_(u'若没有审核权限，将不会审核'))
    auto_confirm_caigouruku=models.BooleanField(_(u'创建采购入库单后自动审核'),default=True,help_text=_(u'若没有审核权限，将不会审核'))
    auto_confirm_lingyongchuku=models.BooleanField(_(u'创建领用出库单后自动审核'),default=True,help_text=_(u'若没有审核权限，将不会审核'))
    auto_confirm_caigoutuihuo=models.BooleanField(_(u'创建采购退货单后自动审核'),default=True,help_text=_(u'若没有审核权限，将不会审核'))
    auto_confirm_pandian=models.BooleanField(_(u'创建盘点单后自动审核'),default=True,help_text=_(u'若没有审核权限，将不会审核'))

    symbol = models.CharField(_(u'货币符号'),max_length=80,blank=True,null=True,help_text=_(u'使用的货币符号'))

    #菜品对应的最大物品数
    max_item = models.IntegerField(_(u'菜品最大原材料数'),default=5,help_text=_(u'配置菜品时，每个菜品对应可配置的最大原材料数目'))

    auto_out_stock_mode=models.IntegerField(_(u'收银自动出库模式'),default=1,help_text=_(u'自动出库模式，0为每次收银结账同步，1为每次日结同步'))
    
    
    #price0=models.BooleanField(_(u'对价格为0的批次不计算均价'))


'''
    仓库
'''    
class Warehouse(MPTTModel):
    org=models.ForeignKey(Organization,on_delete=models.PROTECT)
    parent=models.ForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='shelfs')
    name=models.CharField(_(u'名称'),max_length=100)    
    
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)
    status=models.BooleanField(_(u'启用'),default=True,help_text=_(u'是否启用,可以用来临时禁用,不再接受出入库'))
    oindex=models.BooleanField(_(u'设置为默认出库'),default=False,help_text=_(u'和收银同步时，扣减的仓库'))
    
    address=models.CharField(_(u'仓库地址'),max_length=200,blank=True,null=True)
    residual_capacity=models.FloatField(_(u'剩余容量'),blank=True,null=True)
    capacity=models.FloatField(_(u'实际容量'),blank=True,null=True)
    charger=models.ForeignKey(User,blank=True,null=True,verbose_name=_(u'负责人'),on_delete=models.SET_NULL)
    
    class Meta:
        unique_together = ("name","org","parent")
        permissions=(            
            ('warehouse_read',_(u'仅可见')),
            ('warehouse_write',_(u'可操作')),
        )
    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shelf_list',args=[self.org.pk,self.pk])
        #return self.parent and reverse('shelf_list',args=[self.org.pk,self.parent.pk]) or reverse('warehouses_list',args=[self.org.pk])
    
    @classmethod
    def get_warehouse_path(cls,org,warehouse_str,warehouse_count=2):
        if not warehouse_str:
            return None
        warehouses=warehouse_str.split('->')
        try:
            warehouse=Warehouse.objects.get(org=org,parent__isnull=True,name=warehouses[0])
        except:
            if Warehouse.objects.filter(org=org,parent__isnull=True).count()>=warehouse_count:
                return None
            warehouse=Warehouse.objects.create(org=org,parent=None,name=warehouses[0])
        
        c_warehouse=warehouse
        for _warehouse in warehouses[1:]:
            c_warehouse,created=Warehouse.objects.get_or_create(org=org,parent=c_warehouse,name=_warehouse)
            
            
        return c_warehouse
        
    
    @classmethod        
    def get_queryset_descendants(cls,nodes, include_self=False): 
        if not nodes: 
            return cls.objects.none() 
        filters = [] 
        for n in nodes: 
            lft, rght = n.lft, n.rght 
            if include_self: 
                lft -=1 
                rght += 1 
            filters.append(Q(tree_id=n.tree_id, lft__gt=lft, rght__lt=rght)) 
        q = reduce(operator.or_, filters) 
        return cls.objects.filter(q)
    
    @property
    def full_name(self):
        return '->'.join(self.get_ancestors(include_self=True).values_list('name',flat=True))
    
    @property
    def get_charger(self):
        chargers=self.get_ancestors(ascending=True,include_self=True).filter(charger__isnull=False)
        return chargers.exists() and chargers[0].charger or None 
    

    #获取仓库货物    
    @property
    def get_goods(self):
        #count=Goods.objects.filter(details__invoice__warehouse_root_id=self.pk).distinct().count()
        total_value=self.warehouse_value()
        return total_value[1],total_value[0]
        goods=Goods.objects.filter(details__invoice__invoice_type__in=IN_BASE_TYPE,
                            details__invoice__warehouse_root_id=self.pk,
                           details__invoice__status=2).annotate(sum=Sum('details__last_nums'))        
        count=goods.count()
        amount=0
        for good in goods:
            amount += good.sum*good.price
        
        return count,amount
    
    def serialize_to_json(self):
        return simplejson.dumps(self.serializable_object())

    def serializable_object(self):
     
        obj = {'id':self.pk and int(self.pk) or self.pk,'pId':self.parent and int(self.parent_id) or 0 ,'name': u"%(name)s(￥%(value).2f)"%{'name':self.name,'value':self.warehouse_value()[0]},'open':True, 'children': [],'iconSkin':self.parent and 'icon icon-tasks n' or 'icon icon-home n'}
    
        for child in self.get_children():
            o=child.serializable_object()
            if o:
                obj['children'].append(o)
                      
        return obj
    
    
    def warehouse_value(self,include_children=True):
        if include_children:
            details=InvoiceDetail.objects.filter(warehouse__in=self.get_descendants(include_self=True))
        else:
            details=InvoiceDetail.objects.filter(warehouse=self)
        
        #c=details.filter(invoice__invoice_type__in=IN_BASE_TYPE,invoice__status=2).aggregate(total=Sum('price',field="avg_price*last_nums"),cc=Count('good',field="distinct(good_id)"))  
        details=details.filter(invoice__invoice_type__in=IN_BASE_TYPE,invoice__status=2).exclude(last_nums=0)
        
        l=details.values('good_id').annotate(Sum('last_nums'))
        
        goods_id=[x['good_id'] for x in l if round(x['last_nums__sum'],2)!=0]
        c=details.filter(good_id__in=goods_id).aggregate(total=Sum('price',field="avg_price*last_nums"))
        #return c.exists() and (c[0]['total'],c[0]['cc']) or (0,0)
        return c['total'] or 0,len(goods_id)
    
    '''
    '    以列表形式得到warehouse
    '''
    @classmethod 
    def warehouse_list(cls,org):
        return [warehouse.full_name for warehouse in Warehouse.objects.filter(org=org,status=True)]
    
    '''
    '    以列表形式返回得到warehouse
    '''
    @classmethod
    def warehouse_list_to_warehouse(cls,org,w_str):
        warehouses=Warehouse.objects.filter(org=org)
        i=0

        for w_s in w_str.split('->'):
            warehouse=warehouses.get(level=i,name=w_s)
            warehouses=warehouse.get_children()
            i+=1

        return warehouse
'''
    对应user和org的关系
    level:
    9--后来员工
    0--初始员工
    
'''
class OrgsMembers(models.Model):
    user=models.ForeignKey(User,related_name='om_orgs',on_delete=models.CASCADE)
    org=models.ForeignKey(Organization,related_name='om_members')
    date_joined=models.DateTimeField(auto_now_add=True)
    level=models.IntegerField(default=9)
    superior=models.BooleanField(default=False) 
    
    class Meta:
        verbose_name=_(u'分部员工')
        verbose_name_plural=_(u"分部员工")
        
    def __unicode__(self):
        return u"%s(%s)"%(self.user,self.org)
    
class UserPermissions():
    pass


'''
    商家分类
'''  
class OrganizationGroup(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name='groups')
    name=models.CharField('分类名称',max_length=50)
    
    class Meta:
        unique_together = ("name", "org")
        verbose_name=_(u'分部类别')
        verbose_name_plural=_(u"分部类别")
        
    def __unicode__(self):
        return self.name
    
    
    
'''
    用户组，每个用户可以属于仓库旗下的多个用户组
'''
class UserLevel(models.Model):
    name=models.CharField(_(u'组名'),max_length=50)
    permissions=models.ManyToManyField(Permission,blank=True,verbose_name=_(u'权限'))
    org=models.ForeignKey(Organization,related_name="user_levels",on_delete=models.CASCADE)
    warehouse=models.ManyToManyField(Warehouse,blank=True,related_name='user_levels')
    
    class Meta:
        unique_together = ("name","org")


        permissions=(
                ('wupin_ui',_(u'物品界面操作')),
                ('chenbenka_ui',_(u'成本卡界面操作')),
                ('danju_ui',_(u'单据界面操作')),
                ('tongji_ui',_(u'统计界面操作')),
                ('xitongshezhi_ui',_(u'系统设置界面操作')),
        )

    
        
    def __unicode__(self):
        return self.name

    def get_userlevel_permissions(self):
        return self.permissions.all()
    
    
    
def get_category_upload_path(instance,filename):
    path=os.path.join('SP',instance.user.username,filename)
    return path

class Category(MPTTModel):
    parent=TreeForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='children')
    code=models.CharField(_(u'分类编码'),blank=True,null=True,max_length=100,help_text=_(u"如果使用了条码，将设为分类编码"))
    name=models.CharField(_(u'分类名称'),max_length=50)
    cover=ThumbnailImageField(verbose_name=_(u'图像'),upload_to=get_category_upload_path,blank=True,null=True)
    description=models.CharField(_(u'分类描述'),max_length=200,blank=True,null=True)
    status=models.BooleanField(_(u'是否显示'),default=True,help_text=_(u'是否启用该分类'))
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)
    org=models.ForeignKey(Organization,null=True,blank=True)
    is_global=models.BooleanField(default=True)
    index=models.IntegerField(_(u'分类索引'),default=1,help_text=_(u'分类索引越大,在排序的时候越靠前'))
    
    user=models.ForeignKey(User,null=True,blank=True)
    
    #兼容retail版本
    slu_id=models.IntegerField(_(u'分类slu_id'),null=True,blank=True)
    slu_type=models.IntegerField(_(u'分类添加类型'),default=1,choices=((1,_(u'手动添加')),(2,_(u'已同步')))) #自动同步为2，包含手动添加后自动同步的
    
    class Meta:
        verbose_name='分类'
        verbose_name_plural="分类"
        unique_together = (("name","parent","org"))
        ordering=('-index',)
        
    class MPTTMeta:
        order_insertion_by = ['-index']
        
    def __unicode__(self):
        return self.name
    
    def serialize_to_json(self,org_or_id):
        org=isinstance(org_or_id, Organization) and org_or_id or Organization.objects.get(pk=org_or_id)
        return simplejson.dumps(self.serializable_object(org))

    def serializable_object(self,org):
        if self.is_global or self.org==org:
            if self.cover:
                obj = {'id':self.pk ,'pId':self.parent and self.parent_id or 0, 'open':True ,'name': self.name, 'isParent':True, 'status':self.status, 'icon':self.cover.thumb_url, 'children': []}
            else:
                obj = {'id':self.pk,'pId':self.parent and self.parent_id or 0 , 'open':True , 'name': self.name, 'isParent':True, 'status':self.status, 'children': []}
                

            for child in self.get_children():
                o=child.serializable_object(org)
                if o:
                    obj['children'].append(o)
                      
            return obj

    #物品页面显示分类
    def serializable_object_goodspage(self,org):
        if self.is_global or self.org==org:
            if self.cover:
                obj = {'id':self.pk ,'pId':self.parent and self.parent_id or 0, 'open':True ,'name': self.name, 'isParent':True, 'icon':self.cover.thumb_url, 'children': []}
            else:
                obj = {'id':self.pk,'pId':self.parent and self.parent_id or 0 , 'open':True , 'name': self.name, 'isParent':True, 'children': []}
                

            for child in self.get_children():
                if child.status ==1:
                    o=child.serializable_object(org)
                else:
                    continue
                if o:
                    obj['children'].append(o)
                      
            return obj

'''
    基准商品
'''
class GoodsBase(MPTTModel):
    parent=TreeForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='children')
    cover=ThumbnailImageField(verbose_name=_(u'图像'),upload_to='GB',blank=True,null=True)
    name=models.CharField(_(u'名称'),max_length=100)
    
'''
    商品
'''
def get_product_upload_path(instance,filename):
    path=os.path.join('SPD',instance.last_modify_user.username,filename)
    return path

class Goods(models.Model):
    code=models.CharField(_(u'物品编码'),max_length=100,blank=True,help_text=_(u"如果使用了条码，可将条码号设置为编码值"))
    name=models.CharField(_(u'物品名称'),max_length=50)
    base=models.ForeignKey(GoodsBase,null=True,blank=True)
    
    category=models.ForeignKey(Category,verbose_name=_(u'物品分类'),related_name='goods')
    brand=models.ForeignKey('Brand',verbose_name=_(u'品牌'),blank=True,null=True)
    
    is_batchs=models.IntegerField(_(u'是否进行分批管理'),default=0,choices=((1,_(u'分批管理')),(0,_(u'汇总管理'))),help_text=_(u'如果分批管理，每次入库将会独立批次，汇总管理则会忽略批次，仅汇总管理的物品可以自动出库'))
    is_sn=models.IntegerField(_(u'是否需要唯一码(SN)'),default=0,choices=((0,_(u'不需要')),(1,_(u'需要'))),help_text=_(u'如果使用SN，则所有物品都需要输入其唯一码'))
    
    cover=ThumbnailImageField(verbose_name=_(u'图像'),upload_to=get_product_upload_path,blank=True,null=True)
    ABC=models.IntegerField(_(u'ABC分类'),default=0,choices=((0,_(u'待定')),(1,_(u'A类')),(2,_(u'B类')),(3,_(u'C类'))))
    
    standard=models.CharField(_(u'物品规格'),null=True,blank=True,max_length=20)
    unit=models.ForeignKey('Unit',verbose_name=_(u'物品单位'),blank=True,null=True,limit_choices_to={'parent__isnull':True},on_delete=models.SET_NULL)
    nums=models.FloatField(_(u'库存数量'),default=0)
    
    abbreviation=models.CharField(_(u'助查码'),max_length=50)
    
    refer_price=models.FloatField(_(u'物品成本价格'),default=0,help_text=_(u'物品配置时的参考成本价格'))
    customer_price=models.FloatField(_(u'用户定义的成本价格'),default=0,help_text=_(u'例如用户可以定义最近1个月的采购价为平均价，如果指定了此项，则在成本管理中将使用该价格作为成本价'))
    customer_price_life=models.IntegerField(_(u'计算时间'),blank=True,null=True,help_text=_(u'这段时间内的物品价格将作为成本价'))
    customer_price_life_type=models.IntegerField(_(u'计算期限'),blank=True,null=True,choices=DATE_UNIT_TYPES,default=1)
    chengben_type=models.IntegerField(_(u'计算成本时价格'),default=1,choices=((1,_(u'加权平均后价格')),(2,_(u'最近价格')),(3,_(u'用户指定类型'))))
    
    add_nums=models.FloatField(u'累计数量',default=0,help_text=_(u'入库时增加'))
    
    shelf_life=models.IntegerField(_(u'保质期'),blank=True,null=True)
    shelf_life_type=models.IntegerField(_(u'保质单位'),blank=True,null=True,choices=DATE_UNIT_TYPES,default=1)
    min_warning=models.FloatField(_(u'下限报警'),default=-1,help_text=_(u'下限报警，小于0时忽略'))
    max_warning=models.FloatField(_(u'上限报警'),default=-1,help_text=_(u'上限报警，小于0时忽略'))
    warning_day=models.IntegerField(_(u'批次到期提醒天数'),null=True,blank=True,help_text=_(u'留空使用全局设定值天数，设为小于1的数不提醒'))
    batch_range=models.IntegerField(_(u'列出批次范围'),default=30,help_text=_(u'对于批次货物，在使用时列出多少天内的批次，覆盖全局设置'))
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    last_modify_user=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True)
    status=models.IntegerField(_(u'是否生效'),default=True,choices=((1,_(u'使用')),(0,_(u'不使用'))))
    
    org=models.ForeignKey(Organization)
    is_global=models.BooleanField(_(u'是对所有分部开放'),default=True,help_text=_(u'不开放时，其他分部不能看到该物品'))
    
    help_class=models.CharField(max_length=500,blank=True,null=True)
    index=models.IntegerField(_(u'物品索引'),blank=True,null=True,default=1,help_text=_(u'物品索引越大,在排序的时候越靠前'))
    
    profit=models.FloatField(_(u'利润'),null=True,blank=True)
    percent1=models.FloatField(null=True,blank=True)
    percent2=models.FloatField(null=True,blank=True)
    
    price=models.FloatField(_(u'最近成本价格'),default=0)
    sale_price=models.FloatField(_(u'销售价格'),default=0,help_text=_(u'参考销售价格，会根据单据自动更新'))
    
    price_ori=models.FloatField(_(u'预估成本'),default=0,help_text=_(u'用户指定,不会改变'))
    sale_price_ori=models.FloatField(_(u'预估价格'),default=0,help_text=_(u'用户指定,不会改变'))
    
    last_in_time=models.DateTimeField(_(u'最近入库时间'),null=True,blank=True)
    last_out_time=models.DateTimeField(_(u'最近出库时间'),null=True,blank=True)
    last_in_num=models.FloatField(_(u'最近入库数量'),default=0,null=True,blank=True)
    last_out_num=models.FloatField(_(u'最近出库数量'),default=0,null=True,blank=True)
    last_in_unit=models.ForeignKey('Unit',related_name='last_in_unit',blank=True,null=True,on_delete=models.SET_NULL)
    last_out_unit=models.ForeignKey('Unit',related_name='last_out_unit',blank=True,null=True,on_delete=models.SET_NULL)
    
    last_month_in_num=models.FloatField(_(u'本月入库数量'),default=0,null=True,blank=True)
    last_month_out_num=models.FloatField(_(u'本月出库数量'),default=0,null=True,blank=True)
    last_month_in_unit=models.ForeignKey('Unit',related_name='last_month_in_unit',blank=True,null=True,on_delete=models.SET_NULL)
    last_month_out_unit=models.ForeignKey('Unit',related_name='last_month_out_unit',blank=True,null=True,on_delete=models.SET_NULL)
    last_month_in_avg=models.FloatField(_(u'本月入库均价'),default=0,null=True,blank=True)
    last_month_out_avg=models.FloatField(_(u'本月出库均价'),default=0,null=True,blank=True)
    
    last_30days_in_num=models.FloatField(_(u'30天入库数量'),default=0,null=True,blank=True)
    last_30days_out_num=models.FloatField(_(u'30天出库数量'),default=0,null=True,blank=True)
    last_30days_in_unit=models.ForeignKey('Unit',related_name='last_30days_in_unit',blank=True,null=True,on_delete=models.SET_NULL)
    last_30days_out_unit=models.ForeignKey('Unit',related_name='last_30days_out_unit',blank=True,null=True,on_delete=models.SET_NULL)
    last_30days_in_avg=models.FloatField(_(u'30天入库均价'),default=0,null=True,blank=True)
    last_30days_out_avg=models.FloatField(_(u'30天出库均价'),default=0,null=True,blank=True)
    
    
    #兼容retail版本
    #item_id=models.IntegerField(_(u'菜品ID'),null=True,blank=True)
    item_type=models.IntegerField(_(u'是否为销售商品'),default=1,choices=((1,_(u'是销售商品')),(2,_(u'不是销售商品'))),help_text=_(u'销售商品将会被同步到收银')) #自动同步为2，包含手动添加后自动同步的
    
    
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name=_(u'物品')
        unique_together = (("category", "name",'standard'),)
        db_table="depot_good"
        ordering=['category','-index','id']
    
    '''
    '    得到辅助单位
    '''    
    def units(self):
        if self.unit_id:
            units=Unit.objects.filter(good=self)
            return units
        else:
            return None
    @property
    def get_name(self):
        return self.name
        
    '''
    '    得到辅助单位的价格
    '''
    def get_unit_price(self,unit):
        if not self.unit or not unit or self.unit==unit:
            return self.price_ori or 0,self.sale_price_ori or 0
        else:
            unit=Unit.objects.get(pk=unit.pk)
            return unit.price or 0,unit.sale_price or 0
            
     
    '''
    '    根据单位换算成相应的值
    '''   
    def change_nums(self,num,from_unit,to_unit=None):
    
        to_unit=to_unit and to_unit or self.unit
        if self.unit and from_unit:
            rate_from=from_unit.rate or 1
            rate_to=to_unit.rate or 1
    
            if rate_from>0:
                num=num*rate_from
            else:
                num=num/abs(rate_from)
                
            if rate_to>0:
                num=num/rate_to
            else:
                num=num*abs(rate_to)
            
        return num
    
    
    '''
    '    更新成本价,并同步更新
    '''
    def update_chengben(self,commit=False):
        from cost.models import MenuItem
        if self.chengben_type==3 and self.customer_price_life:
            invoices=Invoice.objects.filter(status=2,details__good=self,invoice_type__in=[1001,1000]).order_by('-event_date')
            if not invoices.exists():
                return False
            
            end_day=invoices[0].event_date
            start=datedelta(end_day,-self.customer_price_life,self.customer_price_life_type)
            invoices=invoices.filter(event_date__gte=start,status=2,invoice_type__in=[1001,1000])
            
            total_and_price=InvoiceDetail.objects.filter(invoice__in=invoices,good=self,total_price__gt=0).aggregate(total=Sum('total_price'),num=Sum('num'))
            self.customer_price=total_and_price['num'] and (total_and_price['total']/total_and_price['num']) or 0
    
            #如果菜品中有同编码的物品，更新其成本价
            '''
            ' 在这里得到并不合适，应该在原材料配置的地方
            '''
            units=Unit.objects.filter(good=self)
            for menuItem in MenuItem.objects.filter(nlu=self.code):

                if menuItem.unit==self.unit.unit or not menuItem.unit:
                    #没有单位或等于主单位
                    menuItem.cost=self.chengben_price
                    menuItem._percent=1
                    #menuItem.save() #暂时不用
                    
                elif units.filter(unit=menuItem.unit).exists():
                    unit=units.filter(unit=menuItem.unit)[0]
                    #如果设置了辅助单位价格，按照辅助单位价格计算
                    menuItem.cost=unit.price or self.change_nums(1,unit)*self.chengben_price
                    menuItem._percent=1
                    #menuItem.save() #暂时不用
            
            #更新与之相关的菜品利润表
            if commit:
                #self.save()
                update_model(self,customer_price=self.customer_price)
                
    
    '''
    '根据设置，得到物品的成本价
    '''            
    @property
    def chengben_price(self):
        
        #return [self.refer_price,self.price,self.customer_price or self.price][self.customer_price_life_type]
        return self.refer_price



'''
    记录物品的入库时的库位历史
'''
class GoodsHisShelf(models.Model):
    good=models.ForeignKey(Goods,on_delete=models.CASCADE)
    shelf=models.ForeignKey(Warehouse,on_delete=models.CASCADE)
    created_time=models.DateTimeField(auto_now_add=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
        
'''
    单位
'''    
class Unit(models.Model):
    unit=models.CharField(_(u'单位名'),max_length=10)
    des=models.CharField(_(u'单位说明'),max_length=50,blank=True,null=True)
    
    status=models.BooleanField(default=1)
    org=models.ForeignKey(Organization)
    is_global=models.BooleanField(u'是对所有仓库开放',default=False)
    
    #一下为辅助单位使用
    parent=models.ForeignKey('self',blank=True,null=True,on_delete=models.CASCADE,related_name='auxiliary_units')
    good=models.ForeignKey(Goods,on_delete=models.CASCADE,related_name='auxiliary_unit',blank=True,null=True)
    rate=models.FloatField(_(u'换算比率'),blank=True,null=True)
    price=models.FloatField(_(u'辅助单位价格'),blank=True,null=True)
    sale_price=models.FloatField(_(u'辅助单位销售价格'),blank=True,null=True)
    
    class Meta:
        verbose_name=_(u'单位')
        db_table="depot_unit"
        #unique_together=('unit','org')
        
    def __unicode__(self):
        return self.unit  
    
    
'''
    品牌
''' 
class Brand(models.Model):
    brand=models.CharField(_(u'品牌名'),max_length=50)
    des=models.CharField(_(u'单位说明'),max_length=50,blank=True,null=True)
    
    status=models.BooleanField(default=1)
    org=models.ForeignKey(Organization)
    is_global=models.BooleanField(u'是对所有仓库开放',default=False)
    
    class Meta:
        verbose_name=_(u'品牌')
        db_table="depot_brand"
        unique_together=('brand','org')
        
    def __unicode__(self):
        return self.brand     
        
        
'''
    领用部门
'''
class ConDepartment(models.Model):
    name=models.CharField(_(u'部门名称'),max_length=50)
    abbreviation=models.CharField(_(u'助查码'),max_length=50)
    address=models.CharField(_(u'部门地址'),max_length=100,blank=True,null=True)
    org=models.ForeignKey(Organization)
    
    phone=models.CharField(_(u'联系人手机'),max_length=20,blank=True,null=True)
    tel=models.CharField(_(u'办公电话'),max_length=20,blank=True,null=True)
    fax=models.CharField(_(u'传真'),max_length=20,blank=True,null=True)
    contact=models.CharField(_(u'联系人'),max_length=20,blank=True,null=True)
    email=models.EmailField(_(u'邮箱'),blank=True,null=True)
    status=models.BooleanField(_(u'状态'),default=1)
    zip_code=models.CharField(_(u'邮编'),max_length=20,blank=True,null=True)
    remark=models.TextField(blank=True,null=True)
    
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    count=models.IntegerField(_(u'领用次数'),default=0)
    money=models.FloatField(_(u'领用金额'),default=0)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name=_(u'领用部门')
        db_table="depot_condepartment"
        unique_together=('name','org')

'''
    供货商
'''
class Supplier(models.Model):
    name=models.CharField(_(u'供货商名称'),max_length=50)
    abbreviation=models.CharField(_(u'助查码'),max_length=50)
    
    
    province=models.ForeignKey(City,related_name='province_suppliers',verbose_name=_(u'所在省份'),blank=True,null=True)
    city=models.ForeignKey(City,related_name='city_suppliers',verbose_name=_(u'所在市'),blank=True,null=True)
    district=models.ForeignKey(City,related_name='district_suppliers',verbose_name=_(u'所在县/区'),blank=True,null=True)
    area=models.ForeignKey(City,related_name='area_suppliers',verbose_name=_(u'所在街道'),blank=True,null=True)
    
    address=models.CharField(_(u'供货商地址'),max_length=100,blank=True,null=True)
    org=models.ForeignKey(Organization)
    
    phone=models.CharField(_(u'供货商手机'),max_length=20,blank=True,null=True)
    tel=models.CharField(_(u'办公电话'),max_length=20,blank=True,null=True)
    fax=models.CharField(_(u'传真'),max_length=20,blank=True,null=True)
    contact=models.CharField(_(u'联系人'),max_length=20,blank=True,null=True)
    email=models.EmailField(_(u'邮箱'),blank=True,null=True)
    status=models.BooleanField(_(u'状态'),default=1)
    zip_code=models.CharField(_(u'供货商邮编'),max_length=20,blank=True,null=True)
    remark=models.TextField(blank=True,null=True)
    
    group=models.ForeignKey('SupplierGroup',verbose_name=_(u'所属分组'),blank=True,null=True)
    tax=models.CharField(_(u'税号'),max_length=20,blank=True,null=True)
    account=models.CharField(_(u'账号'),max_length=50,blank=True,null=True)
    bank=models.CharField(_(u'开户行'),max_length=50,blank=True,null=True)
    invoice_address=models.CharField(_(u'邮寄地址'),max_length=50,blank=True,null=True)
    
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    count=models.IntegerField(_(u'采购次数'),default=0)
    money=models.FloatField(_(u'采购金额'),default=0)
    
    def __unicode__(self):
        return self.name 
    
    class Meta:
        verbose_name=_(u'供货商')
        db_table="depot_supplier"
        unique_together=('name','org')
    
'''
    供货商分组
'''
class SupplierGroup(models.Model):
    name=models.CharField(_(u'名称'),max_length=50)
    status=models.BooleanField(_(u'状态'),default=1)
    remark=models.CharField(max_length=200,blank=True,null=True)
    org=models.ForeignKey(Organization)
    
    class Meta:
        verbose_name=_(u'供货商分组')
        db_table="depot_suppliergroup"
        unique_together=('name','org')
        
    def __unicode__(self):
        return self.name
        
        
'''
    客户
    status为-1时为内置用户，仅能看到
'''
class Customer(models.Model):
    name=models.CharField(_(u'客户名称'),max_length=50)
    abbreviation=models.CharField(_(u'助查码'),max_length=50)
    address=models.CharField(_(u'客户地址'),max_length=100,blank=True,null=True)
    org=models.ForeignKey(Organization)
    
    customer_type=models.IntegerField(_(u'客户类型'),default=1,choices=((1,_(u'公司')),(2,_(u'个人'))))
    
    phone=models.CharField(_(u'客户手机'),max_length=20,blank=True,null=True)
    tel=models.CharField(_(u'办公电话'),max_length=20,blank=True,null=True)
    fax=models.CharField(_(u'传真'),max_length=20,blank=True,null=True)
    contact=models.CharField(_(u'联系人'),max_length=20,blank=True,null=True,help_text=_(u'客户类型为公司时，公司联系人'))
    email=models.EmailField(_(u'邮箱'),blank=True,null=True)
    status=models.BooleanField(_(u'状态'),default=1)
    zip_code=models.CharField(_(u'邮编'),max_length=20,blank=True,null=True)
    remark=models.TextField(blank=True,null=True)
    
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    count=models.IntegerField(_(u'消费次数'),default=0)
    money=models.FloatField(_(u'消费金额'),default=0)
    
    def __unicode__(self):
        return self.name 
    
    class Meta:
        verbose_name=_(u'客户')
        db_table="depot_customer"
        unique_together=('name','org')
    
    
'''
    客户分组
'''
class CustomerGroup(models.Model):
    name=models.CharField(_(u'名称'),max_length=50)
    status=models.BooleanField(_(u'状态'),default=1)
    remark=models.TextField(blank=True,null=True)
    org=models.ForeignKey(Organization)
    
    class Meta:
        verbose_name=_(u'客户分组')
        db_table="depot_customergroup"
        unique_together=('name','org')
                
#销售类型
class SaleType(models.Model):
    name=models.CharField(_(u'类型名称'),blank=True,max_length=200)
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)

    def __unicode__(self):
        return self.name

'''
    '盘点单
'''
class SnapshotWarehouse(models.Model):
    warehouse=models.ForeignKey(Warehouse,related_name='snapshots',blank=True,null=True)
    modify_time=models.DateTimeField(auto_now=True)
    created_time=models.DateField(auto_now_add=True)
    created_user=models.ForeignKey(User,blank=True,null=True)
    status=models.IntegerField(default=0,choices=((0,_(u'草稿')),(1,_(u'待盘点')),(2,_(u'已审核'))))  #1-待盘点 #0-已删除 2-已确认
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    shelf=models.ForeignKey('Warehouse',related_name='shelfSnapshot',null=True,blank=True)
    confirm_time=models.DateTimeField(blank=True,null=True)
    is_delete=models.BooleanField(_(u'已删除'),default=False)
    confirm_user=models.ForeignKey(User,null=True,blank=True,verbose_name=_(u'审核人'),related_name="confirm_user")
    
    class Meta:
        verbose_name=_(u'盘点单')        
        db_table="depot_snapshotwarehouse"
        ordering=['-id']
        
    def __unicode__(self):
        return u'%s%s'%(self.warehouse.name,_(u'盘点'))
    
    @property
    def description(self):
        return u'%s[%s]'%(self.warehouse,self.created_time.strftime('%Y-%m-%d %H:%M:%S'))

    def get_modify_url(self):
        return reverse('list_goods_pandian_preview',args=[self.org.pk,self.pk])
    
    def confirm(self,confirm_user):
        snapshotWarehouse=self
        created_panying=False
        created_pankui=False
        panying_invoice=None
        pankui_invoice=None
        self.confirm_user = confirm_user

        '''try:
            invoice=Invoice.objects.get(content_type=ContentType.objects.get_for_model(snapshotWarehouse),object_id=snapshotWarehouse.pk)
        except:
            create_invoice=True
            invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),status=1,org=self.org,warehouse_root=self.warehouse,
                                            event_date=snapshotWarehouse.created_time,invoice_type=9999,content_object=snapshotWarehouse,charger=self.created_user,
                                            user=self.created_user,confirm_user=self.created_user,remark=None)
        '''

        for _good in snapshotWarehouse.goods.all():
            good=_good.good
            if _good.is_batchs:
                for _detail in _good.details.all():
                    
                    if not _detail.pancha:
                        continue
                    
                    try:
                        detail=InvoiceDetail.objects.filter(batch_code=_detail.batch_code,invoice__status=2,invoice__invoice_type__in=IN_BASE_TYPE)[0]
                        
                        #detail.last_nums+=_detail.pancha
                        #detail.save()
                        rel_batch=True
                        num=good.change_nums(_detail.pancha,detail.unit1)
                    except:
                        rel_batch=False
                        num=_detail.pancha
                         
                    if create_invoice:
                        
                        if rel_batch:
                            #InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code="P_%s_%s_pd"%(invoice.pk,_detail.pk),warehouse=detail.warehouse,warehouse_root=detail.warehouse_root,remark=_detail.batch_code,
                            #                         status=-1,num1=_detail.pancha,unit1=detail.good.unit,price=detail.avg_price,num=_detail.pancha,avg_price=detail.avg_price,last_nums=0,total_price=detail.avg_price*_detail.pancha)
                            InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code="P_%s_%s_pd"%(invoice.pk,_detail.pk),warehouse=detail.warehouse,warehouse_root=detail.warehouse_root,remark=_detail.batch_code,
                                                     num1=_detail.pancha,unit1=detail.good.unit,price=detail.avg_price,num=_detail.pancha,avg_price=detail.avg_price,last_nums=num,total_price=detail.avg_price*_detail.pancha)
                        else:
                            InvoiceDetail.objects.create(invoice=invoice,good=good,batch_code=InvoiceDetail.get_next_detail_code(),warehouse=self.shelf,warehouse_root=self.warehouse,
                                                     num1=_detail.pancha,unit1=_good.unit,price=_detail.price,num=_detail.pancha,avg_price=_detail.price,last_nums=num,total_price=_detail.total_price)
                                
                    good.nums = _detail.shiji
                    good.save()
            else:
                
                if not _good.pancha:
                    continue

                if _good.pancha>0:
                    if created_panying:
                        InvoiceDetail.objects.create(invoice=panying_invoice,good=good,warehouse=self.shelf,warehouse_root=self.warehouse,
                                                 num1=_good.pancha,unit1=good.unit,price=good.sale_price_ori,num=_good.pancha,avg_price=good.sale_price_ori,last_nums=_good.pancha,total_price=good.sale_price_ori*_good.pancha,
                                                 chenben_price=good.price_ori*_good.pancha,remark=None)
                    else:
                        self.confirm_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        panying_invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),status=2,invoice_type=9000,org=self.org,event_date=time.strftime('%Y-%m-%d',time.localtime(time.time())),charger=self.confirm_user,user=self.confirm_user,confirm_user=self.confirm_user,remark="自动生成盘盈单",confirm_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),pandian_relate=self,content_object=self,warehouse_root=self.warehouse)
                        InvoiceDetail.objects.create(invoice=panying_invoice,good=good,warehouse=self.shelf,warehouse_root=self.warehouse,
                                                 num1=_good.pancha,unit1=good.unit,price=good.sale_price_ori,num=_good.pancha,avg_price=good.sale_price_ori,last_nums=_good.pancha,total_price=good.sale_price_ori*_good.pancha,
                                                 chenben_price=good.price_ori*_good.pancha,remark=None)
                        created_panying = True

                elif _good.pancha<0:
                    if created_pankui:
                        InvoiceDetail.objects.create(invoice=pankui_invoice,good=good,warehouse=self.shelf,warehouse_root=self.warehouse,
                                                 num1=-_good.pancha,unit1=good.unit,price=good.sale_price_ori,num=-_good.pancha,avg_price=good.sale_price_ori,last_nums=-_good.pancha,total_price=good.sale_price_ori*-_good.pancha,
                                                 chenben_price=good.price_ori*-_good.pancha,remark=None)
                    else:
                        self.confirm_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                        pankui_invoice=Invoice.objects.create(invoice_code=Invoice.get_next_invoice_code(),status=2,invoice_type=9001,org=self.org,event_date=time.strftime('%Y-%m-%d',time.localtime(time.time())),charger=self.confirm_user,user=self.confirm_user,confirm_user=self.confirm_user,remark="自动生成盘亏单",confirm_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),pandian_relate=self,content_object=self,warehouse_root=self.warehouse)
                        InvoiceDetail.objects.create(invoice=pankui_invoice,good=good,warehouse=self.shelf,warehouse_root=self.warehouse,
                                                 num1=-_good.pancha,unit1=good.unit,price=good.sale_price_ori,num=-_good.pancha,avg_price=good.sale_price_ori,last_nums=-_good.pancha,total_price=good.sale_price_ori*-_good.pancha,
                                                 chenben_price=good.price_ori*-_good.pancha,remark=None)
                        created_pankui = True

                else:
                    continue


                #if create_invoice:
                    #InvoiceDetail.objects.create(invoice=invoice,good=good,warehouse=self.shelf,warehouse_root=self.warehouse,
                                                 #num1=_good.pancha,unit1=good.unit,price=good.refer_price,num=_good.pancha,avg_price=good.refer_price,last_nums=_good.pancha,total_price=good.refer_price*_good.pancha,
                                                 #remark=None)
                
                good.nums = _good.shiji
                print "asdfghj",good,good.nums
                
                good.save() 
                
        snapshotWarehouse.status=2
        snapshotWarehouse.save()
        
        
        if panying_invoice:
            panying_invoice.total_price=panying_invoice.details.all().aggregate(sum_total_price=Sum('total_price'))['sum_total_price'] or 0
            panying_invoice.sale_price=panying_invoice.details.all().aggregate(sum_sale_price=Sum('chenben_price'))['sum_sale_price'] or 0
            panying_invoice.save()
        if pankui_invoice:
            pankui_invoice.total_price=pankui_invoice.details.all().aggregate(sum_total_price=Sum('total_price'))['sum_total_price'] or 0
            pankui_invoice.sale_price=pankui_invoice.details.all().aggregate(sum_sale_price=Sum('chenben_price'))['sum_sale_price'] or 0
            pankui_invoice.save()
        #invoice.status=2
        #invoice.save()

        return snapshotWarehouse.status
                
        
    def unconfirm(self):
        snapshotWarehouse=self
        #invoice=Invoice.objects.get(content_type=ContentType.objects.get_for_model(snapshotWarehouse),object_id=snapshotWarehouse.pk)
        for _good in snapshotWarehouse.goods.all():
            if not _good.good.details.exists():
                continue
            good=_good.good
            if _good.is_batchs:
                for _detail in _good.details.all():
                   
                    detail=InvoiceDetail.objects.filter(pk=_detail.detail_id,invoice__status=2,invoice__invoice_type__in=IN_BASE_TYPE)[0]
                    if not _detail.pancha:
                        continue
                    detail.last_nums = _detail.last_nums
                    detail.save()
                        
                    good.nums = _detail.last_nums
                    good.save()
            else:
                #先减去盘差数量
                
                #try:
                    #snapshotDetail=invoice.details.get(good=good)
                #except:
                    #continue
            
                #detail=InvoiceDetail.objects.filter(good=good,warehouse__in=snapshotWarehouse.shelf.get_descendants(include_self=True),warehouse_root=snapshotWarehouse.warehouse,invoice__status=2,invoice__invoice_type__in=IN_BASE_TYPE)[0]
                if not _good.pancha:
                    continue
                #detail.last_nums-=(_good.pancha-snapshotDetail.last_nums)
                #detail.save()

                good.nums = _good.last_nums

                good.save() 
                
        snapshotWarehouse.status=1

        snapshotWarehouse.invoice_set.all().delete()
        snapshotWarehouse.save()
        
        
        #invoice.status=1
        #invoice.save() 
        
        return snapshotWarehouse.status

'''
    单据
'''
class Invoice(models.Model):
    invoice_code=models.CharField(_(u'单据编号'),max_length=100,blank=True,null=True)
    voucher_code=models.CharField(_(u'凭证号'),max_length=100,blank=True,null=True)
    result=models.BooleanField(_(u'已结款'),default=False)
    status=models.IntegerField(_(u'单据状态'),default=1,choices=INVOICE_STATUS) #0--草稿，不生效  1-开始申请  2--已审核
    org=models.ForeignKey(Organization)
    warehouse_root=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'仓库'),related_name='wr_invoices')
    
    event_date=models.DateField(_(u'日期'))
    invoice_type=models.IntegerField(_(u'单据类型'),choices=INVOICE_TYPES)
    
    content_type=models.ForeignKey(ContentType)
    object_id=models.PositiveIntegerField()
    content_object=GenericForeignKey('content_type', 'object_id')
    
    charger=models.ForeignKey(User,related_name='charger_invoices')
    user=models.ForeignKey(User,verbose_name=_(u'经办人'))
    confirm_user=models.ForeignKey(User,null=True,blank=True,verbose_name=_(u'审核人'),related_name='confirm_invoices')
    
    total_price=models.FloatField(default=0)
    sale_price=models.FloatField(_(u'这个其实是成本价'),default=0,blank=True,null=True)

    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)

    #销售类型
    sale_type=models.ForeignKey(SaleType,on_delete=models.SET_NULL,blank=True,null=True)

    #是否删除
    is_delete=models.BooleanField(_(u'已删除'),default=False)
    #审核时间
    confirm_time=models.DateTimeField(blank=True,null=True)
    #单据来源，记录与其相关的单据
    invoice_from=models.ForeignKey('self',blank=True,null=True,on_delete=models.SET_NULL,verbose_name=_(u'相关单据'))
    pandian_relate=models.ForeignKey(SnapshotWarehouse,on_delete=models.CASCADE,null=True,blank=True,verbose_name=_(u'相关盘点单据'))

    def __unicode__(self):
        return self.invoice_code

    def get_absolute_url(self):
        return reverse('invoice_view',args=[self.org.pk,self.pk])
    
    @property
    def get_num_prefix(self):
        if 1999<self.invoice_type<2999 or self.invoice_type==9001:
            return '-'
        return ''
    
    @property
    def get_invoice_rel(self):
        if self.invoice_type==1009:
            return self.content_object.warehouse_root
        elif self.invoice_type==2009:
            return self.content_object.content_object
        else:
            return self.content_object

    @property
    def get_invoice_type_name(self):
        if self.invoice_type == 1004:
            return "采购申请单"
        if self.invoice_type == 1001:
            return "采购入库单"
        if self.invoice_type == 1000:
            return "初始入库单"
        if self.invoice_type == 2001:
            return "领用出库单"
        if self.invoice_type == 2002:
            return "销售出库单"
        if self.invoice_type == 2000:
            return "采购退货单"
        if self.invoice_type == 9000:
            return "盘盈入库单"
        if self.invoice_type == 9001:
            return "盘亏出库单"
    
    def get_modify_url(self):
        if self.invoice_type==1001:
            return reverse('caigouruku_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==1000:
            return reverse('chushiruku_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==1004:
            return reverse('caigoushenqing_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==2000:
            return reverse('caigoutuihuo_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==2001:
            return reverse('lingyongchuku_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==1002:
            return reverse('tuiliaoruku_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==2002:
            return reverse('xiaoshouchuku_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type==10000:
            return reverse('kuweidiaobo_modify',args=[self.org.pk,self.pk])
        
        elif self.invoice_type==9999:
            if self.content_object:
                return reverse('list_goods_pandian_preview',args=[self.org.pk,self.object_id])
            
    
    class Meta:
        verbose_name=_(u'单据')
        ordering=['-event_date','-id']
        db_table="depot_ininvoice"

        '''
           @单据权限
           @2017/04/28
        '''

        permissions=(
                ('caigoushenqing_query','查询采购申请单'),
                ('caigoushenqing_add','添加采购申请单'),
                ('caigoushenqing_modify','修改采购申请单'),
                ('caigoushenqing_delete','删除采购申请单'),
                ('caigoushenqing_confirm','审核采购申请单'),
                ('caigoushenqing_print','打印采购申请单'),
                ('caigoushenqing_export','导出采购申请单'),

                ('caigouruku_query','查询采购入库单'),
                ('caigouruku_add','添加采购入库单'),
                ('caigouruku_modify','修改采购入库单'),
                ('caigouruku_delete','删除采购入库单'),
                ('caigouruku_confirm','审核采购入库单'),
                ('caigouruku_print','打印采购入库单'),
                ('caigouruku_export','导出采购入库单'),

                ('chushiruku_query','查询初始入库单'),
                ('chushiruku_add','添加初始入库单'),
                ('chushiruku_modify','修改初始入库单'),
                ('chushiruku_delete','删除初始入库单'),
                ('chushiruku_confirm','审核初始入库单'),
                ('chushiruku_print','打印初始入库单'),
                ('chushiruku_export','导出初始入库单'),

                ('caigoutuihuo_query','查询采购退货单'),
                ('caigoutuihuo_add','添加采购退货单'),
                ('caigoutuihuo_modify','修改采购退货单'),
                ('caigoutuihuo_delete','删除采购退货单'),
                ('caigoutuihuo_confirm','审核采购退货单'),
                ('caigoutuihuo_print','打印采购退货单'),
                ('caigoutuihuo_export','导出采购退货单'),

                ('xiaoshouchuku_query','查询销售出库单'),
                ('xiaoshouchuku_add','添加销售出库单'),
                ('xiaoshouchuku_modify','修改销售出库单'),
                ('xiaoshouchuku_delete','删除销售出库单'),
                ('xiaoshouchuku_confirm','审核销售出库单'),
                ('xiaoshouchuku_print','打印销售出库单'),
                ('xiaoshouchuku_export','导出销售出库单'),

                ('lingyongchuku_query','查询领用出库单'),
                ('lingyongchuku_add','添加领用出库单'),
                ('lingyongchuku_modify','修改领用出库单'),
                ('lingyongchuku_delete','删除领用出库单'),
                ('lingyongchuku_confirm','审核领用出库单'),
                ('lingyongchuku_print','打印领用出库单'),
                ('lingyongchuku_export','导出领用出库单'),

                ('tuicangruku_query','查询退仓入库单'),
                ('tuicangruku_add','添加退仓入库单'),
                ('tuicangruku_modify','修改退仓入库单'),
                ('tuicangruku_delete','删除退仓入库单'),
                ('tuicangruku_confirm','审核退仓入库单'),
                ('tuicangruku_print','打印退仓入库单'),
                ('tuicangruku_export','导出退仓入库单'),

                ('baosunchuku_query','查询报损出库单'),
                ('baosunchuku_add','添加报损出库单'),
                ('baosunchuku_modify','修改报损出库单'),
                ('baosunchuku_delete','删除报损出库单'),
                ('baosunchuku_confirm','审核报损出库单'),
                ('baosunchuku_print','打印报损出库单'),
                ('baosunchuku_export','导出报损出库单'),

                ('pandian_query','查询盘点单'),
                ('pandian_add','添加盘点单'),
                ('pandian_modify','修改盘点单'),
                ('pandian_delete','删除盘点单'),
                ('pandian_confirm','审核盘点单'),
                ('pandian_print','打印盘点单'),
                ('pandian_export','导出盘点单'),

                ('panying_query','查询盘盈单'),
                ('panying_add','添加盘盈单'),
                ('panying_modify','修改盘盈单'),
                ('panying_delete','删除盘盈单'),
                ('panying_confirm','审核盘盈单'),
                ('panying_print','打印盘盈单'),
                ('panying_export','导出盘盈单'),

                ('pankui_query','查询盘亏单'),
                ('pankui_add','添加盘亏单'),
                ('pankui_modify','修改盘亏单'),
                ('pankui_delete','删除盘亏单'),
                ('pankui_confirm','审核盘亏单'),
                ('pankui_print','打印盘亏单'),
                ('pankui_export','导出盘亏单'),



                ('huishouzhan_query','回收站查询'),
                ('huishouzhan_delete','回收站删除'),
                ('huishouzhan_restore','回收站还原'),
            )
    
    @classmethod
    def get_next_invoice_code(self):
        today=datetime.datetime.today()
        invoice_code=(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(today,'%Y%m%d'),'seq':get_next_increment(self)}).replace(' ','0')
        return invoice_code

    @classmethod
    def fix_get_next_invoice_code(self):
        today=datetime.datetime.today()
        invoice_code=(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(today,'%Y%m%d'),'seq':fix_get_next_increment(self)}).replace(' ','0')
        return invoice_code

    @classmethod
    def get_org_next_invoice_code(self,org):
        today=datetime.datetime.today()
        org_invoice_total=self.objects.filter(org=org).count()
        invoice_code=(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(today,'%Y%m%d'),'seq':org_invoice_total}).replace(' ','0')
        return invoice_code
    
    @property
    def total_price_des(self):
        return numtoCny(self.total_price)
    
    '''
    '    审核单据
    '''
    def confirm(self,user):
        strat_time = time.time()
        if self.invoice_type in (1000,1001,1009):  #审核采购入库
            if self.status!=2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    if detail.total_price:
                        good.refer_price=(good.add_nums+detail.num) and (good.refer_price*good.add_nums+detail.total_price)/(good.add_nums+detail.num) or 0
                        #good.price=detail.total_price/detail.num
                        good.update_chengben(commit=False)
                        
                    #good.add_nums+=detail.num
                    #good.nums+=detail.num
                    #good.save()
                    update_model(good,add_nums=good.add_nums+detail.num,nums=good.nums+detail.num)

                 
                if not self.payinvoice_set.all().exists():
                    PayInvoice.objects.create(org=self.org,invoice_code=PayInvoice.get_next_invoice_code(),charger=self.charger,user=self.user,total_pay=self.total_price,warehouse_root=self.warehouse_root,event_date=datetime.datetime.now(),invoice_from=self,content_object=self.get_invoice_rel,invoice_type=3000,rest_pay=self.total_price,already_pay=0)
                
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()

                #print 'save_model:' + str(time.time() - strat_time)
                return self.status
            
        elif self.invoice_type==2000: #审核采购退货
            if self.status!=2:

                
                for detail in self.details.all():
                    _last_nums=detail.num
                    good=Goods.objects.get(pk=detail.good_id)
                    if detail.total_price:
                        good.refer_price=(good.add_nums-detail.num) and ((good.refer_price*good.add_nums-detail.total_price)/(good.add_nums-detail.num)) or 0
                        good.update_chengben(commit=False)
                    #good.add_nums-=detail.num
                    #good.nums-=detail.num
                    #good.update_chengben()
                    #good.save()
                    update_model(good,add_nums=good.add_nums-detail.num,nums=good.nums-detail.num)

                    #print 'update_model:' + str(time.time() - strat_time)
                    
                    #同步批次数据
                    _last_nums=sync_batches(detail,global_confirm=True)

                    #print 'sync_batches:' + str(time.time() - strat_time)
                            
                    if _last_nums:
                        
                        return-1


                if not self.payinvoice_set.all():
                    PayInvoice.objects.create(org=self.org,invoice_code=PayInvoice.get_next_invoice_code(),charger=self.charger,user=self.user,total_pay=self.total_price,warehouse_root=self.warehouse_root,event_date=datetime.datetime.now(),invoice_from=self,content_object=self.get_invoice_rel,invoice_type=3001,rest_pay=self.total_price,already_pay=0)
                         
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()
                
                #print 'save_model:' + str(time.time() - strat_time)
                return self.status
        elif self.invoice_type in (2001,2009): #审核领用出库单
            if self.status!=2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    #good.nums-=detail.num
                    #good.save()
                    update_model(good,nums=good.nums-detail.num)

                    #print 'update_model:' + str(time.time() - strat_time)
                    
                    #同步批次数据
                    _last_nums=sync_batches(detail,global_confirm=True)

                    #print 'sync_batches:' + str(time.time() - strat_time)
                    if _last_nums:
                        return u'%s库存数量不够'%detail.good
                    
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()

                
                #print 'save_model:' + str(time.time() - strat_time)
                
                return self.status   
        elif self.invoice_type==1002: #审核退料入库
            if self.status!=2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    #good.nums+=detail.num
                    #good.save()
                    update_model(good,nums=good.nums+detail.num)

                    #print 'update_model:' + str(time.time() - strat_time)
                    
                    ret=sync_tuiliao(detail,global_confirm=False)

                    #print 'sync_tuiliao:' + str(time.time() - strat_time)
                    if ret:
                        return ret
                    
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()
                
                #print 'save_model:' + str(time.time() - strat_time)
                return self.status
        elif self.invoice_type==2002:
            #审核销售出库

            if self.status!=2:
                count_t = 0
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    #good.nums-=detail.num
                    #good.save()
                    update_model(good,nums=good.nums-detail.num)

                    #print 'update_model:' + str(time.time() - strat_time)
                    
                    #同步批次数据
                    _last_nums=sync_batches(detail,global_confirm=True)

                    #print 'sync_batches:' + str(time.time() - strat_time)
                    
                    if _last_nums:
                        return u'%s库存数量不够'%detail.good


                if not self.payinvoice_set.all():
                    PayInvoice.objects.create(org=self.org,invoice_code=PayInvoice.get_next_invoice_code(),charger=self.charger,user=self.user,total_pay=self.total_price,warehouse_root=self.warehouse_root,event_date=datetime.datetime.now(),invoice_from=self,content_object=self.get_invoice_rel,invoice_type=3001,rest_pay=self.total_price,already_pay=0)
                    
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()

                #print 'save_model:' + str(time.time() - strat_time)

                return self.status
        elif self.invoice_type==9999: #审核盘盈盘亏
            if self.status!=2:
                '''
                ' 是否来自盘点单和单品盘点不一样
                '''
                if ContentType.objects.get_for_model(self.content_object)==ContentType.objects.get_for_model(User):
                    self.confirm_user=user    
                    self.status=2

                    self.save()
                    
                    return self.status
                else:
                    if self.content_object:
                        return self.content_object.confirm()
                
        elif self.invoice_type==10000: #调拨
            if self.status!=2:
                invoice_content=ContentType.objects.get_for_model(self)
                out_invoice=Invoice.objects.get(invoice_type=2009,content_type=invoice_content,object_id=self.pk)
                in_invoice=Invoice.objects.get(invoice_type=1009,content_type=invoice_content,object_id=self.pk)  
                
                ret=out_invoice.confirm(user) 
                if ret!=2:
                    return ret
                
                ret=in_invoice.confirm(user)
                if ret!=2:
                    return ret
                
                self.confirm_user=user    
                self.status=2
                self.confirm_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                self.save()
                
                return self.status
                
                
        
    '''
    '    反审核单据
    '''
    def unconfirm(self):
        if self.invoice_type in (1000,1001,1009):
            #if self.status==2:
                #for detail in self.details.all():
                    #if detail.num!=detail.last_nums:
                        #return -1 #已经使用的单据，不能再被反审核
                    
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    if detail.total_price:
                        good.refer_price=(good.add_nums-detail.num) and ((good.refer_price*good.add_nums-detail.total_price)/(good.add_nums-detail.num)) or 0
                        good.update_chengben()
                    #good.add_nums-=detail.num
                    #good.nums-=detail.num
                    #good.update_chengben()
                    
                    #good.save()
                    update_model(good,nums=good.nums-detail.num,add_nums=good.add_nums-detail.num)    
                    
                self.status=0
                self.result = False
                self.save()
                
                
                return self.status
            
        elif self.invoice_type==2000: #反审核采购退货
            if self.status==2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    if detail.total_price:
                        good.refer_price=(good.add_nums+detail.num) and (good.refer_price*good.add_nums+detail.total_price)/(good.add_nums+detail.num) or 0
                        good.update_chengben(commit=False)
                    good.add_nums+=detail.num
                    good.nums+=detail.num
                    #good.update_chengben()
                    
                    good.save()
                    
                    unsync_batches(detail,global_confirm=True)
                
                self.num_at_that_time = None            
                self.status=0
                self.save()
                
                
                return self.status
        elif self.invoice_type in (2001,2009): #反审核领用出库单
            if self.status==2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    update_model(good,nums=good.nums+detail.num)
                    #good.nums+=detail.num
                    #good.save()
                    
                    ret=unsync_batches(detail,global_confirm=False)
                    if ret:
                        return ret
                self.num_at_that_time = None    
                self.status=0
                self.save()
                
                return self.status
        elif self.invoice_type==1002: #反审退料入库库单
            if self.status==2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    update_model(good,nums=good.nums-detail.num)
                    #good.nums-=detail.num
                    #good.save()
                    
                    ret=unsync_tuiliao(detail,global_confirm=True)
                    if ret:
                        return ret
                     
                self.status=0
                self.save()
                
                return self.status
        elif self.invoice_type==2002: #反审销售出库单
            if self.status==2:
                for detail in self.details.all():
                    good=Goods.objects.get(pk=detail.good_id)
                    
                    update_model(good,nums=good.nums+detail.num)
                    #good.nums+=detail.num
                    #good.save()
                    
                    unsync_batches(detail,global_confirm=True)

                self.num_at_that_time = None
                     
                self.status=0
                self.result = False
                self.save()
                
                return self.status
            
        elif self.invoice_type==9999: #反审核盘盈盘亏
            if self.status==2:
                '''
                ' 是否来自盘点单和单品盘点不一样
                '''
                if ContentType.objects.get_for_model(self.content_object)==ContentType.objects.get_for_model(User): 
                    self.status=0
                    self.save()
                    
                    return self.status
                else:
                    if self.content_object:
                        return self.content_object.unconfirm()
                    
        elif self.invoice_type==10000: #调拨
            
            if self.status==2:
                invoice_content=ContentType.objects.get_for_model(self)
                out_invoice=Invoice.objects.get(invoice_type=2009,content_type=invoice_content,object_id=self.pk)
                in_invoice=Invoice.objects.get(invoice_type=1009,content_type=invoice_content,object_id=self.pk)  
                
                ret=out_invoice.unconfirm() 
                if ret!=0:
                    return ret
                
                ret=in_invoice.unconfirm()
                if ret!=0:
                    return ret
                
                self.status=0
                self.save()
                
                return self.status
            
    #生成数量
    def get_nums(self):
        #修改物品的当前数量
        try:
            goods_id_list=list(self.details.all().values_list('good_id',flat=True))
            #goods=Goods.objects.filter(pk__in=goods_id_list,details__invoice__invoice_type__in=[1001,1000,1009,9999],
            #                           details__invoice__status=2).annotate(sum=Sum('details__last_nums'))
            goods=Goods.objects.filter(pk__in=goods_id_list).annotate(count=Count('details__invoice__invoice_type'),sum=SumCase('details__last_nums',case='depot_ininvoice.invoice_type in (%s) and  depot_ininvoice.status=2'%IN_BASE_TYPE_STR,when=True))
            
            for good in goods:
                good.nums=good.sum
                good.save()
        except:
            print traceback.format_exc()
            
        #修改领料部门领用次数和金额
        try:
            invoice_content=ContentType.objects.get_for_model(ConDepartment)#ConDepartment
            
            #过滤领用出库和退料入库
            lists=Invoice.objects.filter(content_type=invoice_content,invoice_type__in=[1002,2001],status=2,
                                   object_id=self.object_id)
            out_list=lists.filter(invoice_type=2001)#领用出库
            in_list=lists.filter(invoice_type=1002)#退料入库

            de_count=out_list.count()#计算次数只计算领用出库单据的次数
            out_amount=0
            in_amount=0
            if out_list.annotate(sum=Sum('total_price')):
                out_amount=out_list.annotate(sum=Sum('total_price'))[0].sum
            if in_list.annotate(sum=Sum('total_price')):
                in_amount=in_list.annotate(sum=Sum('total_price'))[0].sum
            re_amount=out_amount-in_amount
            if self.invoice_type==2001:
                deobj = ConDepartment.objects.get(pk=self.object_id)
                deobj.count=de_count
                deobj.money=re_amount
                deobj.save()
            
            
        except:
            print traceback.format_exc()
        return 



#将物品的数量变为所有单据计算的总和
def update_goods_nums(sender, instance, created, **kwargs):  
    if instance.invoice_type==1001:
        if False: #现在这个表不用了
            for detail in InvoiceDetail.objects.filter(invoice_id=instance.id):
                if detail.num1==detail.num and detail.unit1:
                    for unit in Unit.objects.filter(good=detail.good):
                        unit.price=round(detail.good.change_nums(1,unit)*detail.price,2)
                        unit.save()
                        
                        update_model(unit,price=round(detail.good.change_nums(1,unit)*detail.price,2))
                        
            
                sum=DetailRelBatch.objects.filter(to_batch=detail,from_batch__invoice__status=2).aggregate(sum=Sum('num'))['sum'] or 0
                if detail.num!=(detail.last_nums+sum):
                    print "====warning====",'detail ',detail.pk,' last_nums error!!!!!!!!!!!!!!!!!!!!'
                    detail.last_nums=detail.num-sum
                    detail.save()

    #若为采购申请单，不需要对库存进行修改，不必确认库存数量
    if instance.invoice_type==1004:
        return True
    

    good_ids=[]
    for inv in instance.details.all():
        good_ids.append(inv.good_id)
        
    invoices_detail_base=InvoiceDetail.objects.filter(invoice__org=instance.org,invoice__status=2,good__in=good_ids).select_related('invoice').exclude(invoice__invoice_type=1004).exclude(invoice__invoice_type=9999)#.exclude(invoice_type=10000)
    goods_base=Goods.objects.filter(org=instance.org) 
               
    for inv in instance.details.all():
        details=invoices_detail_base.filter(good=inv.good)
        nums=0
        for detail in details:
            if detail.invoice.get_num_prefix=="-":
                nums-=detail.num or 0
            else:
                nums+=detail.num or 0
        
        g=goods_base.get(pk=inv.good_id)    
        
        if g.nums!=nums:
            g.nums=nums
            g.save()

            update_model(g,nums=nums)
            print "====warning====",'detail ',inv.good_id,' last_nums error!!!!!!!!!!!!!!!!!!!!'

  
        
    sync_caiwu(sender, instance, created, **kwargs)
            
post_save.connect(update_goods_nums, sender=Invoice)            
                
def sync_caiwu(sender, instance, created, **kwargs):
    from caiwu.models import FundsCategory,FundsDayHis
    day=instance.event_date
        
    if instance.invoice_type==1001:
        
        fundsCategorys=FundsCategory.objects.filter(org=instance.org,ftype=5)
        if not fundsCategorys.count():
            return
        
        fundsCategory=fundsCategorys[0]
        if instance.status==2:
            try:
                fundsDayHis=FundsDayHis.objects.get(org=instance.org,date=day,category=fundsCategory,user=instance.confirm_user,remark=instance.pk)
                fundsDayHis.amount='%s'%instance.total_price
                fundsDayHis.remark="%s"%instance.pk
                fundsDayHis.save()
            except:
                fundsDayHis=FundsDayHis.objects.create(org=instance.org,date=day,amount='%s'%instance.total_price,category=fundsCategory,user=instance.confirm_user,remark=instance.pk)
        else:    
            FundsDayHis.objects.filter(org=instance.org,date=day,category=fundsCategory,user=instance.confirm_user,remark="%s"%instance.pk).delete()
        
        FundsDayHis.update_day_amount(instance.org,day)
    elif instance.invoice_type==2002:
        if instance.user.first_name=="POS":
            #POS单据
            fundsCategorys=FundsCategory.objects.filter(org=instance.org,ftype=6)
        else:
            #手动单据
            fundsCategorys=FundsCategory.objects.filter(org=instance.org,ftype=4)
        
        if not fundsCategorys.count():
            return
        
        fundsCategory=fundsCategorys[0]    
        if instance.status==2:
            try:
                fundsDayHis=FundsDayHis.objects.get(org=instance.org,date=day,category=fundsCategory,user=instance.confirm_user,remark=instance.pk)
                fundsDayHis.amount='%s'%instance.total_price
                fundsDayHis.remark="%s"%instance.pk
                fundsDayHis.save()
            except:
                fundsDayHis=FundsDayHis.objects.create(org=instance.org,date=day,amount='%s'%instance.total_price,category=fundsCategory,user=instance.confirm_user,remark=instance.pk)
              
        else:
            FundsDayHis.objects.filter(org=instance.org,date=day,category=fundsCategory,user=instance.confirm_user,remark="%s"%instance.pk).delete()
        
        FundsDayHis.update_day_amount(instance.org,day)
        
    #更新物品基本信息，最近出入价格，当月和30天出库信息
    if instance.status==2:
        if instance.invoice_type in (1001,1000):
            for detail in instance.details.all():
                good=Goods.objects.get(pk=detail.good_id)
                good.price=(detail.unit1==good.unit) and detail.avg_price or good.price
                
                #good.profit=good.sale_price-good.price
                #good.percent1=good.price and (good.sale_price-good.price)*100.0/good.price or 0
                #good.percent2=good.sale_price and (good.sale_price-good.price)*100.0/good.sale_price or 0
                
                good.last_in_time=instance.event_date
                good.last_in_num=detail.num1
                good.last_in_unit=detail.unit1
                
                good.save()
        elif instance.invoice_type in (2002,2000,2001):
            for detail in instance.details.all():
                good=Goods.objects.get(pk=detail.good_id)
                good.sale_price=(detail.unit1==good.unit) and detail.avg_price or good.sale_price
                
                #good.profit=good.sale_price-good.price
                #good.percent1=good.price and (good.sale_price-good.price)*100.0/good.price or 0
                #good.percent2=good.sale_price and (good.sale_price-good.price)*100.0/good.sale_price or 0
                
                good.last_out_time=instance.event_date
                good.last_out_num=detail.num1
                good.last_out_unit=detail.unit1
                
                good.save()
   
    #更新当月和30天内出库信息
    cur_month_details=InvoiceDetail.objects.filter(invoice__event_date__gte=datetime.date.today().replace(day=1),invoice__status=2) 
    day30_details=InvoiceDetail.objects.filter(invoice__event_date__gte=datetime.date.today()+datetime.timedelta(days=-30),invoice__status=2)   
    
    for detail in instance.details.all():
        good=Goods.objects.get(pk=detail.good_id)
        
        in_nums=cur_month_details.filter(good=good,invoice__invoice_type__in=(1000,1001)).aggregate(sum_num=Sum('num'))['sum_num']
        in_datas=cur_month_details.filter(good=good,invoice__invoice_type=1001).aggregate(sum_num=Sum('num'),sum_price=Sum('total_price'))
        
        out_nums=cur_month_details.filter(good=good,invoice__invoice_type__in=(2002,2000,2001)).aggregate(sum_num=Sum('num'))['sum_num']
        out_datas=cur_month_details.filter(good=good,invoice__invoice_type=2002).aggregate(sum_num=Sum('num'),sum_price=Sum('total_price'))
        
        good.last_month_in_num=in_nums
        good.last_month_out_num=out_nums
        good.last_month_in_avg=in_datas['sum_num'] and in_datas['sum_price']/in_datas['sum_num'] or 0
        good.last_month_out_avg=out_datas['sum_num'] and out_datas['sum_price']/out_datas['sum_num'] or 0
        
        
        in_nums=day30_details.filter(good=good,invoice__invoice_type__in=(1000,1001)).aggregate(sum_num=Sum('num'))['sum_num']
        in_datas=day30_details.filter(good=good,invoice__invoice_type=1001).aggregate(sum_num=Sum('num'),sum_price=Sum('total_price'))
        
        out_nums=day30_details.filter(good=good,invoice__invoice_type__in=(2002,2000,2001)).aggregate(sum_num=Sum('num'))['sum_num']
        out_datas=day30_details.filter(good=good,invoice__invoice_type=2002).aggregate(sum_num=Sum('num'),sum_price=Sum('total_price'))
        
        good.last_30days_in_num=in_nums
        good.last_30days_out_num=out_nums
        good.last_30days_in_avg=in_datas['sum_num'] and in_datas['sum_price']/in_datas['sum_num'] or 0
        good.last_30days_out_avg=out_datas['sum_num'] and out_datas['sum_price']/out_datas['sum_num'] or 0
    
        good.save()
        
    '''
    ' 记录物品历史
    '''
    if instance.status==2:
        for detail in instance.details.all().select_related():
            description=u'%s%s%s%s,剩余%s'%(instance.get_invoice_type_display(),instance.get_num_prefix,detail.num1,detail.unit1 or '',detail.good.nums)
            snap_detail,created=GoodHisSnapDetail.objects.get_or_create(invoice_id=instance.id,org=instance.org,good=detail.good,
                                                    defaults={'description':description,'snap_date':instance.event_date,'snap_time':datetime.datetime.now().time()})
            if not created:
                snap_detail.description=description
                snap_detail.snap_date=instance.event_date
                snap_detail.snap_time=datetime.datetime.now().time()
                snap_detail.status=1
                snap_detail.save()
    else:
        GoodHisSnapDetail.objects.filter(invoice_id=instance.id,org=instance.org).delete()


                
'''
    单据细节
'''
class InvoiceDetail(models.Model):
    invoice=models.ForeignKey(Invoice,on_delete=models.CASCADE,related_name='details')
    good=models.ForeignKey(Goods,related_name='details',on_delete=models.PROTECT)
    batch_code=models.CharField(_(u'批次编号'),max_length=50)
    status=models.IntegerField(default=1) #status:1正常 0:用完 -1:已合并
    
    warehouse=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'存放地'))
    warehouse_root=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'存放地'),related_name='wr_invoice_details')
    
    rel_warehouse_root=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'相关存放地'),related_name='rel_invoice_details')
    rel_warehouse=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'相关存放地'),related_name='rel_wr_invoice_details')
    
    shelf_life=models.IntegerField(_(u'保质期'),blank=True,null=True)
    shelf_life_type=models.IntegerField(choices=DATE_UNIT_TYPES,default=1)
    
    #ori_nums=models.ManyToManyField(through)
    num1=models.FloatField(_(u'数量'),help_text=_(u'可以是辅助单位的数量'))
    unit1=models.ForeignKey(Unit,blank=True,null=True,on_delete=models.SET_NULL)
    
    price=models.FloatField()
    avg_price=models.FloatField(blank=True,null=True)
    num=models.FloatField(_(u'数量'),help_text=_(u'转换为主单位后的数量'))
    last_nums=models.FloatField()
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)

    num_at_that_time=models.FloatField(_(u'当时库存'),blank=True,null=True,help_text=_(u"当时单据生效前的库存"))
    
    total_price=models.FloatField()
    chenben_price=models.FloatField(default=0,blank=True,null=True)
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    
    rel_batchs=models.ManyToManyField('self',through='DetailRelBatch',symmetrical=False)

    
    
    class Meta:
        verbose_name=_(u'入库单细节')
        db_table="depot_invoicedetail"

    @classmethod
    def get_next_detail_code(self):
        today=datetime.datetime.today()
        invoice_code=(INVOICE_BATCH_TEMPLATE%{'date':datetime.datetime.strftime(today,'%Y%m%d'),'seq':get_next_increment(self)}).replace(' ','0')
        return invoice_code
    
    '''
    '    剩余数量转化为采购时的单位
    '''
    def last_nums_unit1(self):
        return self.good.change_nums(self.last_nums,self.good.unit,self.unit1)
    
    '''
    '    得到该批次的过期时间
    '''
    @property
    def end_shelf_life(self):
        if self.shelf_life:
            return datedelta(self.created_time,self.shelf_life,self.shelf_life_type)
 
        
class DetailRelBatch(models.Model):
    from_batch=models.ForeignKey(InvoiceDetail,on_delete=models.CASCADE,related_name="from_batches")
    to_batch=models.ForeignKey(InvoiceDetail,related_name="to_batches")
    num=models.FloatField(default=0)
    level=models.BooleanField(default=True) #True 指明对应关系，  False 对应细节
    
def unsync_batches(detail,global_confirm=True):
    rels=DetailRelBatch.objects.filter(level=True,from_batch=detail)
    if rels.exists():
        for _rel in rels:
            rel=_rel.to_batch
            #当为反审核领用出库时，不能重复
            #if (not global_confirm):# and (rel.last_nums+detail.num>rel.num):
            #    return u'物品%s已超出数量，是否重复操作过该物品？'%detail.good
            rel.last_nums+=detail.num
            if not round(rel.last_nums,5):
                rel.last_nums=0
                rel.status=0
            else:
                rel.status=1
            rel.save()
            _rel.num=0
            _rel.save()
            #_rel.delete()
    else:
        #for rel in InvoiceDetail.objects.filter(to_batches__from_batch=detail,level=False):
        for drb in DetailRelBatch.objects.filter(from_batch=detail,level=False).distinct():
            rel=drb.to_batch
            rel.last_nums+=drb.num
            if not round(rel.last_nums,5):
                rel.last_nums=0
                rel.status=0
            else:
                rel.status=1
            rel.save()
            drb.delete()
'''
    退料
'''
def unsync_tuiliao(detail,global_confirm=False):
    lingyong_rels=DetailRelBatch.objects.filter(level=True,from_batch=detail)
    if lingyong_rels.exists():
        for _lingyong_rel in lingyong_rels:
            lingyong_rel=_lingyong_rel.to_batch
            #增加领用数据
            #if lingyong_rel.num<lingyong_rel.last_nums+detail.num:
            #    return u'物品%s已超出数量，是否重复操作过该物品？'%detail.good
            lingyong_rel.last_nums=round(lingyong_rel.last_nums+detail.num,5)
            lingyong_rel.save()
            
            #减少可用数量
            rels=DetailRelBatch.objects.filter(from_batch=lingyong_rel,level=True)
            if rels.exists():
                for _rel in rels:
                    rel=_rel.to_batch
                    if rel.invoice.status!=2:
                        return u'%s单据还未审核'%rel.invoice.invoice_code 
                    if global_confirm and (not detail.invoice.org.profile.neg_inv) and rel.last_nums<detail.num:
                        return u'%s库存不足（不允许为负库存）'%rel.good
                    rel.last_nums-=detail.num
                    if not round(rel.last_nums,5):
                        rel.last_nums=0
                        rel.status=0
                    rel.save()
                    _rel.num=0
                    _rel.save()
                    #_rel.delete()
    else:
        for drb in DetailRelBatch.objects.filter(from_batch=detail,level=False).distinct():
            rel=drb.to_batch
            rel.last_nums-=drb.num
            if not round(rel.last_nums,5):
                rel.last_nums=0
                rel.status=0
            else:
                rel.status=1
            rel.save()
            drb.delete()
'''
    同步退料数据
'''            
def sync_tuiliao(detail,global_confirm=False):
    lingyong_rels=DetailRelBatch.objects.filter(level=True,from_batch=detail)
    if lingyong_rels.exists():
        for _lingyong_rel in lingyong_rels:
            lingyong_rel=_lingyong_rel.to_batch
            #扣减领用数据
            if lingyong_rel.last_nums<detail.num:
                return u'物品%s已超出数量，是否重复操作过该物品？'%detail.good
            lingyong_rel.last_nums=round(lingyong_rel.last_nums-detail.num,5)
            lingyong_rel.save()
            #增加可用数据
            rels=DetailRelBatch.objects.filter(from_batch=lingyong_rel,level=True)
            
            if rels.exists():
                for _rel in rels:
                    rel=_rel.to_batch
                    #当为反审核领用出库时，不能重复
                    #if (not global_confirm) and (rel.last_nums+detail.num>rel.num):
                    #    return u'物品%s已超出数量，是否重复操作过该物品？'%detail.good
                    rel.last_nums+=detail.num
                    if not round(rel.last_nums,5):
                        rel.last_nums=0
                        rel.status=0
                    else:
                        rel.status=1
                    rel.save()
                    
                    _rel.num=0
                    _rel.save()
                    
            else:
                return u'物品%s没有分批管理信息，是否在有单据后调整了批次管理方式？'%detail.good
            
    else:
        #汇总管理
        #rels=detail.good.details.filter(invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date') 
        rels=InvoiceDetail.objects.filter(good=detail.good,invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date')
        '''
        ' 物品如果没有入库，自动补上一张盘点单
        '''
        if not rels.exists():
            
            pos_user=User.objects.get_or_create(username="pos-%s"%detail.invoice.org_id,password="!",email="no@this.user",defaults={'is_active':False})[0]
            invoice,created=Invoice.objects.get_or_create(org=detail.invoice.org,invoice_type=9999,confirm_user=None,warehouse_root=detail.invoice.warehouse_root,defaults={
                                'voucher_code':_(u'自动初始盘点单'),'result':True,'status':2,
                                'event_date':datetime.date.today(),'content_type':ContentType.objects.get_for_model(User),'object_id':pos_user.id,
                                'charger':pos_user,'user':pos_user,'confirm_user':None,'remark':_(u'为了方便出库，由系统自动维护')})
            
            
            if not invoice.invoice_code:
                invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.save()
                
            InvoiceDetail.objects.create(invoice=invoice,good=detail.good,warehouse=detail.invoice.warehouse_root,warehouse_root=detail.invoice.warehouse_root,
                                         num1=0,unit1=detail.good.unit,price=detail.good.price,num=0,last_nums=0,total_price=0)
            rels=InvoiceDetail.objects.filter(good=detail.good,invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date')
            
        lingyong_rels=detail.good.details.filter(invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type=2001,
                                                 invoice__content_type=detail.invoice.content_type,invoice__object_id=detail.invoice.object_id).order_by('invoice__event_date')
                                                 
        #不扣减领用数据，直接相加
        last_rel=rels.exists() and rels[0] or None
        if not last_rel:
            return u'物品%s没有单据，是否已撤销？'%detail.good
        DetailRelBatch.objects.create(from_batch=detail,to_batch=last_rel,num=detail.num,level=False)
        last_rel.last_nums+=detail.num
        if not round(last_rel.last_nums,5):
            last_rel.last_nums=0
            last_rel.status=0
        else:
            last_rel.status=1
        last_rel.save()
        
                                    
def sync_batches(detail,global_confirm=True):
    
    _last_nums=detail.num
    rels=DetailRelBatch.objects.filter(level=True,from_batch=detail).distinct()

    if rels.exists():
        #指定批次
        for _rel in rels:
            rel=InvoiceDetail.objects.get(id=_rel.to_batch_id)
            
            if rel.invoice.status!=2:
                return u'%s单据还未审核'%rel.invoice.invoice_code 
            
            if not detail.invoice.content_object.abbreviation!='POS':
                if  global_confirm and (not detail.invoice.org.profile.neg_inv) and rel.last_nums<detail.num:
                    return u'%s库存不足（不允许为负库存）'%rel.good
            rel.last_nums-=detail.num
            if not round(rel.last_nums,5):
                rel.last_nums=0
                rel.status=0
            
            rel.save()
            _last_nums-=detail.num
            
            _rel.num=detail.num
            _rel.save()

    else:
        #未指定批次
        #rels=detail.good.details.filter(invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date')
        rels=InvoiceDetail.objects.filter(good=detail.good,invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date')
        '''
        ' 物品如果没有入库，自动补上一张盘点单
        '''
        if not rels.exists():
            pos_user=User.objects.get_or_create(username="pos-%s"%detail.invoice.org_id,password="!",email="no@this.user",defaults={'is_active':False})[0]
            invoice,created=Invoice.objects.get_or_create(org=detail.invoice.org,invoice_type=9999,confirm_user=None,warehouse_root=detail.invoice.warehouse_root,defaults={
                                'voucher_code':_(u'自动初始盘点单'),'result':True,'status':2,
                                'event_date':datetime.date.today(),'content_type':ContentType.objects.get_for_model(User),'object_id':pos_user.id,
                                'charger':pos_user,'user':pos_user,'confirm_user':None,'remark':_(u'为了方便出库，由系统自动维护')})
            
            if not invoice.invoice_code:
                invoice.invoice_code=Invoice.get_next_invoice_code()
                invoice.total_price=0
                invoice.save()
                
            InvoiceDetail.objects.create(invoice=invoice,good=detail.good,warehouse=detail.invoice.warehouse_root,warehouse_root=detail.invoice.warehouse_root,
                                         num1=0,unit1=detail.good.unit,price=detail.good.price,num=0,last_nums=0,total_price=0)
            rels=InvoiceDetail.objects.filter(good=detail.good,invoice__status=2,invoice__warehouse_root=detail.invoice.warehouse_root,invoice__invoice_type__in=IN_BASE_TYPE).order_by('-invoice__event_date')
            
        
        if detail.invoice.invoice_type==2000:
            rels.filter(invoice__invoice_type=1001,invoice__content_type=detail.invoice.content_type,invoice__object_id=detail.invoice.object_id)
        for rel in rels.filter(last_nums__gt=0).order_by('invoice__event_date'):
            
            if rel.last_nums>=_last_nums:
                DetailRelBatch.objects.create(from_batch=detail,to_batch=rel,num=_last_nums,level=False)
                rel.last_nums-=_last_nums
                if not round(rel.last_nums,5):
                    rel.last_nums=0
                    rel.status=0
                rel.save()
                
                _last_nums=0
                break
            else:
                DetailRelBatch.objects.create(from_batch=detail,to_batch=rel,num=rel.last_nums,level=False)
                _last_nums=round(_last_nums-rel.last_nums,5)
                rel.last_nums=0
                rel.status=0
                rel.save()
                
        #如果现存数量不足，则将最新的批次补为负数
        
        last_rel=rels.exists() and rels[0] or None
        if global_confirm and last_rel and _last_nums and (detail.invoice.org.profile.neg_inv or detail.invoice.content_object.abbreviation=='POS'):
            
            DetailRelBatch.objects.create(from_batch=detail,to_batch=last_rel,num=_last_nums,level=False)

            last_rel.last_nums=round(last_rel.last_nums-_last_nums,5)
            last_rel.status=1
            last_rel.save()
            
            _last_nums=0
            
    return _last_nums
    
    
'''
    SN记录
'''
class GoodSN(models.Model):
    batch=models.ForeignKey(InvoiceDetail,on_delete=models.CASCADE)
    sn=models.CharField(max_length=200)
    status=models.IntegerField(default=1,choices=((0,_(u'已出库')),(1,_(u'在库')),(2,_(u'其他'))))
    
    


    
'''
    历史库存的物品
'''
class SnapshotWarehouseGood(models.Model):
    snapshotWarehouse=models.ForeignKey(SnapshotWarehouse,on_delete=models.CASCADE,related_name='goods')
    good=models.ForeignKey(Goods,on_delete=models.CASCADE)
    is_batchs=models.IntegerField(default=1)
    code=models.CharField(_(u'物品编号'),max_length=100)
    name=models.CharField(_(u'物品名称'),max_length=50)
    category_name=models.CharField(max_length=50,verbose_name=_(u'物品分类'))
    standard=models.CharField(_(u'物品规格'),null=True,blank=True,max_length=20)
    unit=models.ForeignKey(Unit,verbose_name=_(u'物品单位'),max_length=20,blank=True,null=True)
    last_nums=models.FloatField(_(u'盘点前'),default=0)
    total_price=models.FloatField(_(u'总价'),default=0)
    abbreviation=models.CharField(_(u'助查码'),max_length=50)
    refer_price=models.FloatField(_(u'参考价格'),default=0)
    add_nums=models.FloatField(u'累计数量',default=0,help_text=_(u'出库时计算'))
    
    shiji=models.FloatField(_(u'盘点后数量'),null=True,default=None)
    pancha=models.FloatField(_(u'盘差'),null=True,default=None)
    punit=models.ForeignKey(Unit,verbose_name=_(u'盘点单位'),max_length=20,blank=True,null=True,related_name='pancha_units')
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name=_(u'盘点详情')        
        db_table="depot_snapshotwarehousegood"    
    
    
'''
    历史库存的细节
'''
class SnapshotWarehouseDetail(models.Model):
    snapshotWarehouseGood=models.ForeignKey(SnapshotWarehouseGood,on_delete=models.CASCADE,related_name='details')
    detail_id=models.IntegerField()
    good=models.ForeignKey(Goods)
    batch_code=models.CharField(_(u'批次编号'),max_length=50)
    price=models.FloatField()
    total_price=models.FloatField(_(u'总价'),default=0)
    num1=models.FloatField(_(u'数量'))
    unit1=models.ForeignKey(Unit,blank=True,null=True,on_delete=models.SET_NULL)
    unit=models.ForeignKey(Unit,blank=True,null=True,related_name='units',on_delete=models.SET_NULL)
    last_nums=models.FloatField()
    warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT,verbose_name=_(u'存放地'))
    
    shiji=models.FloatField(_(u'实际盘点数量'),null=True,default=None)
    pancha=models.FloatField(_(u'盘差'),null=True,default=None)
    

    class Meta:
        verbose_name=_(u'快照细节')        
        db_table="depot_snapshotwarehousedetail"
 
'''
' 历史库存数量，由外部程序定期生成
'''        
class GoodHisSnap(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    good=models.ForeignKey(Goods,on_delete=models.CASCADE)
    nums=models.FloatField(_(u'库存数量'),default=0)
    from_type=models.IntegerField(default=1,choices=((1,_(u'自动生成')),(2,_(u'手工盘点'))))
    snap_date=models.DateField()
    
    class Meta:
        verbose_name=_(u'库存历史数据快照')        
        db_table="depot_goodhissnap"
        ordering=('-snap_date',)
        
'''
' 历史库存变动数量
' 单据生成时，插入数据，反审核时status=0，再次审核，status=1
'''
class GoodHisSnapDetail(models.Model):
    invoice_id=models.IntegerField()
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    good=models.ForeignKey(Goods,on_delete=models.CASCADE)
    description=models.CharField(max_length=50,null=True,blank=True)
    snap_date=models.DateField()
    snap_time=models.TimeField()
    status=models.IntegerField(default=1)
    
    class Meta:
        verbose_name=_(u'库存历史数据细节')        
        db_table="depot_goodhissnapdetail"
        ordering=('snap_date','snap_time')

'''
    注册码的表
'''
class MacrosKeyWeb(models.Model):
    org=models.ForeignKey(Organization)
    event_date=models.DateTimeField(auto_now_add=True)
    key_str=models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.key_str
    
    class Meta:
        ordering=('-id','-event_date')
        verbose_name=_(u'注册信息')
        verbose_name_plural=_(u"注册信息")
        

class Announce(models.Model):
    content=models.CharField(_(u'公告内容'),max_length=200)
    insert_date=models.DateField(_(u'插入时间'),auto_now_add=True)
    update_date=models.DateField(_('更新时间'),auto_now=True)
    expired_date=models.DateField(_(u'过期时间'),default=None,null=True)
    announce_type=models.IntegerField(_(u'通知类型'),choices=((1,_(u'一般通知')),(2,_(u'紧急通知'))),default=1) #》2 系统通知
    status=models.IntegerField(_(u'状态'),choices=((1,_(u'正常')),(2,_(u'不显示'))),default=1)
    
    user=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,null=True,blank=True)
    
    class Meta:
        ordering=['id']
        verbose_name=_(u'公告')
        verbose_name_plural=_(u"公告")
        
    def __unicode__(self):
        return self.content[:20]+'...'
    
    
'''
' 需要同步的表的版本号
'''
class SyncTableVer(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,null=True,blank=True)
    good_ver=models.CharField(_(u'商品表版本号'),max_length=20)
    
    class Meta:
        ordering=['id']
        verbose_name=_(u'版本号')
        verbose_name_plural=_(u"版本号")


'''
'增加修改菜品物品对应关系时的日志记录表'
'''

class EditGoodsMenuLog(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,null=True,blank=True)
    menu_id=models.IntegerField()
    menu_name=models.CharField(max_length=60,blank=True,null=True)
    created_time=models.DateTimeField(auto_now_add=True)
    created_user=models.ForeignKey(User,blank=True,null=True)
    is_cleaned=models.IntegerField(default=0)


class EditGoodsMenuLogDetail(models.Model):
    log_id=models.ForeignKey(EditGoodsMenuLog,on_delete=models.CASCADE)
    item_name=models.CharField(max_length=60,blank=True,null=True)
    unit=models.CharField(max_length=60,blank=True,null=True)
    num=models.FloatField(null=True,blank=True)
    price=models.FloatField(null=True,blank=True)
    total_price=models.FloatField(null=True,blank=True)

'''
通用打印模板
'''
class CommonPrintTemplate(models.Model):
    name=models.CharField(max_length=80)

    
'''
   打印模板
'''
class PrintTemplate(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,null=True,blank=True)
    template_name=models.CharField(max_length=80)
    content=models.CharField(max_length=1000)
    print_template_type=models.IntegerField(_(u'模板类型'),default=1001)
    currency_unit=models.CharField(max_length=50,default="￥")
    common_template=models.ForeignKey(CommonPrintTemplate,on_delete=models.PROTECT)


'''
   操作日志
'''
class OperateLog(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE,null=True,blank=True)
    created_user=models.CharField(max_length=80)
    content=models.CharField(max_length=1000)
    created_time=models.DateTimeField(auto_now_add=True)


#付款单
class PayInvoice(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    event_date=models.DateField(_(u'日期'))
    invoice_code=models.CharField(_(u'单据编号'),max_length=100,blank=True,null=True)
    voucher_code=models.CharField(_(u'凭证号'),max_length=100,blank=True,null=True)
    result=models.BooleanField(_(u'已付清'),default=False)
    charger=models.ForeignKey(User,related_name="charger")
    user=models.ForeignKey(User,verbose_name=_(u'经办人'))
    total_pay=models.FloatField(_(u'应付款'),default=0)
    rest_pay=models.FloatField(_(u"待付款"),default=0)
    already_pay=models.FloatField(_(u"已付款"),default=0)
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    warehouse_root=models.ForeignKey(Warehouse,blank=True,null=True,on_delete=models.PROTECT,verbose_name=_(u'仓库'))
    is_delete=models.BooleanField(_(u'已删除'),default=False)
    remark=models.CharField(_(u'备注'),max_length=200,blank=True,null=True)
    invoice_from=models.ForeignKey(Invoice,blank=True,null=True)

    content_type=models.ForeignKey(ContentType)
    object_id=models.PositiveIntegerField()
    content_object=GenericForeignKey('content_type', 'object_id')

    invoice_type=models.IntegerField(_(u'单据类型'),choices=PAY_INVOICE_TYPES,default=3000)



    class Meta:
        ordering=['-event_date','-id']
        
        permissions=(
            ("fukuandan_query","查询付款单"),
            ("fukuandan_add","新增付款单"),
            ("fukuandan_modify","修改付款单"),
            ("fukuandan_delete","删除付款单"),
            ("fukuandan_confirm","审核付款单"),
            ("fukuandan_print","打印付款单"),
            ("fukuandan_export","导出付款单"),

            ("shoukuandan_query","查询收款单"),
            ("shoukuandan_add","新增收款单"),
            ("shoukuandan_modify","修改收款单"),
            ("shoukuandan_delete","删除收款单"),
            ("shoukuandan_confirm","审核收款单"),
            ("shoukuandan_print","打印收款单"),
            ("shoukuandan_export","导出收款单"),

            )


    @classmethod
    def get_next_invoice_code(self):
        today=datetime.datetime.today()
        invoice_code=(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(today,'%Y%m%d'),'seq':get_next_increment(self)}).replace(' ','0')
        return invoice_code

    def get_absolute_url(self):
        return reverse('pay_invoice_view',args=[self.org.pk,self.pk])

    def get_modify_url(self):
        if self.invoice_type == 3000:
            return reverse('fukuandan_modify',args=[self.org.pk,self.pk])
        elif self.invoice_type == 3001:
            return reverse('shoukuandan_modify',args=[self.org.pk,self.pk])


#银行账户
class BankAccount(models.Model):
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    account_name=models.CharField(_(u"账户名"),max_length=200,blank=True)
    account_num=models.CharField(_(u"银行账号"),max_length=100,blank=True)
    bank_deposit=models.CharField(_(u"开户行"),max_length=200,blank=True)
    status=models.BooleanField(_(u"停用"),default=False)

    def __str__(self):
        return self.account_name.encode('utf-8')


class PayInvoiceDetail(models.Model):
    invoice=models.ForeignKey(PayInvoice,on_delete=models.CASCADE)
    account=models.ForeignKey(BankAccount,on_delete=models.SET_NULL,verbose_name=_(u"账户"),max_length=200,blank=True,null=True)
    pay=models.FloatField(_(u'金额'),default=0)
    pay_type=models.CharField(_(u'付款方式'),max_length=200,blank=True)
    created_time=models.DateTimeField(auto_now_add=True)
    modify_time=models.DateTimeField(auto_now=True)
    remark=models.CharField(_(u"备注"),max_length=200,blank=True,null=True)
    org=models.ForeignKey(Organization,on_delete=models.CASCADE)
    event_date=models.DateField(_(u'日期'))

