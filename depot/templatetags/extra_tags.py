# -*- coding: utf-8 -*- 
from django import template

register = template.Library()

@register.filter
def get(mapping, key):
    return mapping.get(key, '')


@register.filter
def division(value,div):
    return div and value/div or div

@register.filter
def good_name(value,index):
	try:
		result = value[int(index)].good.name
	except:
		result = ''
	return result

@register.filter
def good_abb(value,index):
	try:
		result = value[int(index)].good.abbreviation
	except:
		result = ''
	return result

@register.filter
def good_unit(value,index):
	try:
		result = value[int(index)].goods_unit
	except:
		result = ''
	return result

@register.filter
def good_weight(value,index):
	try:
		result = value[int(index)].weight
	except:
		result = ''
	return result