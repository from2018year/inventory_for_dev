# -*- coding: utf-8 -*- 
from django.conf.urls.defaults import patterns,url


'''
    和用户中心交互的的url
'''
urlpatterns=patterns('depot.views',
    url(r'^new_org_with_cmd/(?P<guid>\S+)/$','new_org_with_cmd',name='new_org_with_cmd'),
    
)

'''
    常规url
'''
urlpatterns+=patterns('depot.views',
    url(r'^register/$','register',name='register'),
    url(r'^login/$','login',{'slug':None},name='login'),
    url(r'^login/(?P<slug>\w+)/$','login',name='login_slug'),
    url(r'^logout/$','logout',name='logout'),
    url(r'^login_debug/$','login_debug',{'slug':None}),
    url(r'^main/(?P<org_id>\w+)/$','main',name='main'),
    url(r'^select_orgs/$','select_orgs',name='select_orgs'),
    #url(r'^update_general_info/$','update_general_info'),
    url(r'^org_add_group/(?P<org_id>\w+)/$','org_add_group',name='org_add_group'),
    
    url(r'^org_settings/(?P<org_id>\w+)/$','org_settings',name='org_settings'),
    
    url(r'^settings_org/(?P<org_id>\w+)/$','settings_org',{'template_name':None},name='settings_org'),
    url(r'^settings_org_modify/(?P<org_id>\w+)/$','settings_org',{'template_name':'settings/settings_org_modify.html'},name='settings_org_modify'),
    
    url(r'^select_user/(?P<org_id>\w+)/$','select_user',name='select_user'),
    
    #分部
    url(r'^org_branch/(?P<org_id>\w+)/$','org_branch',name='org_branch'),
    url(r'^org_new/(?P<org_id>\w+)/$','org_modify',{'mod_org_id':None},name='org_new'),
    url(r'^org_modify/(?P<org_id>\w+)/(?P<mod_org_id>\w+)/$','org_modify',name='org_modify'),
    url(r'^org_delete/(?P<org_id>\w+)/$','org_delete',name='org_delete'),
    
    #仓库
    url(r'^(?P<org_id>\w+)/warehouses/(?P<parent_warehouse_id>\w+)/$','warehouses',name='shelf_list'),
    url(r'^(?P<org_id>\w+)/warehouses/$','warehouses',{'parent_warehouse_id':None},name='warehouses_list'),
    
    url(r'^(?P<org_id>\w+)/warehouses_new/$','warehouses_modify',{'parent_warehouse_id':None,'mod_warehouse_id':None},name='warehouses_new'),
    url(r'^(?P<org_id>\w+)/warehouses_modify/(?P<mod_warehouse_id>\w+)/$','warehouses_modify',{'parent_warehouse_id':None},name='warehouses_modify'),
    
    url(r'^(?P<org_id>\w+)/shelf_new/(?P<parent_warehouse_id>\w+)/$','warehouses_modify',{'mod_warehouse_id':None},name='shelf_new'),
    url(r'^(?P<org_id>\w+)/shelf_modify/(?P<parent_warehouse_id>\w+)/(?P<mod_warehouse_id>\w+)/$','warehouses_modify',name='shelf_modify'),
    
    url(r'^(?P<org_id>\w+)/warehouses_delete/$','warehouses_delete',name='warehouses_delete'),
    
    #单位
    url(r'^goods_unit/(?P<org_id>\w+)/$','goods_unit',name='goods_unit'),
    
    #用户和组
    url(r'^orgs_levels/(?P<org_id>\w+)/$','orgs_levels',name='orgs_levels'),
    url(r'^orgs_users/(?P<org_id>\w+)/$','orgs_users',name='orgs_users'),
    url(r'^org_user_new/(?P<org_id>\w+)/$','org_user_modify',{'mod_user_id':None},name='org_user_new'),
    url(r'^org_user_modify/(?P<org_id>\w+)/(?P<mod_user_id>\w+)/$','org_user_modify',name='org_user_modify'),
    url(r'^org_user_modify_pwd/(?P<org_id>\w+)/(?P<mod_user_id>\w+)/$','org_user_modify_pwd',name='org_user_modify_pwd'),
    url(r'^org_user_modify_pwd2/(?P<org_id>\w+)/(?P<mod_user_id>\w+)/$','org_user_modify_pwd2',name='org_user_modify_pwd2'),
    
    url(r'^orgs_deny_login/(?P<org_id>\w+)/$','orgs_deny_login',name='orgs_deny_login'),
    url(r'^orgs_allow_login/(?P<org_id>\w+)/$','orgs_allow_login',name='orgs_allow_login'),
    url(r'^orgs_user_delete/(?P<org_id>\w+)/$','orgs_user_delete',name='orgs_user_delete'),
    
    url(r'^backup/(?P<org_id>\w+)/$','backup',name='backup'),
    url(r'^do_backup/(?P<org_id>\w+)/$','do_backup',name='do_backup'),
    url(r'^down_backup/(?P<org_id>\w+)/$','down_backup',name='down_backup'),
    url(r'^use_backup/(?P<org_id>\w+)/$','use_backup',name='use_backup'),
    url(r'^del_backup/(?P<org_id>\w+)/$','del_backup',name='del_backup'),
    url(r'^down_backup_tools/(?P<org_id>\w+)/$','down_backup_tools',name='down_backup_tools'),
    url(r'^version_update/(?P<org_id>\w+)/$','version_update',name='version_update'),
    
    url(r'^del_all_receipt/(?P<org_id>\w+)/$','del_all_receipt',name='del_all_receipt'),
    url(r'org_import_auth/(?P<org_id>\w+)/$','org_import_auth',name='org_import_auth'),
    url(r'org_auth_web/(?P<org_id>\w+)/$','org_auth_web',name='org_auth_web'),
    
    url(r'org_announce/(?P<org_id>\w+)/$','org_announce',name='org_announce'),
    url(r'org_announce_modify/(?P<org_id>\w+)/(?P<announce_id>\w+)/$','org_announce_modify',name='org_announce_modify'),
    url(r'org_announce_new/(?P<org_id>\w+)/$','org_announce_modify',{'announce_id':None},name='org_announce_new'),
    
    url(r'org_announce_delete/(?P<org_id>\w+)/$','org_announce_delete',name='org_announce_delete'),

    #员工设置
    url(r'^staff/(?P<org_id>\w+)/$','staff_list',name='staff_list'),
    #添加员工
    url(r'^add_staff/(?P<org_id>\w+)/$','add_staff',name='add_staff'),
    url(r'^staff_modify/(?P<org_id>\w+)/(?P<staff_id>\w+)/$','staff_modify',name='staff_modify'),
    #删除员工
    url(r'^staff_delete/(?P<org_id>\w+)/(?P<staff_id>\w+)/$','staff_delete',name='staff_delete'),
    url(r'^staff_deactivate/(?P<org_id>\w+)/(?P<staff_id>\w+)/$','staff_deactivate',name='staff_deactivate'),
    #重置密码
    url(r'^reset_password/(?P<org_id>\w+)/(?P<staff_id>\w+)/$','reset_password',name='reset_password'),
    #权限设置
    url(r'^permission_list/(?P<org_id>\w+)/$','permission_list',name='permission_list'),
    url(r'^add_permission_role/(?P<org_id>\w+)/$','add_permission_role',name='add_permission_role'),
    url(r'^permission_role_detail/(?P<role_id>\w+)/$','permission_role_detail',name='permission_role_detail'),
    url(r'^modify_permission_role/(?P<org_id>\w+)/(?P<role_id>\w+)/$','modify_permission_role',name='modify_permission_role'),
    url(r'^delete_permission_role/(?P<org_id>\w+)/(?P<role_id>\w+)/$','delete_permission_role',name='delete_permission_role'),
    #生成日志
    url(r'^operate_log/(?P<org_id>\w+)/$','operate_log',name='operate_log'),
    #参数设置
    url(r'^settings_param/(?P<org_id>\w+)/$','settings_param',name='settings_param'),
    #打印模板配置
    url(r'^print_template_setting/(?P<org_id>\w+)/(?P<common_template_id>\w+)/$','print_template_setting',name='print_template_setting'),
    #银行账户设置
    url(r'^settings_account/(?P<org_id>\w+)/$','settings_account',name='settings_account'),
    url(r'^change_account_status/(?P<org_id>\w+)/(?P<account_id>\w+)/$','change_account_status',name='change_account_status'),
    url(r'^add_bank_account/(?P<org_id>\w+)/$','add_bank_account',name='add_bank_account'),
    url(r'^modify_bank_account/(?P<org_id>\w+)/(?P<account_id>\w+)/$','add_bank_account',name='modify_bank_account'),
    #销售类型
    url(r'^sale_type_setting/(?P<org_id>\w+)/$','sale_type_setting',name='sale_type_setting'),
    url(r'^add_sale_type/(?P<org_id>\w+)/$','add_sale_type',name='add_sale_type'),
    url(r'^modify_sale_type/(?P<org_id>\w+)/(?P<sale_type_id>\w+)/$','add_sale_type',name='modify_sale_type'),
    url(r'^delete_sale_type/(?P<org_id>\w+)/(?P<sale_type_id>\w+)/$','delete_sale_type',name='delete_sale_type'),
)

