# -*- coding: utf-8 -*- 
from django import forms
from depot.models import Organization, OrgProfile, Warehouse, Announce, UserLevel,Permission,Invoice,BankAccount,SaleType
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.utils import translation
from django.contrib.contenttypes.models import ContentType
import datetime


CONFIG_PERM = (
        ('wupin_ui',_(u'物品界面')),
        ('chenbenka_ui',_(u'成本卡界面')),
        ('danju_ui',_(u'单据界面')),
        ('tongji_ui',_(u'统计界面')),
        ('xitongshezhi_ui',_(u'系统设置界面'))
    )

CAIGOUSHENQING_PERM = (
        ('caigoushenqing_query',_(u'查询')),
        ('caigoushenqing_add',_(u'添加')),
        ('caigoushenqing_modify',_(u'修改')),
        ('caigoushenqing_delete',_(u'删除')),
        ('caigoushenqing_confirm',_(u'审核')),
        ('caigoushenqing_print',_(u'打印')),
        ('caigoushenqing_export',_(u'导出'))
    )

CAIGOURUKU_PERM = (
        ('caigouruku_query',_(u'查询')),
        ('caigouruku_add',_(u'添加')),
        ('caigouruku_modify',_(u'修改')),
        ('caigouruku_delete',_(u'删除')),
        ('caigouruku_confirm',_(u'审核')),
        ('caigouruku_print',_(u'打印')),
        ('caigouruku_export',_(u'导出'))
    )

CHUSHIRUKU_PERM = (
        ('chushiruku_query',_(u'查询')),
        ('chushiruku_add',_(u'添加')),
        ('chushiruku_modify',_(u'修改')),
        ('chushiruku_delete',_(u'删除')),
        ('chushiruku_confirm',_(u'审核')),
        ('chushiruku_print',_(u'打印')),
        ('chushiruku_export',_(u'导出'))
    )

CAIGOUTUIHUO_PERM = (
        ('caigoutuihuo_query',_(u'查询')),
        ('caigoutuihuo_add',_(u'添加')),
        ('caigoutuihuo_modify',_(u'修改')),
        ('caigoutuihuo_delete',_(u'删除')),
        ('caigoutuihuo_confirm',_(u'审核')),
        ('caigoutuihuo_print',_(u'打印')),
        ('caigoutuihuo_export',_(u'导出'))
    )

XIAOSHOUCHUKU_PERM = (
        ('xiaoshouchuku_query',_(u'查询')),
        ('xiaoshouchuku_add',_(u'添加')),
        ('xiaoshouchuku_modify',_(u'修改')),
        ('xiaoshouchuku_delete',_(u'删除')),
        ('xiaoshouchuku_confirm',_(u'审核')),
        ('xiaoshouchuku_print',_(u'打印')),
        ('xiaoshouchuku_export',_(u'导出'))
    )

LINGYONGCHUKU_PERM = (
        ('lingyongchuku_query',_(u'查询')),
        ('lingyongchuku_add',_(u'添加')),
        ('lingyongchuku_modify',_(u'修改')),
        ('lingyongchuku_delete',_(u'删除')),
        ('lingyongchuku_confirm',_(u'审核')),
        ('lingyongchuku_print',_(u'打印')),
        ('lingyongchuku_export',_(u'导出'))
    )

TUICANGRUKU_PERM = (
        ('tuicangruku_query',_(u'查询')),
        ('tuicangruku_add',_(u'添加')),
        ('tuicangruku_modify',_(u'修改')),
        ('tuicangruku_delete',_(u'删除')),
        ('tuicangruku_confirm',_(u'审核')),
        ('tuicangruku_print',_(u'打印')),
        ('tuicangruku_export',_(u'导出'))
    )

BAOSUNCHUKU_PERM = (
        ('baosunchuku_query',_(u'查询')),
        ('baosunchuku_add',_(u'添加')),
        ('baosunchuku_modify',_(u'修改')),
        ('baosunchuku_delete',_(u'删除')),
        ('baosunchuku_confirm',_(u'审核')),
        ('baosunchuku_print',_(u'打印')),
        ('baosunchuku_export',_(u'导出'))
    )

