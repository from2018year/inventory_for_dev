from depot.models import Category, Unit, Goods
from cost.models import CategoryPos, MenuItem, MenuItemDetail
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import cgi
from inventory.common import get_abbreviation


def update_many(objects, fields=[], using="default"):
    """Update list of Django objects in one SQL query, optionally only
    overwrite the given fields (as names, e.g. fields=["foo"]).
    Objects must be of the same Django model. Note that save is not
    called and signals on the model are not raised."""
    if not objects:
        return

    import django.db.models
    from django.db import connections
    con = connections[using]

    names = fields
    meta = objects[0]._meta
    fields = [f for f in meta.fields if
              not isinstance(f, django.db.models.AutoField) and (not names or f.name in names)]

    if not fields:
        raise ValueError("No fields to update, field names are %s." % names)

    fields_with_pk = fields + [meta.pk]
    parameters = []
    for o in objects:
        parameters.append(tuple(f.get_db_prep_save(f.pre_save(o, True), connection=con) for f in fields_with_pk))

    table = meta.db_table
    assignments = ",".join(("%s=%%s" % con.ops.quote_name(f.column)) for f in fields)
    con.cursor().executemany(
        "update %s set %s where %s=%%s" % (table, assignments, con.ops.quote_name(meta.pk.column)),
        parameters)

class SyncMenuStock(object):
    def __init__(self, org, root_parent, is_retail=False):
        self.org = org
        self.is_retail = is_retail
        self.root_parent = Category.objects.get(org=org,parent__isnull=True)

    def update_main_category_pos(self, record):
        try:
            p = CategoryPos.objects.get(parent__isnull=True, org=self.org, slu_id=record['main_group_id'])
            p.processing = 0
            p.last_name = p.name = record['main_group_name']
            p.save()

        except ObjectDoesNotExist:
            p = CategoryPos.objects.create(parent=None, org=self.org, slu_id=record['main_group_id'],
                                           name=record['main_group_name'])
            p.save()
        except MultipleObjectsReturned:
            p = CategoryPos.objects.filter(parent=None, org=self.org, slu_id=record['main_group_id'],
                                           name=record['main_group_name'])[0]
            p.processing = 0
            p.save()
        if self.is_retail is True:
            catepory_pos, created = Category.objects.get_or_create(parent=self.root_parent, org=self.org,
                                                                   slu_id=record['main_group_id'],
                                                                   defaults={'name': record['main_group_name'],
                                                                             'slu_type': 2})
            if not created:
                catepory_pos.name = record['main_group_name']
                catepory_pos.save()
            return (p, catepory_pos)

        return (p, None)

    def update_sub_category_pos(self, record, main_category, catepory_pos=None):
        try:
            c = CategoryPos.objects.get(parent=main_category, org=self.org, slu_id=record['dmi_slu_id'])
            c.processing = 0
            c.last_name = c.name = record['dmi_slu_name']
            c.save()
        except ObjectDoesNotExist:
            c=CategoryPos.objects.create(parent=main_category,org=self.org,slu_id=record['dmi_slu_id'],name=record['dmi_slu_name'])
        except MultipleObjectsReturned:
            c = CategoryPos.objects.filter(parent=main_category, org=self.org, slu_id=record['dmi_slu_id'])[0]
            c.processing = 0
            c.last_name = c.name = record['dmi_slu_name']
            c.save()

        if self.is_retail is True:
            catepory_pos, created = Category.objects.get_or_create(parent=catepory_pos, org=self.org,
                                                                   slu_id=record['dmi_slu_id'],
                                                                   defaults={'name': record['dmi_slu_name'],
                                                                             'slu_type': 2})
            if not created:
                catepory_pos.name = record['dmi_slu_name']
                catepory_pos.save()
        return c

    def update_menuitem(self, record, sub_category_pos, catepory_pos=None):
        unit = record['unit'].encode("utf-8")
        try:
            # p=MenuItem.objects.filter(org=org,item_id=record['item_id'],unit=unit).order_by('-id')[0]
            p = MenuItem.objects.select_related().filter(org=self.org, item_id=record['item_id'], unit=unit).order_by('-id')[
                0]
            p.categoryPos = sub_category_pos
            p.item_name = cgi.escape(record['item_name'])
            p.unit = unit
            p.price = record['price']
            p.processing = 0
            p.nlu = record['nlu']
            p.save()
        except:
            p=MenuItem.objects.create(org=self.org,item_id=record['item_id'],categoryPos=sub_category_pos,item_name=record['item_name'],
            unit=record['unit'],price=record['price'],nlu=record['nlu'])

        if self.is_retail:
            _menuItem = p
            unit = None
            if _menuItem.unit:
                unit, created = Unit.objects.get_or_create(unit=_menuItem.unit, good__isnull=True, org=self.org)
            goods, created = Goods.objects.get_or_create(name=_menuItem.item_name, category=catepory_pos, org=self.org,
                                                         defaults={'unit': unit, 'abbreviation': get_abbreviation(
                                                             _menuItem.item_name), 'sale_price_ori': _menuItem.price,
                                                                   'sale_price': _menuItem.price,
                                                                   'last_modify_user': None})
            if not created and goods.unit != unit:
                goods.unit = unit
                goods.save()

            MenuItemDetail.objects.filter(org=self.org, menuItem=_menuItem, good=goods).delete()
            MenuItemDetail.objects.get_or_create(org=self.org, menuItem=_menuItem, good=goods, weight=1,
                                                     goods_unit=goods.unit)

            weight = 1
            good_unit = goods.unit
            standard_weight = goods.change_nums(weight, good_unit)

            _menuItem.cost = standard_weight * goods.refer_price
            _menuItem.profit = _menuItem.price - _menuItem.cost
            _menuItem.percent1 = _menuItem.cost and (_menuItem.price - _menuItem.cost) * 100.0 / _menuItem.cost or 0
            _menuItem.percent2 = _menuItem.price and (
                                                         _menuItem.price - _menuItem.cost) * 100.0 / _menuItem.price or 0
            _menuItem.sync_type = 1
            _menuItem.save()

    def rebuild_category(self):
        Category.objects.partial_rebuild(Category.objects.filter(org=self.org)[0].tree_id)

    def rebuild_category_pos(self):
        CategoryPos.objects.rebuild()

    def del_category_proccessing(self):
        CategoryPos.objects.filter(org=self.org,processing=1).delete()