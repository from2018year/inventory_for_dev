# -*- coding: utf-8 -*-
from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from depot.models import Organization, Category, Warehouse, Invoice, Unit, Brand,\
    Goods, InvoiceDetail
from django.db import load_backend,connections
from django.db.models import Q
from inventory.settings import EXE_DIR,TMP_DIR
from inventory.settings import MEDIA_ROOT
from inventory.common import *
from django.views.decorators.csrf import csrf_exempt
from inventory.MACROS import INVOICE_CODE_TEMPLATE
import logging
import traceback,os
from cost.views import OS_TYPE
from django.core.exceptions import MultipleObjectsReturned
try:
    from PIL import ImageFile
except:
    import ImageFile
log=logging.getLogger(__name__)

'''
    与收收银机连接，测试是否能联通
'''
def test_pos_ip(request):
    try:
        pos_ip=request.GET.get('pos_ip',None)
        dom_id=request.GET.get('dom_id','')
        orgpos=OrgPOS.objects.filter(pos_ip=pos_ip)
        if orgpos.exists():
            return HttpResponse(simplejson.dumps({'fetch_status':True,'res_id':orgpos[0].org_guid,'dom_id':dom_id}),mimetype='application/json')
        if pos_ip:
            pos_backend=load_backend('django.db.backends.mysql')
            pos_connection=pos_backend.DatabaseWrapper({
                'HOST': pos_ip,
                'NAME': 'coolroid',
                'USER': "root",
                'PASSWORD': "agile",
                'OPTIONS':{},
                'PORT': "3308"
            })
            
            pos_cursor=pos_connection.cursor()
            
            fetch_status=True
            res_id=''
            try:
                pos_cursor.execute('SELECT cr_res_id FROM webreport_setting limit 1');
                data=pos_cursor.fetchone()
                res_id=data[0]
            except:
                fetch_status=False
                print traceback.print_exc()
            
            pos_cursor.close()
            pos_connection.close()
            return HttpResponse(simplejson.dumps({'fetch_status':fetch_status,'res_id':res_id,'dom_id':dom_id}),mimetype='application/json')
    except:
        print traceback.print_exc()
        
'''
    预览图片
'''
def prepic(request):
    try:
        img=request.FILES[request.FILES.keys()[0]]
        try:
            width=int(request.GET.get('width',False))
            height=int(request.GET.get('height',False))
        except:
            width=False
            height=False
        parser=ImageFile.Parser()
        for chunk in img.chunks():
            parser.feed(chunk)
            
        i=parser.close()
        
        newname="%s.%s"%(request.user.pk,img.name.split(".")[-1])

        name="%s/tmp/%s"%(MEDIA_ROOT,newname)
        if width and height:
            w,h=i.size
            scale=float(height)/h
            if w>h:
                scale=float(width)/w      
            i=i.resize((int(w*scale),int(h*scale)))
               
        i.save(name)
        
        return HttpResponse("tmp/%s"%(newname))
    except:
        print(traceback.format_exc())
        return HttpResponse(_(u"预览失败"))
        
        
'''
    得到用户数据
'''
def get_users(request):
    try:
        username=request.REQUEST.get('username','')
        org_id=request.REQUEST['org_id']
        users=User.objects.filter(om_orgs__org_id=org_id).filter(Q(username__icontains=username)|Q(tel__icontains=username))
        ts=simplejson.dumps(list(users.values('employee_id','tel','username','pk')))
        return HttpResponse(ts,mimetype='application/json')
    except:
        print traceback.format_exc()
        return HttpResponse(simplejson.dumps([{}]),mimetype='application/json')
    
    
'''
    判断用户是否具有库存的单据写权限
'''
def confirm_perm(request):
    invoice_type=int(request.GET.get('invoice_type',0))
    warehouse_id=request.GET.get('warehouse_id',0)
    
    return HttpResponse(simplejson.dumps({'confirm':user_can_confirm_invoice(Warehouse.objects.get(pk=warehouse_id),invoice_type,request.user)}),mimetype='application/json')
    
    
