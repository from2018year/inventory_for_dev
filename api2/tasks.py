from inventory.celery import app
from utils import SyncMenuStock
from depot.models import Organization
from cost.models import SyncHis

@app.task
def sync_menu_stock(org_id, is_retail, record, is_last_record=False):
    org = Organization.objects.get(pk=org_id)
    sync_instance = SyncMenuStock(org, is_retail)
    main_category, catepory_pos = sync_instance.update_main_category_pos(record)
    sub_category_pos = sync_instance.update_sub_category_pos(record, main_category, catepory_pos)
    sync_instance.update_menuitem(record, sub_category_pos, catepory_pos)

    if sync_instance.is_retail is True:
        sync_instance.rebuild_category()

    if is_last_record is True:
        sync_instance.del_category_proccessing()

@app.task
def delete_synchis(his_id):
    SyncHis.objects.get(pk=his_id).delete()
