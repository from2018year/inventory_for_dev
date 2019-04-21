# -*- coding: utf-8 -*- 
import urllib,urlparse

'''
    本库下包含url操作的一些辅助函数
'''

def add_params_to_url(url,params):
    '''
        add_params_to_url函数将字典形式的参数加到已存在的url上
        
        url参数是字符串格式
        
        params参数是字典格式
    '''
    
    url_parts=list(urlparse.urlparse(url))
    query=dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    
    url_parts[4]=urllib.urlencode(query)
    
    return urlparse.urlunparse(url_parts)

def del_params_from_url(url,params):
    '''
        del_params_from_url函数删除给定的参数
        
        url参数是原始的字符串格式
        
        params参数是字符串或list格式(删除多参数)
    '''

    url_parts=list(urlparse.urlparse(url.encode('utf8')))
    
    query=dict(urlparse.parse_qsl(url_parts[4]))
    
    if isinstance(params, (tuple,list)):
        for param in params:
            query.pop(param,None)
    else:
        query.pop(params,None)
    
    url_parts[4]=urllib.urlencode(query)
    
    return urlparse.urlunparse(url_parts)

def get_url_param(url,key):
    '''
        get_url_param函数得到给定url中的参数值,如果没找到返回None
        
        url参数是字符串格式
        
        key为字符串
    '''
    url_parts=list(urlparse.urlparse(url))
    query=dict(urlparse.parse_qsl(url_parts[4]))
    
    return query.has_key(key) and query[key] or None

    