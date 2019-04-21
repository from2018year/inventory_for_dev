# -*- coding: utf-8 -*- 
from pyExcelerator.Workbook import Workbook
from pyExcelerator import CompoundDoc
from MACROS import DATE_UNIT_TYPES as TIME_SPAN
from inventory.settings import DATABASES, STYLE
from django.db import models
import random
import hashlib
import traceback
from django.db import connection
import decimal,datetime,os,uuid,time
import socket
import logging
log=logging.getLogger(__name__)

def get_next_increment(amodel):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute( "SELECT Auto_increment FROM information_schema.tables WHERE table_schema='%s' and table_name='%s';" % (DATABASES['default']['NAME'],amodel._meta.db_table))
    
    row = cursor.fetchone()
    cursor.close()
    return row[0]

def fix_get_next_increment(amodel):
    return get_next_increment(amodel) + 1

class SQLCountCase(models.sql.aggregates.Aggregate):
    is_ordinal = True
    sql_function = 'COUNT'
    sql_template = "%(function)s(CASE %(case)s WHEN %(when)s THEN 1 ELSE null END)"

    def __init__(self, col, **extra):
        if isinstance(extra['when'], basestring):
            extra['when'] = "'%s'"%extra['when']

        if not extra.get('case', None):
            extra['case'] = '"%s"."%s"'%(extra['source'].model._meta.db_table, extra['source'].name)

        if extra['when'] is None:
            extra['when'] = True
            extra['case'] += ' IS NULL '

        super(SQLCountCase, self).__init__(col, **extra)

class CountCase(models.Aggregate):
    name = 'COUNT'

    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = SQLCountCase(col, source=source, is_summary=is_summary, **self.extra)
        query.aggregates[alias] = aggregate
        
        
class SQLSumCase(models.sql.aggregates.Aggregate):
    is_ordinal = False
    sql_function = 'SUM'
    sql_template = "%(function)s(CASE %(case)s WHEN %(when)s THEN %(field)s ELSE 0.0 END)"

    def __init__(self, col, **extra):
        if isinstance(extra['when'], basestring):
            extra['when'] = "'%s'"%extra['when']

        if not extra.get('case', None):
            extra['case'] = '"%s"."%s"'%(extra['source'].model._meta.db_table, extra['source'].name)

        if extra['when'] is None:
            extra['when'] = True
            extra['case'] += ' IS NULL '

        super(SQLSumCase, self).__init__(col, **extra)

class SumCase(models.Aggregate): # TODO
    name = 'SUM'

    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = SQLSumCase(col, source=source, is_summary=is_summary, **self.extra)
        query.aggregates[alias] = aggregate


import math   
def numtoCny(num):   
    capUnit = ['万','亿','万','圆','']   
    capDigit = { 2:['角','分',''], 4:['仟','佰','拾','']}   
    capNum=['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']   
    snum = str('%019.02f') % num   
    if snum.index('.')>16:   
        return ''  
    ret,nodeNum,subret,subChr='','','',''  
    CurChr=['','']   
    for i in range(5):   
        j=int(i*4+math.floor(i/4))   
        subret=''  
        nodeNum=snum[j:j+4]   
        lens=len(nodeNum)   
        for k in range(lens):   
            if int(nodeNum[k:])==0:   
                continue  
            CurChr[k%2] = capNum[int(nodeNum[k:k+1])]   
            if nodeNum[k:k+1] != '0':   
                CurChr[k%2] += capDigit[lens][k]   
            if  not ((CurChr[0]==CurChr[1]) and (CurChr[0]==capNum[0])):   
                if not((CurChr[k%2] == capNum[0]) and (subret=='') and (ret=='')):   
                    subret += CurChr[k%2]   
        subChr = [subret,subret+capUnit[i]][subret!='']   
        if not ((subChr == capNum[0]) and (ret=='')):   
            ret += subChr   
    return [ret,capNum[0]+capUnit[3]][ret=='']  


