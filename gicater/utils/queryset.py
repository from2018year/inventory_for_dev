# -*- coding: utf-8 -*- 
import itertools
import operator
try:
    '''
    '此段只有在django中生效，增强查询统计功能，
    queryset.values('good','good__name').annotate(
        num=SumCase('num',case='depot_ininvoice.invoice_type in (1,2,3)',when=True),
        total=CountCase('price',case='depot_ininvoice.invoice_type',when=5)
    )  
    '''
    from django.db import models
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
except:
    pass

class GeneratorLen(object):
    """
    ’ 将用户自定义的查询转化为可迭代的形式
    ' 在templates中可以使用for迭代，就如同普通的queryset
    """
    def __init__(self,it,leng):
        self.it=it
        self.leng=leng
    def __len__(self):
        return self.leng
        
    def __iter__(self):
        for elt in self.it:
            yield elt
    def __getitem__(self,index):
        try:
            return next(itertools.islice(self.it,index,index+1))
        except TypeError:
            return list(itertools.islice(self.it,index.start,index.stop,index.step))
        
        
def dictfetchall(cursor_or_fetchall,desc=None,as_list=False):
    """
    '    自定义的查询返回为字典的list格式
    '    如果直接传递cursor,则无需再传入desc
    '    如果是传递的cursor.fetchall之后的内容，则需要同时传入desc=cursor.description
    """
    if type(cursor_or_fetchall)!=tuple:
        desc = desc and desc or cursor_or_fetchall.description
        
    ret=(
        dict(zip([col[0] for col in desc], row))
        for row in (type(cursor_or_fetchall)==tuple and [cursor_or_fetchall] or [cursor_or_fetchall.fetchall()])[0]
    )
    
    if as_list:
        ret=[x for x in ret]

    return ret

try:
    from django.db.models import Q
    import mptt
    def get_queryset_descendants(cls,nodes,include_self=False): 
        """
        '    基于mptt的cls，用于返回一个queryset的子接点
        """
        if not isinstance(cls, mptt.models.MPTTModelBase):
            raise Exception(u"only MPTTModel can use this method.")
        if not nodes: 
            return cls.objects.none() 
        filters = [] 
        for n in nodes: 
            lft, rght = n.lft, n.rght 
            if include_self: 
                lft -=1 
                rght += 1 
            filters.append(Q(tree_id=n.tree_id, lft__gt=lft, rght__lt=rght)) 
        q = reduce(operator.or_, filters) 
        return cls.objects.filter(q)
except:
    pass
    
    
if __name__=="__main__":
    import MySQLdb
    
    conn=MySQLdb.connect(host="localhost",user="root",passwd="agile",port=3308,db="mysql")
    cursor=conn.cursor()
    
    length=cursor.execute("select * from user")
    
    res=cursor.fetchall()
    desc = cursor.description
    
    cursor.close()
    conn.close()
    
    print "row data",res
    dict_res=dictfetchall(res,desc)
    print "after dictfetch",dict_res
    for r in dict_res:
        print "username is",r['User']
    
    dict_res=dictfetchall(res,desc)
    gener_res=GeneratorLen(dict_res,length)  
     
    print 'after GeneratorLen',gener_res,"length is",len(gener_res)
    for r in gener_res:
        print "username is",r['User']
    