# -*- coding: utf-8 -*- 
import math   
import random
import os
import re

class NumTooLargeException(Exception):
    pass


def randomStr(min_length=8,max_length=8,upper=False,zero=False,only_num=False):
    """
    'min_length:返回的最小长度
    'max_length:返回的最大长度
    'zero:是否去除0与O,1与lI,2与Z,8与B
    """
    num_str="1234567890"
    num_str_nozero="345679"
    char_str="abcdefghijklmnopqrstuvwxyz"
    char_str_nozero="abcdefghijkmnpqrstuvwxy"
    
    min_length=(min_length>0) and min_length or 8
    max_length=(max_length>=min_length) and max_length or min_length
    
    str = ''
    if zero:
        chars = char_str+num_str
    else:
        chars = char_str_nozero+num_str_nozero
    if only_num:
        chars=num_str
        
    length = len(chars) - 1
    for i in range(max_length):
        str+=chars[random.randint(0, length)]
        
    return upper and str[:random.randrange(min_length,max_length+1)].upper() or str[:random.randrange(min_length,max_length+1)]

def numtoCny(num):  
    """
    '将浮点数或整数转化为人民币的大写形式
    '小数位最多支持到2位，多余的忽略
    '整数位最多支持到16位，多余将爆出异常
    """ 
    capUnit = ['万','亿','万','圆','']   
    capDigit = { 2:['角','分',''], 4:['仟','佰','拾','']}   
    capNum=['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']   
    snum = str('%019.02f') % num   
    if snum.index('.')>16:   
        raise NumTooLargeException("num to large")
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


def get_abbreviation(str_input,upper=True):
    '''
    '得到拼音的首字母，暂时未处理多音字
    '''
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
        return_list.append(_single_get_first(one_unicode))
    return upper and "".join(return_list).upper() or "".join(return_list)
    
def _single_get_first(unicode1):
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


def convent_TW(line,charset=None):
    from helper.langconv import Converter
    '''
    ' 将简体中文的语句转化为繁体
    ’ line为unicode或指定字符集
    ' zh_wiki.py:https://github.com/skydark/nstools/blob/master/zhtools/zh_wiki.py
    ' langconv.py:https://github.com/skydark/nstools/blob/master/zhtools/langconv.py
    '''

    line = Converter('zh-hant').convert(charset and line.decode(charset) or line)   
    return charset and line.encode(charset) or line
     
def convert_django_cn_to_tw(file_path): 
    '''
    ' django1.4.2下测试过
    ' 在同翻译文件的目录下生成.po.po文件，如果检查核实，手动重命名覆盖
    '''

    
    TW_FILE_ARR=[file_path.replace('\\','/')] #,os.path.join(BASE,'../locale/zh_TW/LC_MESSAGES/djangojs.po').replace('\\','/')
    
    for TW_FILE in TW_FILE_ARR:
        TW_FILE_BAK="%s.po"%TW_FILE
        
        file=open(TW_FILE)
        file_bak=open(TW_FILE_BAK,'w+')
        
        mult_line_start=False
        last_word_tw=""
        mult_line=[]
        
        for line in file:
            word=re.findall(r"msgid \"(.*)\"",line)
            re_word=re.findall(r"msgstr \"(.*)\"",line)    
           
            if word:
                file_bak.write(line)
                if word[0]:
                    mult_line_start=False
                    last_word_tw=convent_TW(word[0],'utf8')
                else:
                    mult_line_start=True
            
            elif re_word:
                mult_line_start=False
                if mult_line:
                    file_bak.write("msgstr \"\"")
                else:
                    file_bak.write("msgstr \"%s\"\n"%(last_word_tw))
                
            else:
                file_bak.write(line)
                
                if mult_line_start:
                    mult_line.append(line)
                elif mult_line:
                    
                    for l in mult_line:
                        file_bak.write(convent_TW(l,'utf8'))
                    mult_line=[]
                    
                        
                
        file.close()
        file_bak.close()


if __name__=="__main__":
    print "numtocny 123 is",numtoCny(123)
    print "numtocny 100.5 is",numtoCny(100.5)
    print "numtocny 123456789.53 is",numtoCny(212345123456789.53)
    
    print get_abbreviation(u'卧梅又闻花,长长',upper=False)
    print convent_TW(u'（注意：如曾安装过Lodop旧版附件npActiveXPLugin,请在【工具】->【附加组件】-')
    print convent_TW('（注意：如曾安装过Lodop旧版附件npActiveXPLugin,请在【工具】->【附加组件】-','utf8')
    
    convert_django_cn_to_tw(r"D:\workspace\member_version\member\locale\zh_TW\LC_MESSAGES\djangojs.po")