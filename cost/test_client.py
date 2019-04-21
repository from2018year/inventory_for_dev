# -*- coding: utf-8 -*- 
import simplejson
headers={'user-agent':'Mozilla/5.0 (Windows NT 6.1; rv:15.0) Gecko/20100101 Firefox/15.0.1',
         'referer':''}
url=u"http://192.168.1.102:83/cost/cost_sync/?guid={0012}"


import urllib2,urllib
d=urllib2.urlopen(urllib2.Request(url,headers=headers)).read()

req_dict=simplejson.loads(d)
token=req_dict['token']
last_sync_time=req_dict['last_sync']

print token,last_sync_time
sale={'guid':'{0000-DEFAULT-0000}','datas':[
        {'zdate':'2015-01-30','details':[
            {'item_id':1010,'item_name':(u'四喜'),
                'nlu':'1010','price':14,'num':1,
                'total_price':14,'unit':''
            },
            {'item_id':1011,'item_name':(u'五福'),
                'nlu':'1011','price':15,'num':1,
                'total_price':15,'unit':'瓶'
            },
            {'item_id':1012,'item_name':(u'六粮'),
                'nlu':'1012','price':10,'num':1,
                'total_price':10,'unit':'杯'
            }]
        }
    ]}

sale_str=simplejson.dumps(sale)
print urllib.urlencode({'token':token[1:],'sale_str':sale_str})
#d=urllib2.urlopen(urllib2.Request(url,headers=headers),urllib.urlencode({'token':token[1:],'sale_str':sale_str})).read()
#print d
