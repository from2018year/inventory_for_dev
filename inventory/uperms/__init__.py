# -*- coding: utf-8 -*- 
if __name__=='__main__':
    from django.core.management import setup_environ
    import os, sys
    
    BASE=os.path.dirname(os.path.abspath(__file__))
    dirname = os.path.dirname(os.path.join(BASE,'../../').replace('\\','/'))
    print dirname
    sys.path.append(dirname)
    import inventory.settings as settings # Assumed to be in the same directory.
    setup_environ(settings)
        
from django.contrib.auth.models import User    
    
class OPermLookupDict(object):
    def __init__(self, user, module_name,org_id):
        self.user, self.module_name,self.org_id = user, module_name,org_id

    def __repr__(self):
        return str(self.user.get_org_permissions(org_id=self.org_id))

    def __getitem__(self, perm_name):
        return self.user.has_org_perm(self.org_id,"%s.%s" % (self.module_name, perm_name))

    def __nonzero__(self):
        return self.user.has_module_perms(self.module_name)


class OPermWrapper(object):
    def __init__(self, user,org_id):
        self.user = user
        self.org_id=org_id

    def __getitem__(self, module_name):
        return OPermLookupDict(self.user, module_name,self.org_id)

    def __iter__(self):
        # I am large, I contain multitudes.
        raise TypeError("PermWrapper is not iterable.")


def _test():
    user=User.objects.get(pk=578)
    
    print user.get_org_group_permissions(86)
    print user.get_org_group_permissions(86)
    #print user.get_org_group_permissions(1)
    #print user.get_org_permissions(1)
    
    #print user.has_org_perm(1,'orgs.chongzhi')
    print user.has_org_perm(86,'depot.wupin_ui')
    print user.has_org_warehouse_perm(86,'depot.wupin_ui')
    #print 'orgs.manage' in user.get_org_permissions(2)
    #print user.is_org_superuser(org_id=2)
    print(OPermWrapper(user,86))
    
    #from django.contrib.auth.context_processors import PermWrapper
    #print PermWrapper(user)['orgs.kaika']
    
if __name__=='__main__':
    

    _test()
    
