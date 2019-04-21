# -*- coding: utf-8 -*- 
from django.utils.translation import ugettext_lazy as _
import platform

OS_TYPE=platform.system().upper()

INVOICE_CODE_TEMPLATE="T_%(date)s_%(seq)10s"
INVOICE_BATCH_TEMPLATE="P_%(date)s_%(seq)10s"
CONSUME_PRICE=True  #领用时是否看到进货价格

INVOICE_STATUS=(
    (10,_(u'全部')),
    (0,_(u'草稿')),
    (1,_(u'申请中')),
    (2,_(u'已审核')),
)

INVOICE_TYPES=[
    (1000,_(u'初始入库')),
    (1001,_(u'采购入库')),
    #(1002,_(u'退料入库单据')),
    #(1009,_(u'调拨入库单据')),
    (1004,_(u'采购申请')),
    
    (2000,_(u'采购退货')),
    (2001,_(u'领用出库')),
    (2002,_(u'销售出库')),
    #(2009,_(u'调拨出库单据')),
    (9000,_(u'盘盈单')),
    (9001,_(u'盘亏单')),
    #(9999,_(u'盘盈盘亏')),
    #(10000,_(u'库位调拨单据')),
    
]

PAY_INVOICE_TYPES=[
    (3000,_(u'付款')),
    (3001,_(u'收款')),
]

IN_BASE_TYPE=[1000,1001,1009,9000,9999]
IN_BASE_TYPE_STR="1000,1001,1009,9999"

BILL_TYPES=(
    (1,_(u'入库单')),
    (2,_(u'出库单')),
)

BILL_UNITS=(
    (1,_(u'单位1')),
    (2,_(u'单位2')),
)

GOOD_STANDARDS=(
    (1,_(u'规格1')),
    (2,_(u'规格2')),
)

GOOD_UNITS=(
    (1,_(u'单位1')),
    (2,_(u'单位2')),
)

CUSTOMER_TYPE=(
    (1,_(u'供货商')),
    (2,_(u'客户')),
)

DATE_UNIT_TYPES=(
    (1,_(u'天')),
    (2,_(u'周')),
    (3,_(u'月')),
    (4,_(u'年')),
)

IN_INVOICE_TYPES=(
    (1,_(u'采购入库')),
    (2,_(u'退料入库')),
    #(3,_(u'其他入库')),
    (4,_(u'盘盈入库')),
    (5,_(u'调拨单据')),
    (6,_(u'合并单据')),
    
)

OUT_INVOICE_TYPES=(
    (1,_(u'销售出库')),
    (2,_(u'领用出库')),
    (3,_(u'采购退货')),
    (4,_(u'报损出库')),
    #(5,_(u'其他出库')),
    (6,_(u'盘亏出库')),
    (7,_(u'调拨单据')),
    (8,_(u'合并单据')),
    
)



SEX=(
    (1,_(u"男")),
    (0,_(u"女")),
)

ORGS_TYPE=(
    (1,_(u'直营')),
    (2,_(u'加盟')),
)

ORGS_TYPE_SELECT=(
    (0,_(u'全部')),
    (1,_(u'直营')),
    (2,_(u'加盟')),
)

INDUSTRY=(
    (1,_(u'餐饮行业')),
    (2,_(u'酒店行业')),
    (3,_(u'服装行业')),
    (4,_(u'零售行业')),
)

BIRTH_TYPES=(
    (0,_(u'公历')),
    (1,_(u'农历')),
)