'''
    进销存url
'''
urlpatterns+=patterns('depot.views',
    url(r'^chushiruku/(?P<org_id>\w+)/$','chushiruku',name='chushiruku'),
    url(r'^chushiruku_add/(?P<org_id>\w+)/$','chushiruku_add',name='chushiruku_add'),
    url(r'^chushiruku_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','chushiruku_add',name='chushiruku_modify'),
    
    url(r'^kuweidiaobo/(?P<org_id>\w+)/$','kuweidiaobo',name='kuweidiaobo'),
    url(r'^kuweidiaobo_add/(?P<org_id>\w+)/$','kuweidiaobo_add',name='kuweidiaobo_add'),
    url(r'^kuweidiaobo_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','kuweidiaobo_add',name='kuweidiaobo_modify'),
    
    url(r'^caigouruku/(?P<org_id>\w+)/$','caigouruku',name='caigouruku'),
    url(r'^caigouruku_add/(?P<org_id>\w+)/$','caigouruku_add',name='caigouruku_add'),
    url(r'^caigouruku_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','caigouruku_add',name='caigouruku_modify'),
    url(r'^select_goods/(?P<org_id>\w+)/$','select_goods',name='select_goods'),
    url(r'^get_goods_json/(?P<org_id>\w+)/$','get_goods_json',name='get_goods_json'),
    url(r'^get_diaobo_goods_json/(?P<org_id>\w+)/$','get_diaobo_goods_json',name='get_diaobo_goods_json'),
    
    
    
    url(r'^invoice_view/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','invoice_view',name='invoice_view'),
    url(r'^pay_invoice_view/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','pay_invoice_view',name='pay_invoice_view'),
    url(r'^invoice_view_log/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','invoice_view_log',name='invoice_view_log'),
    url(r'^invoice_view_part/(?P<org_id>\w+)/','invoice_view',{'invoice_id':None},name='invoice_view_part'),
    url(r'^confirm_invoice/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','confirm_invoice',name='confirm_invoice'),
    url(r'^unconfirm_invoice/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','unconfirm_invoice',name='unconfirm_invoice'),
    url(r'^delete_invoice/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','delete_invoice',name='delete_invoice'),
    
    url(r'^caigoutuihuo/(?P<org_id>\w+)/$','caigoutuihuo',name='caigoutuihuo'),
    url(r'^caigoutuihuo_add/(?P<org_id>\w+)/$','caigoutuihuo_add',name='caigoutuihuo_add'),
    url(r'^caigoutuihuo_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','caigoutuihuo_add',name='caigoutuihuo_modify'),
    url(r'^select_goods_use/(?P<org_id>\w+)/$','select_goods_use',name='select_goods_use'),
    url(r'^select_goods_use_kuweidiaobo/(?P<org_id>\w+)/$','select_goods_use_kuweidiaobo',name='select_goods_use_kuweidiaobo'),
    url(r'^select_invoices_use/(?P<org_id>\w+)/$','select_invoices_use',name='select_invoices_use'),
    
    
    url(r'^lingyongchuku/(?P<org_id>\w+)/$','lingyongchuku',name='lingyongchuku'),
    url(r'^lingyongchuku_add/(?P<org_id>\w+)/$','lingyongchuku_add',name='lingyongchuku_add'),
    url(r'^lingyongchuku_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','lingyongchuku_add',name='lingyongchuku_modify'),
    
    url(r'^tuiliaoruku/(?P<org_id>\w+)/$','tuiliaoruku',name='tuiliaoruku'),
    url(r'^tuiliaoruku_add/(?P<org_id>\w+)/$','tuiliaoruku_add',name='tuiliaoruku_add'),
    url(r'^tuiliaoruku_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','tuiliaoruku_add',name='tuiliaoruku_modify'),
    url(r'^select_goods_tuiku/(?P<org_id>\w+)/$','select_goods_tuiku',name='select_goods_tuiku'),
    
    
    url(r'^xiaoshouchuku/(?P<org_id>\w+)/$','xiaoshouchuku',name='xiaoshouchuku'),
    url(r'^xiaoshouchuku_add/(?P<org_id>\w+)/$','xiaoshouchuku_add',name='xiaoshouchuku_add'),
    url(r'^xiaoshouchuku_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','xiaoshouchuku_add',name='xiaoshouchuku_modify'),
    
    
    url(r'^jishikucun/(?P<org_id>\w+)/$','jishikucun',name='jishikucun'),
    url(r'^jishikucun_view/(?P<org_id>\w+)/(?P<warehouse_id>\w+)/$','jishikucun_view',name='jishikucun_view'),
    url(r'^jishikucun_view_total/(?P<org_id>\w+)/$','jishikucun_view',{'warehouse_id':None},name='jishikucun_view_total'),
    url(r'^goods_detail/(?P<org_id>\w+)/(?P<goods_id>\w+)/(?P<warehouse_id>\w+)/$','goods_detail',name='goods_detail'),
    url(r'^goods_detail_total/(?P<org_id>\w+)/(?P<goods_id>\w+)/$','goods_detail',name='goods_detail_total'),
    
    
    url(r'^cangkupandian/(?P<org_id>\w+)/(?P<warehouse_id>\w+)/$','cangkupandian',name='cangkupandian'),
    url(r'^list_goods_pandian_preview/(?P<org_id>\w+)/(?P<snap_id>\w+)/$','list_goods_pandian_preview',name='list_goods_pandian_preview'),
    url(r'^create_goods_pandian_table/(?P<org_id>\w+)/$','create_goods_pandian_table',name='create_goods_pandian_table'),
    url(r'^sync_good_count/(?P<org_id>\w+)/$','sync_good_count',name='sync_good_count'),
    
    
    url(r'^panyinpankui/(?P<org_id>\w+)/$','panyinpankui',name='panyinpankui'),
    url(r'^panyingruku/(?P<org_id>\w+)/$','panyingruku',name='panyingruku'),
    url(r'^pankuichuku/(?P<org_id>\w+)/$','pankuichuku',name='pankuichuku'),
    url(r'^pandian/(?P<org_id>\w+)/$','pandian',name='pandian'),
    url(r'^pandian_view/(?P<org_id>\w+)/$','pandian_view',name='pandian_view'),
    url(r'^pandian_view_print/(?P<org_id>\w+)/(?P<snap_id>\w+)/$','pandian_view_print',name='pandian_view_print'),
    url(r'^export_pandian/(?P<org_id>\w+)/(?P<snap_id>\w+)/$','export_pandian',name='export_pandian'),
    
    
    url(r'^confirm_pandian_dan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','confirm_pandian_dan',name='confirm_pandian_dan'),
    url(r'^set_pandian_dan/(?P<org_id>\w+)/$','set_pandian_dan',name='set_pandian_dan'),
    url(r'^cancel_pandian_dan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','cancel_pandian_dan',name='cancel_pandian_dan'),
    url(r'^del_snapshot_good/(?P<org_id>\w+)/$','del_snapshot_good',name='del_snapshot_good'),
    
    url(r'^delete_pandian_dan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','delete_pandian_dan',name='delete_pandian_dan'),
    url(r'^pandian_huishouzhan/(?P<org_id>\w+)/$','pandian_huishouzhan',name='pandian_huishouzhan'),
    url(r"^delete_pandian_huishouzhan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$",'delete_pandian_huishouzhan',name='delete_pandian_huishouzhan'),
    url(r'^restore_pandian_huishouzhan/(?P<org_id>\w+)/(?P<snap_id>\w+)/$','restore_pandian_huishouzhan',name='restore_pandian_huishouzhan'),
    url(r'^restore_all_pandian_huishouzhan/(?P<org_id>\w+)/$','restore_all_pandian_huishouzhan',name="restore_all_pandian_huishouzhan"),
    url(r'^clear_pandian_huishouzhan/(?P<org_id>\w+)/$','clear_pandian_huishouzhan',name='clear_pandian_huishouzhan'),
    
    url(r'^goods_warnings/(?P<org_id>\w+)/$','goods_warnings',name='goods_warnings'),
    url(r'^download_good_template/$','download_good_template',name='download_good_template'),
    url(r'^upload_good_template/(?P<org_id>\w+)/$','upload_good_template',name='upload_good_template'),
    
    url(r'^result_cancel/(?P<org_id>\w+)/$','result_cancel',name='result_cancel'),
    url(r'^result_ok/(?P<org_id>\w+)/$','result_ok',name='result_ok'),
    
    #导出库存盘点excel
    url(r'^download_goods_pandian_table/(?P<org_id>\w+)/$','download_goods_pandian_table',name='download_goods_pandian_table'),
    url(r'^upload_goods_pandian_table/(?P<org_id>\w+)/$','upload_goods_pandian_table',name='upload_goods_pandian_table'),

    url(r'^goods/(?P<org_id>\w+)/$','goods',name='goods'),

    #打印模板
    url(r'^print_template/(?P<org_id>\w+)/(?P<invoice_id>\w+)/(?P<common_template_id>\w+)/$','print_template',name='print_template'),
    #保存打印模板
    url(r'^save_print_template/(?P<org_id>\w+)/(?P<common_template_id>\w+)/$','save_print_template',name='save_print_template'),
    #加载模板
    url(r'^get_print_template/$','get_print_template',name='get_print_template'),
    #删除模板
    url(r'^delete_print_template/$','delete_print_template',name='delete_print_template'),
    #采购申请单
    url(r'^caigoushenqing_view/(?P<org_id>\w+)/$','caigoushenqing_view',name='caigoushenqing_view'),
    url(r'^caigoushenqing_add/(?P<org_id>\w+)/$','caigoushenqing_add',name='caigoushenqing_add'),
    url(r'^caigoushenqing_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','caigoushenqing_add',name='caigoushenqing_modify'),
    #导出单据列表
    url(r'^export_invoice/(?P<org_id>\w+)/(?P<invoice_type>\w+)/$','export_invoice',name='export_invoice'),
    #导出单据详情
    url(r'^export_invoice_detail/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','export_invoice_detail',name='export_invoice_detail'),
    #回收站
    url(r'^huishouzhan/(?P<org_id>\w+)/$','huishouzhan',name="huishouzhan"),
    url(r'^delete_huishouzhan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/(?P<invoice_type>\w+)/$','delete_huishouzhan',name='delete_huishouzhan'),
    url(r'^clear_huishouzhan/(?P<org_id>\w+)/(?P<invoice_type>\w+)/$','clear_huishouzhan',name="clear_huishouzhan"),
    url(r'^restore_huishouzhan/(?P<org_id>\w+)/(?P<invoice_id>\w+)/(?P<invoice_type>\w+)/$','restore_huishouzhan',name='restore_huishouzhan'),
    url(r'^restore_all_huishouzhan/(?P<org_id>\w+)/(?P<invoice_type>\w+)/$','restore_all_huishouzhan',name='restore_all_huishouzhan'),

    #付款单
    url(r'^fukuandan_view/(?P<org_id>\w+)/$','fukuandan_view',name="fukuandan_view"),
    url(r'^fukuandan_add/(?P<org_id>\w+)/$','fukuandan_add',name="fukuandan_add"),
    url(r'^fukuandan_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','fukuandan_add',name="fukuandan_modify"),
    url(r'^delete_paydetail/(?P<org_id>\w+)/(?P<detail_id>\w+)/$','delete_paydetail',name="delete_paydetail"),
    url(r'^delete_pay_invoice/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','delete_pay_invoice',name="delete_pay_invoice"),
    url(r'^export_pay_invoice/(?P<org_id>\w+)/(?P<pay_invoice_type>\w+)/$','export_pay_invoice',name='export_pay_invoice'),
    url(r'^export_pay_invoice_detail/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','export_pay_invoice_detail',name='export_pay_invoice_detail'),
    url(r'^print_pay_invoice/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','print_pay_invoice',name='print_pay_invoice'),
    #付款单回收站
    url(r'^pay_huishouzhan/(?P<org_id>\w+)/$','pay_huishouzhan',name="pay_huishouzhan"),

    #收款单
    url(r'^shoukuandan_view/(?P<org_id>\w+)/$','shoukuandan_view',name="shoukuandan_view"),
    url(r'^shoukuandan_add/(?P<org_id>\w+)/$','shoukuandan_add',name="shoukuandan_add"),
    url(r'^shoukuandan_modify/(?P<org_id>\w+)/(?P<invoice_id>\w+)/$','shoukuandan_add',name="shoukuandan_modify"),                                                                                                                                                                                                                                                                                                                                                                 

)