PANDIAN_PERM = (
        ('pandian_query',_(u'查询')),
        ('pandian_add',_(u'添加')),
        ('pandian_modify',_(u'修改')),
        ('pandian_delete',_(u'删除')),
        ('pandian_confirm',_(u'审核')),
        ('pandian_print',_(u'打印')),
        ('pandian_export',_(u'导出'))
    )

PANYING_PERM = (
        ('panying_query',_(u'查询')),
        ('panying_add',_(u'添加')),
        ('panying_modify',_(u'修改')),
        ('panying_delete',_(u'删除')),
        ('panying_confirm',_(u'审核')),
        ('panying_print',_(u'打印')),
        ('panying_export',_(u'导出'))
    )

PANKUI_PERM = (
        ('pankui_query',_(u'查询')),
        ('pankui_add',_(u'添加')),
        ('pankui_modify',_(u'修改')),
        ('pankui_delete',_(u'删除')),
        ('pankui_confirm',_(u'审核')),
        ('pankui_print',_(u'打印')),
        ('pankui_export',_(u'导出'))
    )

HUISHOUZHAN_PERM = (
        ('huishouzhan_query',_(u'查询')),
        ('huishouzhan_delete',_(u'删除')),
        ('huishouzhan_restore',_(u'还原'))
    )

SHOUKUANDAN_PERM = (
        ('shoukuandan_query',_(u'查询')),
        ('shoukuandan_add',_(u'添加')),
        ('shoukuandan_modify',_(u'修改')),
        ('shoukuandan_delete',_(u'删除')),
        ('shoukuandan_print',_(u'打印')),
        ('shoukuandan_export',_(u'导出'))
    )

FUKUANDAN_PERM = (
        ('fukuandan_query',_(u'查询')),
        ('fukuandan_add',_(u'添加')),
        ('fukuandan_modify',_(u'修改')),
        ('fukuandan_delete',_(u'删除')),
        ('fukuandan_print',_(u'打印')),
        ('fukuandan_export',_(u'导出'))
    )
'''
    修改公司
'''
class SettingOrgForm(forms.ModelForm):

    class Meta:
        model=Organization
        fields=('org_name','org_guid','org_group','stores_address','province','city','district','area','industry','url','phone','tel',
                'fax','post_code')
        
        widgets={
            'stores_address':forms.TextInput(attrs={'style':"width:98%",'placeholder':_(u'详细街道地址')}),
            'org_guid':forms.TextInput(attrs={'style':"width:98%"}),
        }
        
'''
    修改公司配置信息
'''        
class SettingOrgProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):         
        super(SettingOrgProfileForm, self).__init__(*args, **kwargs) 

        if self.instance.pk and self.instance.org and not self.instance.org.parent:
            self.fields['cengji']=forms.IntegerField(label=_(u'仓库允许层级数'),required=True,min_value=1)
        else:
            del self.fields['cengji']  
        
    
    class Meta:
        model=OrgProfile
        fields=('neg_inv','warn_day','remind_date','email','send_email','cengji','is_auto_caigouruku','auto_out_stock_mode')
        
'''
    修改公司参数信息
'''        
class SettingOrgParamForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):         
        super(SettingOrgParamForm, self).__init__(*args, **kwargs)       
    
    class Meta:
        model=OrgProfile
        fields=('neg_inv','warn_day','remind_date','email','send_email','is_auto_caigouruku','symbol','max_item','auto_confirm_caigoushenqing','auto_confirm_caigouruku','auto_confirm_xiaoshouchuku','auto_confirm_lingyongchuku','auto_confirm_caigoutuihuo','auto_confirm_pandian')
'''
    修改仓库/货架
'''
class WarehouseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):         
        super(WarehouseForm, self).__init__(*args, **kwargs)
        
        if kwargs['initial'].get('parent',None):
            del self.fields['address']
            del self.fields['charger']
            #del self.fields['oindex']
        
    class Meta:
        model=Warehouse
        fields=('name','remark','status','address','charger',)
        
        widgets={
            'address':forms.TextInput(attrs={'style':"width:100%"}),
            'remark':forms.Textarea(attrs={'style':"width:100%"}),
        }
    
        
        