def user_can_confirm_invoice(warehouse,invoice_type,user):
    
    if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_manage',)):
        return True
    if invoice_type==1001:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True
    elif invoice_type==1000:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True  
    elif invoice_type==1002:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True  
    elif invoice_type==2000:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True
    elif invoice_type==2001:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True
    elif invoice_type==2002:
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True 
    elif invoice_type in (9999,10000):          
        if user.has_org_warehouse_perm(warehouse.pk,('depot.warehouse_write',)):
            return True
        
    return False
    
'''
    的到分类组的json
'''
def get_categorys(request,org_id):
    try:
        org=Organization.objects.get(pk=org_id)
        root_org=org.get_root_org()
        #
        try:
            cobj,ret=Category.objects.get_or_create(parent__isnull=True,org=root_org)
        except MultipleObjectsReturned:
            cobj = Category.objects.filter(parent__isnull=True,org=root_org)[0]

        cobj.name=_(u'全部分类')
        cobj.save()
        
        category_id=request.POST.get('id',None)
        
        if category_id:
            category=Category.objects.get(pk=category_id)
        else:
            category=Category.objects.get(parent__isnull=True,org=root_org)
        
        return HttpResponse(category.serialize_to_json(org),mimetype='application/json')
    except:
        print traceback.format_exc()
        
'''
    保存图片
'''
@csrf_exempt
def export_image(request):
    def readFile(filename,buf_size=262144):
            f=open(filename,'rb')
            while True:
                c=f.read(buf_size)
                if c:
                    yield c
                else:
                    break
            f.close()
            
    file_type=request.POST['type']
    svg=request.POST['svg']
    filename=request.POST['filename']
    
    svg_name="%s%s.svg"%(TMP_DIR,request.user.pk)
    if os.path.exists(svg_name):
        os.remove(svg_name)
    
    f=open(svg_name,'w')
    
    f.write(svg.encode('utf8'))
    f.close()
    
    if file_type=="application/pdf":
        format="-f pdf"
        ext="pdf"
    elif file_type=="image/svg+xml":
        format="-f svg"
        ext="svg"
    else:
        format="-f png"
        ext="png"
        
    out_name="%s%s.%s"%(TMP_DIR,filename,ext)
    if os.path.exists(out_name):
        os.remove(out_name)
    
    if OS_TYPE=="WINDOWS":
        cstr="cmd /c \"%srsvg-convert.exe\" %s %s -o %s "%(EXE_DIR,svg_name,format,out_name)
    else:
        cstr="\"%srsvg-convert.exe\" %s %s -o %s "%(EXE_DIR,svg_name,format,out_name)
    
    print cstr
    os.system(cstr)
    
    response = HttpResponse(readFile(out_name),mimetype='application/octet-stream') 
    response['Content-Disposition'] = 'attachment; filename=%s.%s' %(filename,ext)
    
    return response
        
        
