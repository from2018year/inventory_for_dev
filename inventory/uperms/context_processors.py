from inventory.uperms import OPermWrapper
from depot.models import Organization
from inventory.settings import STYLE

def auth_org_perm(request):
    """
    Returns context variables required by apps that use Django's authentication
    system.

    If there is no 'user' attribute in the request, uses AnonymousUser (from
    django.contrib.auth).
    """
    if hasattr(request, 'user'):
        user = request.user
    else:
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()
    
    org=request.session.get('org',None)
    org_id=org and org.pk or 0
        
    def _is_root_org(org_id):
        try:
            org_id=int(org_id)
            if org_id:
                if Organization.objects.get(pk=org_id).parent:
                    return False
                else:
                    return True
            else:
                return False
        except:
            return False
        
        
    if user.is_anonymous() or not org_id or request.path=='/':
        return {'INDUSTRY':(org and org.style=='retail') and 'retail' or 'restaurant'}

    
    return {
        'is_root_org':_is_root_org(org_id),
        'operms': OPermWrapper(user,org_id),
        'warehouse_perm':user.get_warehouses(org_id),
        'warehouse_write_perm':user.get_warehouses(org_id,perms=['warehouse_write']),
        'is_superior':user.is_org_superuser(org_id),
        #'wm_perm':user.get_warehouses(org_id,perms=['warehouse_manage']),
        #'pandian_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_pandian_read','warehouse_pandian_write']),
        #'caigou_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_caigou_read','warehouse_caigou_write']),
        #'tuihuo_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_tuihuo_read','warehouse_tuihuo_write']),
        #'lingyong_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_lingyong_read','warehouse_lingyong_write']),
        #'tuiliao_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_tuiliao_read','warehouse_tuiliao_write']),
        #'xiaoshou_perm':user.get_warehouses(org_id,perms=['warehouse_manage','warehouse_xiaoshou_read','warehouse_xiaoshou_write']),
        
        'agile':STYLE=='agile',
        'INDUSTRY':(org and org.style=='retail') and 'retail' or 'restaurant'
    }