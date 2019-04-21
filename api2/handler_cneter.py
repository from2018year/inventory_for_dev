# -*- coding: utf-8 -*- 

from piston.handler import AnonymousBaseHandler, BaseHandler
from django.utils import simplejson
from django.utils.translation import ugettext as _
import traceback
from inventory.common import datedelta, CountCase, SumCase
import datetime
from django.db.models import F
from django.core.exceptions import ObjectDoesNotExist
from depot.models import Warehouse, Invoice, OrgProfile, Goods, InvoiceDetail,\
    Organization
from dateutil import rrule
from depot.views import sync_auth_key

class OrganizationGaiKuangHandler(BaseHandler):
    
    def read(self,request,guid):
        try:
            template_var={}
            org=Organization.objects.get(org_guid=guid)
        
            
            warehouses=Warehouse.objects.filter(org=org,parent__isnull=True)
            childcount=0
            goodscount=0
            amountcount=0
            for wh in warehouses:
                childcount+=wh.get_children().count()
                wv=wh.warehouse_value()
          
                goodscount+=wv[1]
                amountcount+=wv[0]
            
       
            template_var['wh_all']={'childcount':childcount,'goodscount':goodscount,'amountcount':amountcount}

            
            
            caigou_invoices=Invoice.objects.filter(org=org,invoice_type=1001,status=2,warehouse_root__in=warehouses)
            xiaoshou_invoices=Invoice.objects.filter(org=org,invoice_type=2002,status=2,warehouse_root__in=warehouses)
            
            weijie_caigou=caigou_invoices.filter(result=0)
            weijie_xiaoshou=xiaoshou_invoices.filter(result=0)
            template_var['weijie']={'caigou':weijie_caigou.count(),'xiaoshou':weijie_xiaoshou.count()}
        
            template_var['warnings']={}
            template_var['warnings'].update({'min_warning':Goods.objects.filter(org=org,min_warning__gte=0).filter(min_warning__gte=F('nums')).count()})
            try:
                org.profile
            except:
                OrgProfile.objects.get_or_create(org=org)
            warn_day=org.profile.warn_day
            today=datetime.datetime.now()
            life_warnings=[]
            life_serious=[]
            batch_avail=InvoiceDetail.objects.select_related('good').filter(invoice__org=org,invoice__status=2,invoice__invoice_type=1001,last_nums__gt=0,good__is_batchs=1)
            for batch in batch_avail:
                
                day=batch.good.warning_day or warn_day
                if day>0 and batch.end_shelf_life:#如果该批次输入了过期时间
                    if rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()==0:
                        life_serious.append(batch)
                    elif rrule.rrule(rrule.DAILY,dtstart=today,until=batch.end_shelf_life).count()<day:
                        life_warnings.append(batch)
                       
            template_var['warnings'].update({'life_warnings':len(life_warnings)})
            template_var['warnings'].update({'life_serious':len(life_serious)})
            
            now=datetime.datetime.now()
            _date=sync_auth_key(Organization.objects.get(pk=org.id))[1]
            reg_status="success"
            if _date<now:
                reg_status="warning"
            elif _date<datedelta(now, 1, 3):
                reg_status="danger"
            
            template_var['reg_status']=reg_status
            template_var['expired']=_date.strftime('%Y-%m-%d')
            template_var['org_id']=org.id
            template_var['auto_out_stock_mode']=org.profile.auto_out_stock_mode
            
            return template_var
        except ObjectDoesNotExist,e:
            return {'error':_(u'未开通服务')}
        except:
            print traceback.print_exc()
            
        