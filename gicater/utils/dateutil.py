# -*- coding: utf-8 -*- 
import datetime


def datedelta(d,years=0,months=0,weeks=0,days=0):
    '''
    '让python支持年月的加减操作,时间置为凌晨
    '''
    one_day=datetime.timedelta(days=1)
    
    def _month_add(d,v):
        q,r=divmod(d.month+v, 12)
        
        if isinstance(d,datetime.datetime):
            d2=datetime.datetime(d.year+q,r+1,1)-one_day
        elif isinstance(d,datetime.date):
            d2=datetime.date(d.year+q,r+1,1)-one_day
            
        if  d.month!=(d+one_day).month:
            return d2
        
        if d.day>=d2.day:
            return d2
        
        return d2.replace(day=d.day)
    
    if years:
        d=_month_add(d,years*12)
        
    if months:
        d=_month_add(d,months)
        
    if weeks:
        d=d+datetime.timedelta(weeks=weeks)
        
    if days:
        d=d+datetime.timedelta(days=days)
        
    return d


def daterange(start_date, end_date,include_end=False):
    '''
    ' for day in daterange(start_date,end_date,include_end=True):
    '''
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)
    if include_end:
        yield end_date


if __name__=="__main__":
    d=datetime.datetime.now()
    print "set base time is now ",d
    
    print "after 1 year is ",datedelta(d,years=1)
    
    print "6 months and 7 days is",datedelta(d,months=6,days=7)
    
    print "before 3 months is",datedelta(d,years=1,months=-3)