'''
    python支持时间操作
'''
def datedelta(d,value,type):
    one_day=datetime.timedelta(days=1)
    
    def _month_add(d,v):
        q,r=divmod(d.month+v, 12)
        
        d2=datetime.datetime(d.year+q,r+1,1)-one_day
        if  d.month!=(d+one_day).month:
            return d2
        
        if d.day>=d2.day:
            return d2
        
        return d2.replace(day=d.day)
        
    if type==TIME_SPAN[0][0]:
        #天
        return d+datetime.timedelta(days=value)
    elif type==TIME_SPAN[1][0]:
        #周
        return d+datetime.timedelta(weeks=value)
    elif type==TIME_SPAN[2][0]:
        return _month_add(d,value)
    elif type==TIME_SPAN[3][0]:
        return _month_add(d,value*12)
    else:
        raise Exception(_(u'不支持的类型'))
    
'''
    Excel 上传下载支持
'''

def _save_stream(self,stream):
    # 1. Align stream on 0x1000 boundary (and therefore on sector boundary)
    padding = '\x00' * (0x1000 - (len(stream) % 0x1000))
    self.book_stream_len = len(stream) + len(padding)

    self._XlsDoc__build_directory()
    self._XlsDoc__build_sat()
    self._XlsDoc__build_header()
        
    s=""
    s="%s%s"%(s,str(self.header))
    s="%s%s"%(s,str(self.packed_MSAT_1st))
    s="%s%s"%(s,str(stream))
    s="%s%s"%(s,str(padding))
    s="%s%s"%(s,str(self.packed_MSAT_2nd))
    s="%s%s"%(s,str(self.packed_SAT))
    s="%s%s"%(s,str(self.dir_stream))
        
    return s
class _Wookbook(Workbook):
    '''
    ’返回二进制流以供response返回
    '''
    def __init__(self, *args, **kwds):
        Workbook.__init__(self, *args, **kwds)
        CompoundDoc.XlsDoc.save_stream=_save_stream 
        
    def save_stream(self):
        doc=CompoundDoc.XlsDoc()
        return doc.save_stream(self.get_biff_data())
    
'''
    上传文件的辅助方式
'''
def handle_uploaded_file(pwd,f,nf):
    destination=open("%s/%s"%(pwd,nf and nf or f.name),'wb+')
    for chunk in f.chunks():
        destination.write(chunk)

'''
    测试端口是否开启
'''
def isOpen(ip,port,time_out=5):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(time_out)
    try:
        s.connect((ip,int(port)))
        s.shutdown(2)
        s.close()
        return True
    except:
        return False
    
'''
    得到文件的MD5
'''
def file_md5(filePath):
    with open(filePath, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()
    
'''
    得到多文件的MD5
'''
def multfile_md5(filePath):
    m = hashlib.md5()
    if isinstance(filePath, (list,tuple)):
        for _filePath in filePath:
            with open(_filePath, 'rb') as fh:
                while True:
                    data = fh.read(8192)
                    if not data:
                        break
                    m.update(data)
    else: 
        with open(filePath, 'rb') as fh:
            while True:
                data = fh.read(8192)
                if not data:
                    break
                m.update(data)
    return m.hexdigest()
            
'''
    模拟tree
'''
from collections import defaultdict
def tree():
    return defaultdict(tree)

'''
    得到拼音首字母
'''
def get_abbreviation(str_input):
    
    if isinstance(str_input, unicode):
        unicode_str = str_input
    else:
        try:
            unicode_str = str_input.decode('utf8')
        except:
            try:
                unicode_str = str_input.decode('gbk')
            except:
                print 'unknown coding'
                return
    
    return_list = []
    for one_unicode in unicode_str:
        #print single_get_first(one_unicode)
        return_list.append(single_get_first(one_unicode))
    return "".join(return_list).upper()   
    
def single_get_first(unicode1):
    str1 = unicode1.encode('gbk')
    try:        
        ord(str1)
        return str1
    except:
        asc = ord(str1[0]) * 256 + ord(str1[1]) - 65536
        if asc >= -20319 and asc <= -20284:
            return 'a'
        if asc >= -20283 and asc <= -19776:
            return 'b'
        if asc >= -19775 and asc <= -19219:
            return 'c'
        if asc >= -19218 and asc <= -18711:
            return 'd'
        if asc >= -18710 and asc <= -18527:
            return 'e'
        if asc >= -18526 and asc <= -18240:
            return 'f'
        if asc >= -18239 and asc <= -17923:
            return 'g'
        if asc >= -17922 and asc <= -17418:
            return 'h'
        if asc >= -17417 and asc <= -16475:
            return 'j'
        if asc >= -16474 and asc <= -16213:
            return 'k'
        if asc >= -16212 and asc <= -15641:
            return 'l'
        if asc >= -15640 and asc <= -15166:
            return 'm'
        if asc >= -15165 and asc <= -14923:
            return 'n'
        if asc >= -14922 and asc <= -14915:
            return 'o'
        if asc >= -14914 and asc <= -14631:
            return 'p'
        if asc >= -14630 and asc <= -14150:
            return 'q'
        if asc >= -14149 and asc <= -14091:
            return 'r'
        if asc >= -14090 and asc <= -13119:
            return 's'
        if asc >= -13118 and asc <= -12839:
            return 't'
        if asc >= -12838 and asc <= -12557:
            return 'w'
        if asc >= -12556 and asc <= -11848:
            return 'x'
        if asc >= -11847 and asc <= -11056:
            return 'y'
        if asc >= -11055 and asc <= -10247:
            return 'z'
        return ''

'''
    将时间变为一个序列
'''
def daterange(start_date, end_date,include_end=False):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)
    if include_end:
        yield end_date
        