'''
    基本信息url
'''
urlpatterns+=patterns('depot.views',
    url(r'^info/(?P<org_id>\w+)/$','info',name='info'), 
    url(r'^goods_brand/(?P<org_id>\w+)/$','goods_brand',name='goods_brand'),
    url(r'^goods_and_category/(?P<org_id>\w+)/$','goods_and_category',name='goods_and_category'),
    
    url(r'^add_category/(?P<org_id>\w+)/$','add_category',{'category_id':None},name='add_category'),
    url(r'^add_category/(?P<org_id>\w+)/(?P<category_id>\w+)/$','add_category',name='add_category_2'),
    url(r'^get_categorys/(?P<org_id>\w+)/$','get_categorys',name='get_categorys'),
    url(r'^del_category/(?P<org_id>\w+)/$','del_category',name='del_category'),
    
    url(r'^add_goods/(?P<org_id>\w+)/$','add_goods',name='add_goods'),
    url(r'^auxiliary_unit/(?P<org_id>\w+)/(?P<goods_id>\w+)/$','auxiliary_unit',name='auxiliary_unit'),
    
    url(r'^list_goods_opt/(?P<org_id>\w+)/$','list_goods',{'mod':True},name='list_goods_opt'),
    url(r'^list_goods_view/(?P<org_id>\w+)/$','list_goods',{'mod':False},name='list_goods_view'),
    url(r'^del_goods/(?P<org_id>\w+)/$','del_goods',name='del_goods'),
    
    url(r'^departments/(?P<org_id>\w+)/$','departments',name='departments'),
    url(r'^mod_department/(?P<org_id>\w+)/(?P<department_id>\w+)/$','mod_department',name='mod_department'),
    url(r'^add_department/(?P<org_id>\w+)/$','mod_department',{'department_id':None},name='add_department'),
    url(r'^department_delete/(?P<org_id>\w+)/$','department_delete',name="department_delete"),
    
    
    url(r'^supplier_group/(?P<org_id>\w+)/$','supplier_group',name='supplier_group'),
    url(r'^suppliers/(?P<org_id>\w+)/$','suppliers',name='suppliers'),
    url(r'^mod_supplier/(?P<org_id>\w+)/(?P<supplier_id>\w+)/$','mod_supplier',name='mod_supplier'),
    url(r'^add_supplier/(?P<org_id>\w+)/$','mod_supplier',{'supplier_id':None},name='add_supplier'),
    url(r'^supplier_delete/(?P<org_id>\w+)/$','supplier_delete',name="supplier_delete"),
    
    
    url(r'^customers/(?P<org_id>\w+)/$','customers',name='customers'),
    url(r'^mod_customer/(?P<org_id>\w+)/(?P<customer_id>\S+)/$','mod_customer',name='mod_customer'),
    url(r'^add_customer/(?P<org_id>\w+)/$','mod_customer',{'customer_id':None},name='add_customer'),
    url(r'^customer_delete/(?P<org_id>\w+)/$','customer_delete',name="customer_delete"),
    
    url(r'^download_pandian_goods/(?P<org_id>\w+)/$','download_pandian_goods',name="download_pandian_goods"),
    
)

