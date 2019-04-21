# -*- coding: utf-8 -*- 
import traceback
import decimal
import datetime
import logging
import re
#FORMAT = '[%(levelname)s]%(asctime)s(%(filename)s %(lineno)d):%(message)s'
#logging.basicConfig(name="gicater.utils.common",format=FORMAT,level=logging.DEBUG,datefmt='%Y-%m-%d %H:%M:%S')

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

try:
    '''
    ' 让django的json支持日期  Decimal等类型
    ' 用法  simplejson.dumps(dumpObj,cls=GicaterEncoder)
    '''
    from django.utils import simplejson
    class GicaterEncoder(simplejson.JSONEncoder):
        def default(self, obj):
            '''Convert object to JSON encodable type.'''
            if isinstance(obj, decimal.Decimal):
                return float("%s" % obj)
            
            if isinstance(obj,datetime.datetime):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            
            if isinstance(obj,datetime.date):
                return obj.strftime("%Y-%m-%d")
            
            if isinstance(obj,datetime.time):
                return obj.strftime('%H:%M')
            
            
            return simplejson.JSONEncoder.default(self, obj)
except:
    pass



def sendSms(msg,mobiles,userid,account,password,gateway='http://211.147.242.161:8888/sms.aspx'):
    '''
    ' mobiles 手机号码，多个时用,隔开
    '''
    data={}
    data['userid']=userid
    data['account']=account.encode('utf8')
    data['password']=password
    data['action']='send'
    data['content']=msg.encode('utf8')
    data['mobile']=mobiles
    
    import urllib2,urllib
    try:
        response = urllib2.urlopen(gateway,urllib.urlencode(data))
        xml=response.read()
        
        root=ET.fromstring(xml)
        res_dict=dict([(child.tag,child.text) for child in root]) 
        logging.debug(str(res_dict))
        return res_dict
    except:
        print traceback.print_exc()
        return {'error':u"网络错误"}
    
def sendTwilioSms(msg, mobiles, sid, token, mfrom):
    from twilio.rest import Client
    
    msg_to=mobiles
    
    try:
        client = Client(sid, token)
        message = client.messages.create(
            to=msg_to, 
            from_=mfrom,
            body=msg)

        print(message.status)
        return 1
    except:
        print(traceback.print_exc())
        return 0
    
re_phone=re.compile('^1[358]\d{9}$|^170\d{8}')
def valid_phone(phone):
    return isinstance(phone,(str,unicode)) and bool(re_phone.match(phone))


# -*- coding: utf-8 -*- 
from email.mime.text import MIMEText 
import smtplib
import os
from django.template import Template,Context


log=logging.getLogger(__name__)


def email_template(template,data):
    '''
    '利用django template格式化发送内容
    '参数：
    ’    template:模板名称，改模板是邮件模块下自带的
    '    data:字典格式，用于渲染模板的变量
    '''
    f=open(os.path.join(os.path.dirname(__file__),template))
    html_str=f.read()
    f.close()
    
    t=Template(html_str)
    
    templates=Context(data)
    return t.render(templates)

def send_email(**kwargs):      
    '''
    '与邮件服务器通信，发动邮件
    '由于当前参数不明确，暂定为**kwargs
    '''
    mail_host=kwargs.get('mail_host')
    #mail_postfix=kwargs.get('mail_postfix',None)
    mail_type=kwargs.get('mail_type',None)
    
    mail_user=kwargs.get('mail_user')
    mail_pass=kwargs.get('mail_pass')
    mail_to=kwargs.get('mail_to',None)
    mail_sub=kwargs.get('mail_sub',None)
    mail_content=kwargs.get('mail_content',None)
    
    msg = MIMEText(mail_content,_subtype='html',_charset='utf-8')    
    msg['Subject'] = mail_sub   
    #msg['From'] = me=mail_user+"@"+mail_postfix 设置发送人。别名，可能会导致误认垃圾邮件
    me=mail_user   #发送人。
    msg['From']=mail_user
        
    if isinstance(mail_to, list):
        msg['To'] = ",".join(mail_to)
    else:
        msg['To'] = mail_to
    try:  
        s = smtplib.SMTP(timeout=30)  
        s.connect(mail_host,80)  #连接smtp服务器
        s.login(mail_user,mail_pass)  #登陆服务器
        s.sendmail(me, mail_to, msg.as_string())  #发送邮件
        s.quit()  
        log.debug("send email to %s success"%mail_to)
        return True  
    except Exception, e:  
        print str(e)  
        log.debug("send email to %s failed"%mail_to)
        return False   

    
if __name__=="__main__":
    
    '''
    
    email_data={'username':'username'}
    email_content="Hello World" #email_template("invite_bb8.html",email_data)
    email_content=str(email_content)


    email_sub = u"join in BB8"
    send_email(mail_type="bb8",
                mail_to=['1849896877@qq.com'],mail_sub=email_sub,mail_content=email_content)  
    '''
    
    #sendTwilioSms("【来电】send msg from twilio,just a test", "+8618676720259")