def readcpuid():
    try:
        os.popen('wmic cpu get ProcessorId')
        s=os.popen('wmic cpu get ProcessorId')
        line=s.readline()
        while line:
            if line.lower().index("processorid")==0:
                cpuid=s.readline()
                break
            line=s.readline()
        restr=uuid.uuid3(uuid.NAMESPACE_DNS,cpuid)
        if STYLE=="inventory_en":#如果是英文版的，在最后加“-1”
            restr = str(restr)+'-1'
            
        return restr  
    except:
        print traceback.print_exc()
        cursor=connection.cursor()
        cursor.execute("select key_str,aes_decrypt(install_date,'salt') from macros_key_hj")
        row=cursor.fetchone() 
        cpuid=str(time.strptime(row[1],'%Y-%m-%d'))
        restr=uuid.uuid3(uuid.NAMESPACE_DNS,cpuid)
        if STYLE=="inventory_en":#如果是英文版的，在最后加“-1”
            restr = str(restr)+'-1'
            
        return restr   
        
NUMS="1234567890"
VNUMS="123456789"
LETTERS="abcdefghijklmnopqrstuvwxyz".upper()
JISHU="13579"
OUSHU="02468"
'''
    校验注册码
    返回0-正常 1-逻辑错误 2-md5错误 3-过期
'''      
def check_ma(ma_str,reg=False):
    try:
        time_str='%s%s'%(ma_str[16:22],ma_str[38:44])
        md5_str='%s%s'%(ma_str[0:16],ma_str[22:38])
        now=datetime.datetime.now()
        
        sites=2
        sites_str=None
        if len(ma_str)==48:
            sites_str=ma_str[44:]
        
        if hashlib.md5('coolroid_inventory%s'%(readcpuid())).hexdigest().upper()==md5_str.upper():
            s="%04d%04d"%((int(time_str[0:4])+int(time_str[4:8]))%10000,(int(time_str[0:4])+int(time_str[8:12]))%10000)
            if sites_str:
                sites='%d'%((int(time_str[0:4])+int(sites_str))%10000)
            _date=time.strptime(s,'%Y%m%d')
            _date=datetime.datetime(*_date[:6])
            if _date<now:
                return 3,_date,sites
            else:
                #插入数据库
                return 0,_date,sites
        else:
            return 2,None,None
        
    except:
        print traceback.print_exc()
        return 1,None,None
    
    
def create_ma(m_id,nyear):
    '''
        得到随机字符串
        string是随机字符串长
        length是长度
    '''
    def randomStr(string,length):
        return "".join(random.sample(string,length))
    
    time_str_list=[]
    _day=datetime.datetime.now()
    day=datedelta(_day,nyear,4)
    time_help=(randomStr(NUMS[:9],4))
    
    md5_str=hashlib.md5('coolroid_inventory%s'%m_id).hexdigest().upper()
    
    
    time_str_list.append(time_help)
    time_str_list.append('%04d'%((day.year-int(time_help)+10000)%10000))
    time_str_list.append('%04d'%((int('%02d%02d'%(day.month,day.day))-int(time_help)+10000)%10000))
    
    time_str="".join(time_str_list)
    
    return '%s%s%s%s'%(md5_str[0:16],time_str[0:6],md5_str[16:],time_str[6:])