urlpatterns+=patterns('depot.views',
    url(r'^tongji_main/(?P<org_id>\w+)/$','tongji_main',name='tongji_main'),
    url(r'^tongji_search_danju/(?P<org_id>\w+)/$','tongji_search_danju',name='tongji_search_danju'),
    url(r'^tongji_get_refer/(?P<org_id>\w+)/$','tongji_get_refer',name='tongji_get_refer'),
    url(r'^tongji_lingyong_danju/(?P<org_id>\w+)/$','tongji_lingyong_danju',name='tongji_lingyong_danju'),
    url(r'^tongji_gonghuoshang_danju/(?P<org_id>\w+)/$','tongji_gonghuoshang_danju',name='tongji_gonghuoshang_danju'),
    url(r'^tongji_goods_inout_danju/(?P<org_id>\w+)/$','tongji_goods_inout_danju',name='tongji_goods_inout_danju'),
    url(r'^tongji_goods_inout_detail/(?P<org_id>\w+)/$','tongji_goods_inout_detail',name='tongji_goods_inout_detail'),
    url(r'^tongji_auto_stock_log/(?P<org_id>\w+)/$','tongji_auto_stock_log',name='tongji_auto_stock_log'),
    url(r'^tongji_auto_stock_sum/(?P<org_id>\w+)/$','tongji_auto_stock_sum',name='tongji_auto_stock_sum'),
    url(r'^tongji_goods_num_change/(?P<org_id>\w+)/$','tongji_goods_num_change',name='tongji_goods_num_change'),
    url(r'^get_snap_his/(?P<org_id>\w+)/$','get_snap_his',name='get_snap_his'),
    url(r'^dppd/(?P<org_id>\w+)/(?P<goods_id>\w+)/$','dppd',name='dppd'),

    url(r'^search_ruku/(?P<org_id>\w+)/$','search_ruku',name='search_ruku'),
    url(r'^search_chuku/(?P<org_id>\w+)/$','search_chuku',name='search_chuku'),
    url(r'^tongji_ruku/(?P<org_id>\w+)/$','tongji_ruku',name='tongji_ruku'),
    url(r'^tongji_chuku/(?P<org_id>\w+)/$','tongji_chuku',name='tongji_chuku'),

    url(r'^dongtai_analysis/(?P<org_id>\w+)/$','dongtai_analysis',name='dongtai_analysis'),

    url(r'^minus_stock_query/(?P<org_id>\w+)/$','minus_stock_query',name='minus_stock_query'),
    
)