NATIONS=(
    (1,_(u'汉族')),
    (2,_(u'壮族')),
    (3,_(u'苗族')),
    (4,_(u'回族')),
    (5,_(u'瑶族')),
    (6,_(u'满族')),
    (7,_(u'仫佬族')),
    (8,_(u'侗族')),
    (9,_(u'维吾尔族')),
    (10,_(u'土家族')),
    (11,_(u'彝族')),
    (12,_(u'蒙古族')),
    (13,_(u'藏族')),
    (14,_(u'布依族')),
    (15,_(u'朝鲜族')),
    (16,_(u'白族')),
    (17,_(u'哈尼族')),
    (18,_(u'哈萨克族')),
    (19,_(u'黎族')),
    (20,_(u'傣族')),
    (21,_(u'畲族')),
    (22,_(u'傈僳族')),
    (23,_(u'仡佬族')),
    (24,_(u'东乡族')),
    (25,_(u'拉祜族')),
    (26,_(u'水族')),
    (27,_(u'佤族')),
    (28,_(u'纳西族')),
    (29,_(u'羌族')),
    (30,_(u'土族')),
    (31,_(u'锡伯族')),
    (32,_(u'柯尔克孜族')),
    (33,_(u'达斡尔族')),
    (34,_(u'景颇族')),
    (35,_(u'毛南族')),
    (36,_(u'撒拉族')),
    (37,_(u'布朗族')),
    (38,_(u'塔吉克族')),
    (39,_(u'阿昌族')),
    (40,_(u'普米族')),
    (41,_(u'鄂温克族')),
    (42,_(u'怒族')),
    (43,_(u'京族')),
    (44,_(u'基诺族')),
    (45,_(u'德昂族')),
    (46,_(u'保安族')),
    (47,_(u'俄罗斯族')),
    (48,_(u'裕固族')),
    (49,_(u'乌孜别克族')),
    (50,_(u'门巴族')),
    (51,_(u'鄂伦春族')),
    (52,_(u'独龙族')),
    (53,_(u'塔塔尔族')),
    (54,_(u'赫哲族')),
    (55,_(u'高山族')),
    (56,_(u'珞巴族')),
    (100,_(u"其他")),
)

CREDENTIAL_TYPES=(
    (1,_(u'身份证')),
    (2,_(u'驾驶证')),
)

MOLING_RULES=(
    (0,_(u'不抹零')),
    (1,_(u'小数抹零')),
    (2,_(u'个位抹零')),
    (3,_(u'十位抹零')),
    
    (5,_(u'个位四舍五入')),
    (6,_(u'小数四舍五入')),
    (7,_(u'分位四舍五入')),
    
    (4,_(u'个位二八舍入，三七作五')),
    (8,_(u'分位二八舍入，三七作五')),
)

CARD_STATUSES=(
    (0,_(u'未激活')),
    (1,_(u'正常')),
    (2,_(u'挂失')),
    (3,_(u'锁定')),
    (4,_(u'已过期')),
)

CREDIT_LEVELS=(
    (1,_(u'不好')),
    (2,_(u'一般')),
    (3,_(u'很好')),
)

PASSWORD_CHARS=['1','2','3','4','5','6','7','8','9','0',
                'a','b','c','d','e','f','g','h','i','g','k','l','m',
                'n','o','p','q','r','s','t','u','v','w','x','y','z']

TIME_SPAN=(
    (1,_(u'天')),
    (2,_(u'周')),
    (3,_(u'月')),
    (4,_(u'年')),
)

GOODS_STATUS=(
    (1,_(u'正常')),
    (0,_(u'下架')),
)