def create_ma_web(m_id,nyear=0,sites=1,add_sites=0):
    from depot.models import Organization,MacrosKeyWeb
    '''
        得到随机字符串
        string是随机字符串长
        length是长度
    '''
    def randomStr(string,length):
        return "".join(random.sample(string,length))
    
    if isinstance(m_id, Organization):
        m_id=m_id.pk
        org=m_id
    else:
        org=Organization.objects.get(pk=m_id)
        
    try:
        old_ma=MacrosKeyWeb.objects.filter(org=org)[0]
    except:
        old_ma=None
        
    time_str_list=[]
    if old_ma:
        res,_day,sites=fetch_key_web(old_ma)
        log.debug("expired date is %s,sites is %s"%(_day,sites))
    else:
        _day=datetime.datetime.now()
    
    sites=int(sites)+add_sites
    
    if isinstance(nyear, int):      
        if nyear:
            day=datedelta(_day,nyear,4)
        elif not old_ma:
            day=datedelta(_day,1,3)
        else:
            day=_day
    elif isinstance(nyear, float):
        months = int(nyear*10)
        day=datedelta(_day, months, 3)
    else:
        day = nyear
        
    if not old_ma:    
        day=datedelta(day,1,1)
    time_help=(randomStr(NUMS[:9],4))
    
    
        
    md5_str=hashlib.md5('coolroid_inventory%s'%m_id).hexdigest().upper()
    
    
    time_str_list.append(time_help)
    time_str_list.append('%04d'%((day.year-int(time_help)+10000)%10000))
    time_str_list.append('%04d'%((int('%02d%02d'%(day.month,day.day))-int(time_help)+10000)%10000))
    
    time_str_list.append('%04d'%((sites-int(time_help)+10000)%10000))
    
    time_str="".join(time_str_list)
    
    return '%s%s%s%s'%(md5_str[0:16],time_str[0:6],md5_str[16:],time_str[6:])
        
def fetch_key(only_check=False):
    cursor=connection.cursor()
    cursor.execute("select key_str,aes_decrypt(install_date,'salt') from macros_key_hj")
    row=cursor.fetchone()
    
    if row[0]:
        res,d,sites=check_ma(row[0])
        #print 'xxxxxxxxxxxxxxxxxx',row[0],row[1],res,d,sites
        return row[0],row[1],res,d,sites
    else:
        if only_check:
            return False
        return row[0],row[1],None,None,2
    
'''  
 返回0-正常 1-逻辑错误 2-md5错误 3-过期  
 key可以是MacrosKeyWeb类型
 也可以是字符串，为字符串时必须指定oeg_id 
'''
def fetch_key_web(key,org_id=None):
    try:
        if not org_id:
            ma_str=key.key_str
        else:
            ma_str=key
        time_str='%s%s'%(ma_str[16:22],ma_str[38:44])
        md5_str='%s%s'%(ma_str[0:16],ma_str[22:38])
        now=datetime.datetime.now()
        
        sites=1
        sites_str=None
        if len(ma_str)==48:
            sites_str=ma_str[44:]
            
        
        if hashlib.md5('coolroid_inventory%s'%(org_id or key.org_id)).hexdigest().upper()==md5_str.upper():
            s="%04d%04d"%((int(time_str[0:4])+int(time_str[4:8]))%10000,(int(time_str[0:4])+int(time_str[8:12]))%10000)
            if sites_str:
                sites='%d'%((int(time_str[0:4])+int(sites_str))%10000)
            _date=time.strptime(s,'%Y%m%d')
            _date=datetime.datetime(*_date[:6])
            if _date<now:
                return 3,_date,sites
            else:
                #插入数据库
                return 0,_date,sites
        else:
            return 2,None,None
        
    except:
        print traceback.print_exc()
        return 1,None,None

def update_key(key_str,id=None):
    cursor=connection.cursor()
    num=cursor.execute("update macros_key_hj set key_str='%s'"%key_str)
    return num

def update_key_web(key_str,org):
    from depot.models import MacrosKeyWeb
    return MacrosKeyWeb.objects.get_or_create(org=org,key_str=key_str)[0]