urlpatterns+=patterns('depot.views',
    url(r'^org_chengben/(?P<org_id>\w+)/$','org_chengben',name='org_chengben'),
)

'''
'simple
'''
urlpatterns+=patterns('depot.views',
    url(r'^wupin/(?P<org_id>\w+)/$','wupin',name='wupin'),
    url(r'^simple_list_wupin/(?P<org_id>\w+)/$','list_wupin',{'category_id':None}),
    url(r'^simple_list_wupin/(?P<org_id>\w+)/(?P<category_id>\w+)/$','list_wupin'),
    
    url(r'^caipin/(?P<org_id>\w+)/$','caipin',name='caipin'),
    url(r'^simple_list_caipin/(?P<org_id>\w+)/$','list_caipin',{'category_id':None}),
    url(r'^simple_list_caipin/(?P<org_id>\w+)/(?P<category_id>\w+)/$','list_caipin'),
    url(r'^menuItem_detail/(?P<menuItem_id>\w+)/$','menuItem_detail',name='menuItem_detail'),
    
    url(r'^caipin_delete/(?P<org_id>\w+)/$','caipin_delete',name='caipin_delete'),
    url(r'^simple_list_delete_caipin/(?P<org_id>\w+)/$','list_delete_caipin',{'category_id':None,'delete':True},name="list_delete_caipin"),
    url(r'^simple_list_delete_caipin/(?P<org_id>\w+)/(?P<category_id>\w+)/$','list_delete_caipin',{'delete':True}),
    url(r'^recover_menuitem/(?P<org_id>\w+)/$','recover_menuitem',name='recover_menuitem'),
    
    url(r'^import_from_pos/(?P<org_id>\w+)/$','import_from_pos',name='import_from_pos'),
    url(r'^in_out_simple/(?P<org_id>\w+)/$','in_out_simple',name='in_out_simple'),
    url(r'^goods_img/(?P<goods_id>\w+)/$', 'goods_img', name='goods_img'),
    
)


'''
    工具url
'''
urlpatterns+=patterns('depot.views',
    url(r'^test_pos_ip/$','test_pos_ip',name='test_pos_ip'),
    url(r'^sync_old_ip/(?P<org_id>\w+)/$','sync_old_ip',name="sync_old_ip"),
    url(r'^get_users/$','get_users',name='get_users'),
    url(r'^prepic/$','prepic',name='prepic'),
    url(r'^confirm_perm/$','confirm_perm',name='confirm_perm'),  
)