'''
    同步旧版数据
'''
def sync_old_ip(request,org_id):
    try:
        old_ip=request.POST.get('old_ip')
        org=Organization.objects.get(pk=org_id)
        
        pos_backend=load_backend('django.db.backends.mysql')
        pos_connection=pos_backend.DatabaseWrapper({
                'HOST': old_ip,
                'NAME': 'coolroid',
                'USER': "root",
                'PASSWORD': "agile",
                'OPTIONS':{},
                'PORT': "3308"
            })
        
        pos_cursor=pos_connection.cursor()
        pos_cursor.execute('SELECT goods_name,goods_code,goods_category_id,category_name,goods_standard,unit,goods_abbreviation,goods_price,goods_refer_price,goods_min_warning,goods_max_warning,goods_nums FROM depot_good a left join depot_category b on a.goods_category_id=b.id left join depot_unit c on a.goods_unit_id=c.id')
        datas=pos_cursor.fetchall()
        
        pos_cursor.execute('SELECT id,category_name,parent_id from depot_category where id>1')
        categorys=pos_cursor.fetchall()
        
        #更新key
        pos_cursor.execute('SELECT key_str,install_date from macros_key_hj')
        reg_key=pos_cursor.fetchone()
        cursor=connections['default'].cursor()

        cursor.execute("UPDATE macros_key_hj SET key_str=%s WHERE key_str IS NULL",(reg_key[0],))
        cursor.close()
        
        pos_cursor.close()
        pos_connection.close()
        
        CATEGORY_DIC={}
        for category in categorys:
            CATEGORY_DIC[category[0]]=[category[1],category[2]]
        
        ABC_DIC={'A':1,'B':2,'C':3}
        
        class _GoodHelp():
            def __init__(self,name,code,category,parent_category,standard,unit,abbreviation,refer_price,min_warning,max_warning,brand,is_batchs,is_sn,ABC,nums,warehouse):
                self.name=name
                self.code=code or ''
                self.category=category
                self.parent_category=parent_category 
                self.standard=standard or ''
                self.unit=unit and Unit.objects.get_or_create(org=org,unit=unit,good__isnull=True)[0] or None
                self.abbreviation=abbreviation
                self.refer_price=refer_price
                self.min_warning=min_warning
                self.max_warning=max_warning
                self.brand=brand and Brand.objects.get_or_create(org=org,brand=brand)[0] or None
                self.is_batchs=is_batchs
                self.is_sn=is_sn
                self.ABC=ABC_DIC.get(ABC,0)
                self.nums=nums
                self.warehouse=warehouse
                #self.warehouse_str=warehouse_str
                
                
            def save(self,invoice):
                try:
                    parent_category=self.parent_category# or _(u'全部分类') 
                    #c=Category.objects.filter(name=u'%s'%self.category,parent__name=u'%s'%parent_category)
                    
                    c=Category.objects.filter(name=u'%s'%(self.category==_(u'默认分类') and  _(u'全部分类') or self.category))
                    
                    if c.count()>1 and parent_category:
                        c=c.filter(parent__name=u'%s'%parent_category)
      
                    if c.exists() and c.count()==1:
                        pass
                    else:
                        print u'(%s)mult category or none,pass[%s,%s]'%(self.name,c.exists(),c.count())
                        msg.append(u'(%s)找到了%s个分类，忽略'%(self.name,c.count()))
                        return None,None
                    
                    
                    obj,created=Goods.objects.get_or_create(name=self.name,org=org,category=c[0],defaults={'code':self.code,'standard':self.standard,
                                            'unit':self.unit,'abbreviation':self.abbreviation,'refer_price':self.refer_price,
                                            'min_warning':self.min_warning,'max_warning':self.max_warning,'brand':self.brand,
                                            'is_batchs':self.is_batchs,'is_sn':self.is_sn,'ABC':self.ABC,'last_modify_user':request.user,
                                            'nums':0,'add_nums':0})
                    #更新已存在的信息
                    if created:
                        #warehouse=Warehouse.get_warehouse_path(org,self.warehouse_str,request.session.get('sites',2))
                        warehouse=self.warehouse
                        if warehouse and self.nums:
                            invoice,created=Invoice.objects.get_or_create(pk=golbal_invoice_id,defaults={'org':org,'result':True,
                                                'invoice_code':(INVOICE_CODE_TEMPLATE%{'date':datetime.datetime.strftime(datetime.datetime.today(),'%Y%m%d'),'seq':golbal_invoice_id}).replace(' ','0'),
                                                'warehouse_root':warehouse.get_root(),'event_date':datetime.date.today(),
                                                'invoice_type':1000,'charger':request.user,'user':request.user,
                                                'confirm_user':request.user,'content_object':request.user})
                            
                            invoiceDetail=InvoiceDetail.objects.create(invoice=invoice,good=obj,batch_code=InvoiceDetail.get_next_detail_code(),
                                                        warehouse=warehouse,warehouse_root=warehouse.get_root(),num1=self.nums,unit1=self.unit,
                                                        price=self.refer_price,avg_price=self.refer_price,num=self.nums,last_nums=self.nums,
                                                        total_price=self.nums*self.refer_price)
                            
                            invoice.total_price+=invoiceDetail.total_price
                            invoice.save()
                            
                            
                            
                        
                        #if self.remark:
                        #    obj.remark=self.remark
                        obj.last_modify_user=request.user
                        obj.save()
                    '''
                        只有初始导入的时候做一些动作
                    '''
    
                    return obj,invoice
                except:
                    print traceback.print_exc()
                    print u'(%s)except,pass'%(self.good_name)
                    return None,None
        goods=[] 
        categorys={}
        child_categorys={}
        categorys_tree=tree()
        msg=[]
        ines=Invoice.objects.filter(id__lte=2000).order_by('-id')
        golbal_invoice_id=ines.exists() and (ines[0].pk+1) or 1000
        warehouse=Warehouse.objects.filter(org=org).order_by('id')[0]
        invoice=None
        
        def process(invoice):
            info=""
            i=1
            ws=set()
            for data in datas:
                i+=1
                j=0
                
                try:
                    _parent_category=CATEGORY_DIC.get(CATEGORY_DIC[data[2]][1],[None,None])[0]  #上级分类
                    _parent_category=(_parent_category!=_(u'默认分类') and _parent_category or None)
                except:
                    _parent_category=None    
                    
                _good=_GoodHelp(
                    data[0],  #物品名称
                    data[1] or None, #编码
                    data[3],  #物品分类
                    _parent_category,
                    data[4],  #规格
                    data[5],  #单位

                    data[6] or get_abbreviation(data[2]), #goods_abbr
                    data[8] or 0,   #goods_price
                    data[9] or -1, #goods_min_warning
                    data[10] or -1, #goods_max_warning
                    None,  #品牌
                    0,   #分批管理
                    0,   #SN管理
                    0,   #ABC
                    data[11] or 0,   #初始库存
                    warehouse, #初始货架
                )
                
                
                #num=sheet[1].has_key((i,10)) and sheet[1][(i,10)] or 0
                '''
                    测试数量和货架填写是否正确
                '''
               
                    
                goods.append(_good)
                log.debug(u'append good %s to good list'%_good.name)
                
                
                parent=_good.parent_category
                child=_good.category
                
                categorys.update({child:True})
                if parent:
                    categorys.update({parent:True})
                    child_categorys.update({child:True})
                    categorys_tree[parent][child]=True
                else:
                    pass
                    #categorys_tree[child]=True
            
            #根据目录结构建立分类     
      
            for key in child_categorys.keys():
                categorys.pop(key)
            import json
            from collections import defaultdict
            def print_key(key,parent_key): 
                '''
                                    新建分类信息，如果有，则忽略
                '''
                if parent_key:
                    ps=Category.objects.filter(name=parent_key)
                    if ps.count()==1:
                        if not key==_(u'默认分类'):
                            Category.objects.get_or_create(name=key,parent=(ps[0]!=_(u'默认分类') and ps[0] or None),org=org,defaults={'user':request.user})
  
                    else:
                        info=u"\n分类%s有多个，忽略"%(parent_key)
                        msg.append(info)
                else:
                    Category.objects.get_or_create(name=key,org=org,defaults={'parent':None,'user':request.user})
                    
                if type(categorys_tree[key])==defaultdict:
                    for k in categorys_tree[key].keys():
                        print_key(k,key)
                
            
            for key in categorys.keys(): 
                print_key(key,_(u'全部分类'))
                
            #将所有的物品录入
            succeesd=0
            
            for good in goods:
                s,invoice=good.save(invoice)
                if s:
                    succeesd+=1
    
            
            msg.append(u'已处理%s个物品'%succeesd)               
            return "%s"%("\n".join(msg)),invoice
        
        response,invoice=process(invoice)
        if invoice:
            try:
                invoice.confirm(request.user)
            except:
                print traceback.print_exc()
        return HttpResponse(response)
        
    except:
        print traceback.print_exc()
        return HttpResponse(_(u'操作失败'));



try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.
import random
from django.conf import settings
from django.utils.decorators import available_attrs
from django.utils.hashcompat import md5_constructor
 
if hasattr(random, 'SystemRandom'):
    randrange = random.SystemRandom().randrange
else:
    randrange = random.randrange
_MAX_CSRF_KEY = 18446744073709551616L     # 2 << 63
 
def _get_new_submit_key():
    return md5_constructor("%s%s" % (randrange(0, _MAX_CSRF_KEY), settings.SECRET_KEY)).hexdigest()
 
def anti_resubmit(page_key=''):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if request.method == 'GET':
                request.session['%s_submit' % page_key] = _get_new_submit_key()
                print 'session:' + request.session.get('%s_submit' % page_key)
            elif request.method == 'POST':
                old_key = request.session.get('%s_submit' % page_key, '')
                if old_key == '':
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect('/page_expir')
                request.session['%s_submit' % page_key] = ''
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator