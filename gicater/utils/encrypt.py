# -*- coding: utf-8 -*- 
import hashlib


KEY_GICATER_MEMBER="gicater"

def encrypt_half_md5(s,key=KEY_GICATER_MEMBER):
    '''
    '此加密方式为传入的字符连接给定秘钥经过md5加密，然后取md5的偶数位后倒置
    '''
    m=hashlib.md5((u"%s%s"%(s,key)).encode('utf8'))
    code=list(m.hexdigest()[1::2])
    code.reverse()
    return "".join(code)
    
    
    
def valid_half_encrypt(s,encrypt_str,key=KEY_GICATER_MEMBER):
    '''
    '此解密方法将验证传入的encrypt_str是否为s经过encrypt_half_md5加密后的字符串
    '''
    m=hashlib.md5((u"%s%s"%(s,key)).encode('utf8'))
    code=list(m.hexdigest()[1::2])
    code.reverse()

    return "".join(code)==encrypt_str


def encrypt_pos(s,key):
    '''
    '此加密方法用于和POS验证时使用,key取当前时间的时间戳（1970到现在的秒数）+gk
    '''
    return hashlib.md5((u"%s%s"%(s,key)).encode('utf8')).hexdigest()

def valid_pos(s,encrypt_str,key):
    '''
    '此解密方法用于和POS验证时使用,验证POS传递的请求是否为合法的
    '''
    return hashlib.md5((u"%s%sgk"%(s,key)).encode('utf8')).hexdigest()==encrypt_str



if __name__=="__main__":
    import time
    ss=["{0001-test}",u'uniocde字符试试']
    for s in ss:
        print "test ",s,type(s)
        x=encrypt_half_md5('add_new',"1428564146")
        print "after encrypt_half_md5" ,s," is ",x
    
        print "valid_half_encrypt",valid_half_encrypt(s,x)
        
    print 'create pos access'
    guid="eeee"
    _t=str(int(time.time()))
    print "?guid="+guid+"&token="+encrypt_pos(guid,_t+'gk')+"&t="+_t
        
