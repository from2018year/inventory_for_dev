# -*- coding: utf-8 -*- 
if __name__=='__main__':
    from django.core.management import setup_environ
    import os, sys
    BASE=os.path.dirname(os.path.abspath(__file__))
    dirname = os.path.dirname(os.path.join(BASE,'../').replace('\\','/'))   #os.path.dirname(r'D:/inventory')
    sys.path.append(dirname)
    import inventory.settings as settings # Assumed to be in the same directory.
    setup_environ(settings)
        
    from django.contrib.auth.models import User  
    from django.utils import simplejson
    from django.forms.models import inlineformset_factory
    import traceback,datetime,time
    from django.db.models import Q
    from django.db.models.aggregates import Count,Sum,Min,Max,Avg
    from django.forms.formsets import formset_factory
    from django.contrib.auth.models import Permission
    from cost.models import *
    from depot.models import *
    from inventory.common import *
    from django.template import loader
    from django.template.context import Context
    from collections import defaultdict
    from django.contrib.contenttypes.models import ContentType
    from mptt.templatetags.mptt_tags import cache_tree_children
    from django.db import connections
    import pprint
    import json
    import itertools
    
    def update_database():
        print u'更新数据库...'
        cursor=connection.cursor()
        
        try:
            cursor.execute("alter table depot_unit drop index unit")
            print u'更新单位表完成'
        except:
            print u'已更新单位表'
            
        try:
            cursor.execute("alter table depot_organization drop index org_name")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_organization add column slug varchar(20) NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_organization add column style varchar(20) default 'gicater'")
        except:
            pass
            
        try:
            cursor.execute("alter table depot_orgsmembers add column level integer default 9")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_warehouse add column oindex integer default 0")
        except:
            pass
            
            
        try:
            cursor.execute("alter table auth_user modify column username varchar(100) NOT NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table cost_syncseqdetail add column goods_text varchar(100) NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_detailrelbatch engine=innodb")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_good engine=innodb")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_ininvoice engine=innodb")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_invoicedetail engine=innodb")
        except:
            pass
        
        try:
            cursor.execute("alter table cost_menuitem modify column nlu varchar(20) NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table cost_syncseqdetail modify column nlu varchar(20) NULL")
        except:
            print traceback.print_exc()
            pass
        
        
        try:
            cursor.execute("alter table depot_organization add column province_id  integer NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_organization add column city_id integer NULL")
        except:
            pass
        try:
            cursor.execute("alter table depot_organization add column district_id integer NULL")
        except:
            pass
        try:
            cursor.execute("alter table depot_organization add column area_id integer NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_snapshotwarehousegood modify column abbreviation varchar(50) NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_snapshotwarehouse add column shelf_id integer NULL")
        except:
            pass
        
        try:
            cursor.execute("update depot_snapshotwarehouse set shelf_id = warehouse_id")
        except:
            pass
       
        try:
            cursor.execute("alter table depot_invoicedetail add column rel_warehouse_root_id integer NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_invoicedetail add column rel_warehouse_id integer NULL")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_unit add column price float default 0")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_unit add column sale_price float default 0")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_good add column base_id integer null default null")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_good add column batch_range integer default 30")
        except:
            pass
        
        
        try:
            cursor.execute("alter table depot_supplier add column province_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_supplier add column city_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_supplier add column district_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_supplier add column area_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_snapshotwarehousedetail add column detail_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table cost_menuitem add column categoryPos_id integer null")
        except:
            pass
        
        try:
            cursor.execute("alter table cost_menuitem add column processing integer default 0")
        except:
            pass

        try:
            cursor.execute("alter table cost_menuitem add column status integer default 1")
        except:
            pass
        
        
        try:
            cursor.execute("alter table depot_good add column last_in_time datetime null")
            cursor.execute("alter table depot_good add column last_out_time datetime null")
            cursor.execute("alter table depot_good add column last_in_num double default 0")
            cursor.execute("alter table depot_good add column last_out_num double default 0")
            cursor.execute("alter table depot_good add column last_in_unit_id integer null")
            cursor.execute("alter table depot_good add column last_out_unit_id integer null")
            
            cursor.execute("alter table depot_good add column last_month_in_num double default 0")
            cursor.execute("alter table depot_good add column last_month_out_num double default 0")
            cursor.execute("alter table depot_good add column last_month_in_unit_id integer null")
            cursor.execute("alter table depot_good add column last_month_out_unit_id integer null")
            cursor.execute("alter table depot_good add column last_month_in_avg double default 0")
            cursor.execute("alter table depot_good add column last_month_out_avg double default 0")
            
            cursor.execute("alter table depot_good add column last_30days_in_num double default 0")
            cursor.execute("alter table depot_good add column last_30days_out_num double default 0")
            cursor.execute("alter table depot_good add column last_30days_in_unit_id integer null")
            cursor.execute("alter table depot_good add column last_30days_out_unit_id integer null")
            cursor.execute("alter table depot_good add column last_30days_in_avg double default 0")
            cursor.execute("alter table depot_good add column last_30days_out_avg double default 0")
        except:
            pass
            
        try:    
            cursor.execute("alter table depot_good add column profit double default 0")
            cursor.execute("alter table depot_good add column percent1 double default 0")
            cursor.execute("alter table depot_good add column percent2 double default 0")
        except:
            pass
        
        try:    
            cursor.execute("alter table depot_customer modify column abbreviation varchar(50) NULL")
            cursor.execute("alter table depot_supplier modify column abbreviation varchar(50) NULL")
            cursor.execute("alter table depot_condepartment modify column abbreviation varchar(50) NULL")
        except:
            pass
        
        try:    
            cursor.execute("alter table depot_good add column price_ori double default 0")
            cursor.execute("alter table depot_good add column sale_price_ori double default 0")
        except:
            pass
        
        try:    
            cursor.execute("alter table cost_synchisstep add column seq_id integer NULL default NULL")
            cursor.execute("alter table cost_menuitemdetail modify column menuItem_id integer NULL")
        except:
            pass
        
        try:    
            cursor.execute("alter table depot_good add column item_id integer NULL default NULL")
            cursor.execute("alter table depot_good add column item_type integer default 1")
        except:
            pass
        
        try:    
            cursor.execute("alter table depot_category add column slu_id integer NULL default NULL")
            cursor.execute("alter table depot_category add column slu_type integer default 1")
        except:
            pass
        
        try:
            cursor.execute("alter table depot_good modify column last_modify_user_id integer NULL")
        except:
            pass


        '''
         添加默认通用打印模板
         2017/4/20
        '''
        try:
            cursor.execute("insert into depot_commonprinttemplate (id,name) values (1,'默认通用模板')")
        except:
            print traceback.print_exc()
            
        Category.objects.rebuild()
        
        '''
           增加org单据参数配置
        '''
        try:
            cursor.execute("alter table depot_orgprofile add column is_auto_caigouruku tinyint default 1")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_caigouruku tinyint default 1")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_caigoushenqing tinyint default 1")
        except:
            print traceback.print_exc()

        '''
            每个店增加货币符号
        '''
        try:
            cursor.execute("alter table depot_orgprofile add column symbol varchar(80) NULL")
        except:
            print traceback.print_exc()

        '''
            为回收站功能增加单据字段is_delete
        '''
        try:
            cursor.execute("alter table depot_ininvoice add column is_delete tinyint default 0")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_snapshotwarehouse add column is_delete tinyint default 0")
        except:
            print traceback.print_exc()

        '''
            权限显示中文
        '''
        try:
            cursor.execute("update auth_permission set name='查询盘点单' where codename = 'pandian_query'")
            cursor.execute("update auth_permission set name='删除盘点单' where codename = 'pandian_delete'")
            cursor.execute("update auth_permission set name='打印盘点单' where codename = 'pandian_print'")
        except:
            print traceback.print_exc()

        #添加菜品利润记录的item_id
        try:
            cursor.execute("alter table cost_menuitemprofit add column item_id int Null")
        except:
            print traceback.print_exc()

        #更改菜品sync_type的默认值
        try:
            cursor.execute("alter table cost_menuitem alter column sync_type drop default")
            cursor.execute("alter table cost_menuitem alter column sync_type set default 1")
        except:
            print traceback.print_exc()

        #增加客户配置菜品的最大物品数
        try:
            cursor.execute("alter table depot_orgprofile add column max_item integer default 5")
        except:
            print traceback.print_exc()

        #增加单据审核时间，销售类型字段
        try:
            cursor.execute("alter table depot_ininvoice add column sale_type_id integer NULL")
        except:
            print traceback.print_exc()

        #增加单据相关单据
        try:
            cursor.execute("alter table depot_ininvoice add column invoice_from_id integer NULL")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_ininvoice add column confirm_time datetime NULL")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_snapshotwarehouse add column confirm_time datetime NULL")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_xiaoshouchuku tinyint default 1")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_lingyongchuku tinyint default 1")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_caigoutuihuo tinyint default 1")
        except:
            print traceback.print_exc()

        #添加财务单据类型
        try:
            cursor.execute("alter table depot_payinvoice add column invoice_type integer default 3000")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_payinvoice add column content_type_id integer")
        except:
            print traceback.print_exc()

        try:
            cursor.execute("alter table depot_payinvoice add column object_id integer")
        except:
            print traceback.print_exc()

        #添加付款收款账户
        try:
            cursor.execute("alter table depot_payinvoicedetail add column account_id integer NULL")
        except:
            print traceback.print_exc()

        #增加付款单详情日期
        try:
            cursor.execute("alter table depot_payinvoicedetail add column event_date date NULL")
        except:
            print traceback.print_exc()

        #添加盘点单对应盘盈盘亏字段
        try:
            cursor.execute("alter table depot_ininvoice add column pandian_relate_id integer NULL")
        except:
            print traceback.print_exc()


        try:
            cursor.execute("alter table depot_snapshotwarehouse add column confirm_user_id integer NULL")
        except:
            print traceback.print_exc()

        #自动审核盘点单
        try:
            cursor.execute("alter table depot_orgprofile add column auto_confirm_pandian tinyint default 1")
        except:
            print traceback.print_exc()
        #单据当时库存记录
        try:
            cursor.execute("alter table depot_invoicedetail add column num_at_that_time float NULL")
        except:
            print traceback.print_exc()

        #添加菜品成本到同步记录，方便统计成本卡动态
        try:
            cursor.execute("alter table cost_syncseqdetail add column cost float default 0")
        except:
            print traceback.print_exc()



    
    update_database()
    
    '''
    for detail in InvoiceDetail.objects.filter(invoice__invoice_type=1001):
            if detail.num1==detail.num and detail.unit1:
                for unit in Unit.objects.filter(good=detail.good):
                    unit.price=round(detail.good.change_nums(1,unit)*detail.price,2)
                    unit.save()
    '''                
      
    
      
    print u'全部更新完毕，如果遇到错误，请联系聚客餐饮 http://www.gicater.com'
    