'''
    添加/修改用户
'''
class UserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):         
        super(UserForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields['password']
            del self.fields['password_re']
        
    password_re=forms.CharField(label=_(u'重复密码'),max_length=30,widget=forms.PasswordInput(render_value=True),error_messages={'required':_(u'请输入重复密码'),'invalid':_(u'输入不正确')})
    
    class Meta:
        model=User
        exclude=('first_name','last_name','is_staff','is_active','is_superuser','last_login','date_joined','delinquent','upermissions')
        widgets={
            'password':forms.PasswordInput(render_value=True),
            'address':forms.TextInput(attrs={'style':"width:100%"}),
            'remark':forms.Textarea(attrs={'style':"width:100%"}),
            'birthday':forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}),
        }
        
    def clean_password_re(self):
        if not self.cleaned_data['password_re']==self.cleaned_data['password']:
            raise forms.ValidationError(_(u'重复密码不一致'))
        return self.cleaned_data['password_re']
    

'''
    修改密码
'''
class UserPWDForm(forms.Form):
    def __init__(self,*args, **kwargs):
        super(UserPWDForm, self).__init__(*args, **kwargs)
        self.data.update({'user':kwargs['initial'].get('user',None)})
        self.fields['old_password'].required=kwargs['initial'].get('opwd',True)
    
    old_password=forms.CharField(max_length=50,label=_(u'当前密码'),widget=forms.PasswordInput(render_value=True),required=True,error_messages={'required':_(u'请输入重复密码'),'invalid':_(u'输入不正确')})
    password=forms.CharField(label=_(u'新密码'),max_length=50,widget=forms.PasswordInput(render_value=True),error_messages={'required':_(u'请输入新密码'),'invalid':_(u'输入不正确')})
    password_re=forms.CharField(label=_(u'重复密码'),max_length=50,widget=forms.PasswordInput(render_value=True),error_messages={'required':_(u'请输入重复密码'),'invalid':_(u'输入不正确')})
    user=forms.ModelChoiceField(required=True,queryset=User.objects.all())
    
    def clean(self):
        cleaned_data=super(UserPWDForm, self).clean()
        if self.errors:
            return cleaned_data
        old_password=cleaned_data['old_password']
        user=cleaned_data['user']
        
        if old_password:
            if not user.check_password(old_password):
                del cleaned_data['old_password']
                self._errors['old_password']=self.error_class([_(u'初始密码不正确')])
        
        password=cleaned_data['password'] 
        password_re=cleaned_data['password_re']
        if password!=password_re:
            del cleaned_data['password']
            del cleaned_data['password_re']
            self._errors['password']=self.error_class([_(u'两次密码不一致')])
            self._errors['password_re']=self.error_class([_(u'两次密码不一致')])
                
        return cleaned_data
    
    
'''
    公告form
'''
class AnnounceForm(forms.ModelForm):
    class Meta:
        model=Announce
        fields=('content','expired_date','status','announce_type')
        
        widgets={
            'content':forms.Textarea(attrs={'style':"width:80%"}),
            'expired_date':forms.TextInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}),
        }

'''
   员工form
'''
class StaffForm(forms.ModelForm):
    def __init__(self,org,*args,**kwargs):
        super(StaffForm,self).__init__(*args,**kwargs)
        
        self.fields['user_levels'] = forms.ModelChoiceField(queryset=UserLevel.objects.filter(org=org))
        self.fields['password_re'] = forms.CharField(label=_(u'重复密码'),max_length=50)

    def clean(self):
        cleaned_data=super(StaffForm, self).clean()
        if self.errors:
            return cleaned_data      
        
        password=cleaned_data['password'] 
        password_re=cleaned_data['password_re']
        if password!=password_re:
            del cleaned_data['password']
            del cleaned_data['password_re']
            self._errors['password']=self.error_class([_(u'两次密码不一致')])
            self._errors['password_re']=self.error_class([_(u'两次密码不一致')])

        if not cleaned_data['user_levels']:
            self._errors['user_levels']=self.error_class([_(u'请选择权限')])

                
        return cleaned_data
        
    class Meta:
        model=User
        fields=('username','password','first_name','position','is_active')