CREATE_SQL={
    'menu_item':
    '''
    CREATE TABLE `menu_item` (
  `item_id` int(11) NOT NULL,
  `item_name1` varchar(60) DEFAULT NULL,
  `item_name2` varchar(60) DEFAULT NULL,
  `icon` varchar(512) DEFAULT NULL,
  `slu_id` int(11) DEFAULT NULL,
  `nlu` varchar(20) DEFAULT NULL,
  `class_id` int(11) DEFAULT NULL,
  `print_class` int(11) DEFAULT NULL,
  `item_type` int(11) DEFAULT '0',
  `allow_condiment` int(11) DEFAULT NULL,
  `required_condiment` int(11) DEFAULT '0',
  `check_availability` bit(1) DEFAULT NULL,
  `no_access_mgr` bit(1) DEFAULT NULL,
  `major_group` int(11) DEFAULT NULL,
  `family_group` int(11) DEFAULT NULL,
  `price_1` float DEFAULT '0',
  `cost_1` float DEFAULT '0',
  `unit_1` varchar(30) DEFAULT '',
  `date_from_1` date DEFAULT NULL,
  `date_to_1` date DEFAULT NULL,
  `surcharge_1` float DEFAULT '0',
  `tare_weight_1` float DEFAULT '0',
  `price_2` float DEFAULT '0',
  `cost_2` float DEFAULT '0',
  `unit_2` varchar(30) DEFAULT '',
  `date_from_2` date DEFAULT NULL,
  `date_to_2` date DEFAULT NULL,
  `surcharge_2` float DEFAULT '0',
  `tare_weight_2` float DEFAULT '0',
  `price_3` float DEFAULT '0',
  `cost_3` float DEFAULT '0',
  `unit_3` varchar(30) DEFAULT '',
  `date_from_3` date DEFAULT NULL,
  `date_to_3` date DEFAULT NULL,
  `surcharge_3` float DEFAULT '0',
  `tare_weight_3` float DEFAULT '0',
  `price_4` float DEFAULT '0',
  `cost_4` float DEFAULT '0',
  `unit_4` varchar(30) DEFAULT '',
  `date_from_4` date DEFAULT NULL,
  `date_to_4` date DEFAULT NULL,
  `surcharge_4` float DEFAULT '0',
  `tare_weight_4` float DEFAULT '0',
  `price_5` float DEFAULT '0',
  `cost_5` float DEFAULT '0',
  `unit_5` varchar(30) DEFAULT '',
  `date_from_5` date DEFAULT NULL,
  `date_to_5` date DEFAULT NULL,
  `surcharge_5` float DEFAULT '0',
  `tare_weight_5` float DEFAULT NULL,
  `slu_priority` int(11) DEFAULT '0',
  `period_class_id` int(11) DEFAULT '0',
  `rvc_class_id` int(11) DEFAULT '0',
  `commission_type` int(11) DEFAULT '0',
  `commission_value` float DEFAULT '0',
  `ticket_class` int(11) DEFAULT '1',
  `tax_group` int(11) DEFAULT '-1',
  PRIMARY KEY (`item_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'descriptors_menu_item_slu':
    '''
    CREATE TABLE `descriptors_menu_item_slu` (
  `dmi_slu_id` int(11) NOT NULL,
  `dmi_slu_number` int(11) DEFAULT NULL,
  `dmi_slu_name` varchar(30) DEFAULT NULL,
  `touchscreen_style` int(11) DEFAULT NULL,
  `class_id` int(11) DEFAULT '-1',
  `print_class` int(11) DEFAULT '-1',
  `allow_condimentint` int(11) DEFAULT '-1',
  `required_condiment` int(11) DEFAULT '-1',
  `item_type` int(11) DEFAULT '0',
  `major_group` int(11) DEFAULT '-1',
  `family_group` int(11) DEFAULT '-1',
  `period_class_id` int(11) DEFAULT '-1',
  `rvc_class_id` int(11) DEFAULT '-1',
  `ticket_class` int(11) DEFAULT '1',
  `tax_group` int(11) DEFAULT '-1',
  `commission_type` int(11) DEFAULT '0',
  `commission_value` float DEFAULT '0',
  PRIMARY KEY (`dmi_slu_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'item_main_group':
    '''
    CREATE TABLE `item_main_group` (
  `main_group_id` int(11) NOT NULL,
  `main_group_name` varchar(30) DEFAULT NULL,
  `second_group_id` int(11) NOT NULL,
  PRIMARY KEY (`main_group_id`,`second_group_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
}

CREATE_EXTRA_SQL={
    'menu_item_handle':
    '''
    CREATE TABLE `menu_item_handle` (
  `item_id` int(11) NOT NULL,
  `item_name1` varchar(60) DEFAULT NULL,
  `item_name2` varchar(60) DEFAULT NULL,
  `icon` varchar(512) DEFAULT NULL,
  `slu_id` int(11) DEFAULT NULL,
  `nlu` varchar(20) DEFAULT NULL,
  `class_id` int(11) DEFAULT NULL,
  `print_class` int(11) DEFAULT NULL,
  `item_type` int(11) DEFAULT '0',
  `allow_condiment` int(11) DEFAULT NULL,
  `required_condiment` int(11) DEFAULT '0',
  `check_availability` bit(1) DEFAULT NULL,
  `no_access_mgr` bit(1) DEFAULT NULL,
  `major_group` int(11) DEFAULT NULL,
  `family_group` int(11) DEFAULT NULL,
  `price_1` float DEFAULT '0',
  `cost_1` float DEFAULT '0',
  `unit_1` varchar(30) DEFAULT '',
  `date_from_1` date DEFAULT NULL,
  `date_to_1` date DEFAULT NULL,
  `surcharge_1` float DEFAULT '0',
  `tare_weight_1` float DEFAULT '0',
  `price_2` float DEFAULT '0',
  `cost_2` float DEFAULT '0',
  `unit_2` varchar(30) DEFAULT '',
  `date_from_2` date DEFAULT NULL,
  `date_to_2` date DEFAULT NULL,
  `surcharge_2` float DEFAULT '0',
  `tare_weight_2` float DEFAULT '0',
  `price_3` float DEFAULT '0',
  `cost_3` float DEFAULT '0',
  `unit_3` varchar(30) DEFAULT '',
  `date_from_3` date DEFAULT NULL,
  `date_to_3` date DEFAULT NULL,
  `surcharge_3` float DEFAULT '0',
  `tare_weight_3` float DEFAULT '0',
  `price_4` float DEFAULT '0',
  `cost_4` float DEFAULT '0',
  `unit_4` varchar(30) DEFAULT '',
  `date_from_4` date DEFAULT NULL,
  `date_to_4` date DEFAULT NULL,
  `surcharge_4` float DEFAULT '0',
  `tare_weight_4` float DEFAULT '0',
  `price_5` float DEFAULT '0',
  `cost_5` float DEFAULT '0',
  `unit_5` varchar(30) DEFAULT '',
  `date_from_5` date DEFAULT NULL,
  `date_to_5` date DEFAULT NULL,
  `surcharge_5` float DEFAULT '0',
  `tare_weight_5` float DEFAULT NULL,
  `slu_priority` int(11) DEFAULT '0',
  `period_class_id` int(11) DEFAULT '0',
  `rvc_class_id` int(11) DEFAULT '0',
  `commission_type` int(11) DEFAULT '0',
  `commission_value` float DEFAULT '0',
  `ticket_class` int(11) DEFAULT '1',
  `tax_group` int(11) DEFAULT '-1',
  PRIMARY KEY (`item_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'descriptors_menu_item_slu_handle':
    '''
    CREATE TABLE `descriptors_menu_item_slu_handle` (
  `dmi_slu_id` int(11) NOT NULL,
  `dmi_slu_number` int(11) DEFAULT NULL,
  `dmi_slu_name` varchar(30) DEFAULT NULL,
  `touchscreen_style` int(11) DEFAULT NULL,
  `class_id` int(11) DEFAULT '-1',
  `print_class` int(11) DEFAULT '-1',
  `allow_condimentint` int(11) DEFAULT '-1',
  `required_condiment` int(11) DEFAULT '-1',
  `item_type` int(11) DEFAULT '0',
  `major_group` int(11) DEFAULT '-1',
  `family_group` int(11) DEFAULT '-1',
  `period_class_id` int(11) DEFAULT '-1',
  `rvc_class_id` int(11) DEFAULT '-1',
  `ticket_class` int(11) DEFAULT '1',
  `tax_group` int(11) DEFAULT '-1',
  `commission_type` int(11) DEFAULT '0',
  `commission_value` float DEFAULT '0',
  PRIMARY KEY (`dmi_slu_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'item_main_group_handle':
    '''
    CREATE TABLE `item_main_group_handle` (
  `main_group_id` int(11) NOT NULL,
  `main_group_name` varchar(30) DEFAULT NULL,
  `second_group_id` int(11) NOT NULL,
  PRIMARY KEY (`main_group_id`,`second_group_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'total_statistics':
    '''
    CREATE TABLE `total_statistics` (
  `total_checks` int(11) NOT NULL DEFAULT '0',
  `total_guests` int(11) NOT NULL DEFAULT '0',
  `install_date` datetime DEFAULT NULL,
  `db_version` varchar(10) DEFAULT NULL,
  `dayend_time` datetime DEFAULT NULL
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'history_order_head':
    '''
    CREATE TABLE `history_order_head` (
  `order_head_id` int(11) NOT NULL,
  `check_number` int(11) DEFAULT NULL,
  `rvc_center_id` int(11) DEFAULT NULL,
  `rvc_center_name` varchar(30) DEFAULT NULL,
  `table_id` int(11) DEFAULT NULL,
  `table_name` varchar(30) DEFAULT NULL,
  `check_id` int(11) NOT NULL DEFAULT '0',
  `open_employee_id` int(11) DEFAULT NULL,
  `open_employee_name` varchar(30) DEFAULT NULL,
  `customer_num` int(11) DEFAULT NULL,
  `customer_id` int(11) DEFAULT '0',
  `customer_name` varchar(30) DEFAULT NULL,
  `pos_device_id` int(11) DEFAULT NULL,
  `pos_name` varchar(30) DEFAULT NULL,
  `order_start_time` datetime DEFAULT NULL,
  `order_end_time` datetime DEFAULT NULL,
  `should_amount` float DEFAULT NULL,
  `return_amount` float DEFAULT NULL,
  `discount_amount` float DEFAULT NULL,
  `actual_amount` float DEFAULT NULL,
  `print_count` int(11) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `eat_type` int(11) DEFAULT NULL,
  `check_name` varchar(30) DEFAULT NULL,
  `original_amount` float DEFAULT '0',
  `service_amount` float DEFAULT '0',
  `edit_time` datetime DEFAULT NULL,
  `party_id` int(11) DEFAULT NULL,
  `edit_employee_name` varchar(30) DEFAULT NULL,
  `remark` varchar(50) DEFAULT NULL,
  `is_make` int(11) DEFAULT NULL,
  `delivery_info` varchar(100) DEFAULT NULL,
  `kds_show` int(11) DEFAULT '0',
  `kds_time` datetime DEFAULT NULL,
  KEY `idx_headcheck` (`order_head_id`,`check_id`) USING BTREE
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'history_order_detail':
    '''
    CREATE TABLE `history_order_detail` (
  `order_detail_id` int(11) NOT NULL,
  `order_head_id` int(11) DEFAULT NULL,
  `check_id` int(11) DEFAULT '1',
  `menu_item_id` int(11) DEFAULT '0',
  `menu_item_name` varchar(60) DEFAULT '',
  `product_price` float DEFAULT '0',
  `is_discount` bit(1) DEFAULT b'0',
  `original_price` float DEFAULT NULL,
  `discount_id` int(11) DEFAULT '0',
  `actual_price` float DEFAULT '0',
  `is_return_item` bit(1) DEFAULT b'0',
  `order_employee_id` int(11) DEFAULT '0',
  `order_employee_name` varchar(30) DEFAULT '',
  `pos_device_id` int(11) DEFAULT '0',
  `pos_name` varchar(30) DEFAULT '',
  `order_time` datetime DEFAULT NULL,
  `return_time` datetime DEFAULT NULL,
  `return_reason` varchar(200) DEFAULT '',
  `unit` varchar(30) DEFAULT '',
  `is_send` bit(1) DEFAULT b'0',
  `condiment_belong_item` int(11) DEFAULT '0',
  `quantity` float DEFAULT '0',
  `eat_type` int(11) DEFAULT '1',
  `auth_id` int(11) DEFAULT NULL,
  `auth_name` varchar(40) DEFAULT '',
  `weight_entry_required` bit(1) DEFAULT NULL,
  `description` char(100) DEFAULT NULL,
  `n_service_type` int(11) DEFAULT NULL,
  `not_print` int(11) DEFAULT NULL,
  `seat_num` int(11) DEFAULT NULL,
  `discount_price` float DEFAULT NULL,
  `sales_amount` float DEFAULT NULL,
  `is_make` int(11) DEFAULT NULL,
  KEY `idx_detailcheck` (`order_head_id`,`check_id`),
  KEY `idx_condiment` (`condiment_belong_item`),
  KEY `idx_detail` (`order_detail_id`)
) ENGINE=FEDERATED DEFAULT CHARSET=utf8
    '''
    ,
    'history_day_end':
    '''
    CREATE TABLE `history_day_end` (
  `history_day_end_id` int(11) NOT NULL AUTO_INCREMENT,
  `day` date NOT NULL,
  `rvc_center_id` int(11) NOT NULL,
  `period_id` int(11) NOT NULL,
  `eidt_time` datetime DEFAULT NULL,
  `sales_amount` decimal(11,2) DEFAULT NULL,
  `discount_amount` decimal(11,2) DEFAULT NULL,
  `service_amount` decimal(11,2) DEFAULT NULL,
  `return_amount` decimal(11,2) DEFAULT NULL,
  `should_amount` decimal(11,2) DEFAULT NULL,
  `actual_amount` decimal(11,2) DEFAULT NULL,
  `eatin_amount` decimal(11,2) DEFAULT NULL,
  `out_amount` decimal(11,2) DEFAULT NULL,
  `invoice_amount` decimal(11,2) DEFAULT NULL,
  `tax_amount` decimal(11,2) DEFAULT NULL,
  `customer_num` int(11) DEFAULT NULL,
  `chk_num` int(11) DEFAULT NULL,
  `table_num` int(11) DEFAULT NULL,
  PRIMARY KEY (`history_day_end_id`)
) ENGINE=FEDERATED AUTO_INCREMENT=17 DEFAULT CHARSET=utf8
    '''
}