class ModifyStaffForm(forms.ModelForm):
    def __init__(self,org,*args,**kwargs):
        super(ModifyStaffForm,self).__init__(*args,**kwargs)
        
        self.fields['user_levels'] = forms.ModelChoiceField(queryset=UserLevel.objects.filter(org=org))
        
    class Meta:
        model=User
        fields=('username','first_name','position','is_active')

class ResetPasswordForm(forms.Form):
    def __init__(self,*args,**kwargs):
        super(ResetPasswordForm,self).__init__(*args,**kwargs)
        self.fields['password'] = forms.CharField(label=_(u'密码'),max_length=50)
        self.fields['password_re'] = forms.CharField(label=_(u'重复密码'),max_length=50)

    def clean(self):
        cleaned_data=super(ResetPasswordForm, self).clean()
        if self.errors:
            return cleaned_data      
        
        password=cleaned_data['password'] 
        password_re=cleaned_data['password_re']
        if password!=password_re:
            del cleaned_data['password']
            del cleaned_data['password_re']
            self._errors['password']=self.error_class([_(u'两次密码不一致')])
            self._errors['password_re']=self.error_class([_(u'两次密码不一致')])
                
        return cleaned_data

class PermissionForm(forms.Form):
    user_level = forms.CharField(max_length=20,required=False)
    caigoushenqing_perms = forms.MultipleChoiceField(label=_(u'采购申请单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=CAIGOUSHENQING_PERM,required=False)
    caigouruku_perms = forms.MultipleChoiceField(label=_(u'采购入库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=CAIGOURUKU_PERM,required=False)
    chushiruku_perms = forms.MultipleChoiceField(label=_(u'初始入库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=CHUSHIRUKU_PERM,required=False)
    caigoutuihuo_perms = forms.MultipleChoiceField(label=_(u'采购退货单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=CAIGOUTUIHUO_PERM,required=False)
    xiaoshouchuku_perms = forms.MultipleChoiceField(label=_(u'销售出库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=XIAOSHOUCHUKU_PERM,required=False)
    lingyongchuku_perms = forms.MultipleChoiceField(label=_(u'领用出库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=LINGYONGCHUKU_PERM,required=False)
    tuicangruku_perms = forms.MultipleChoiceField(label=_(u'退仓入库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=TUICANGRUKU_PERM,required=False)
    baosunchuku_perms = forms.MultipleChoiceField(label=_(u'报损出库单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=BAOSUNCHUKU_PERM,required=False)
    pandian_perms = forms.MultipleChoiceField(label=_(u'盘点单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=PANDIAN_PERM,required=False)
    panying_perms = forms.MultipleChoiceField(label=_(u'盘盈单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=PANYING_PERM,required=False)
    pankui_perms = forms.MultipleChoiceField(label=_(u'盘亏单'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=PANKUI_PERM,required=False)
    huishouzhan_perms = forms.MultipleChoiceField(label=_(u'回收站权限'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=HUISHOUZHAN_PERM,required=False)
    shoukuandan_perms = forms.MultipleChoiceField(label=_(u'收款单权限'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=SHOUKUANDAN_PERM,required=False)
    fukuandan_perms = forms.MultipleChoiceField(label=_(u'付款单权限'),widget=forms.CheckboxSelectMultiple(attrs={"class":"invoice"}),choices=FUKUANDAN_PERM,required=False)
    config_permissions = forms.MultipleChoiceField(label=_(u'系统权限'),widget=forms.CheckboxSelectMultiple(attrs={"class":"config"}),choices=CONFIG_PERM,required=False)

class OperateQueryForm(forms.Form):
    date_from =forms.DateField(label=_(u'起始时间'),initial=datetime.date.today().replace(day=1),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    date_to = forms.DateField(label=_(u'结束时间'),initial=datetime.date.today(),widget=forms.DateInput(attrs={'onClick':"WdatePicker({lang:'%s'})"%translation.get_language()}))
    created_user = forms.CharField(label=_(u'操作人'),max_length=80,required=False)
    content = forms.CharField(label=_(u'操作内容'),max_length=1000,required=False)

class AccountSettingForm(forms.ModelForm):
     class Meta:
        model=BankAccount
        exclude=('org')

class SaleTypeSettingForm(forms.ModelForm):
    class Meta:
        model=SaleType
        exclude=('org')
