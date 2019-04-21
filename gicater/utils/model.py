# -*- coding: utf-8 -*- 
import contextlib
from copy import deepcopy
from django.db.models.expressions import ExpressionNode, F
from django.db.models.fields.files import FileField
from django.db.models.query import QuerySet
from django.db import models, transaction
import operator


def get_object_or_none(cls, *args, **kwargs):
    """
    Works like get_object_or_404() except it returns None instead
    of raising Http404 exception.
    """
    def _get_queryset(cls):
        if isinstance(cls, QuerySet):
            return cls
        if isinstance(cls, models.Manager):
            manager = cls
        else:
            manager = cls._default_manager

        return manager.all()

    qs = _get_queryset(cls).filter(*args, **kwargs)[:1]
    return next(iter(qs), None)


def get_field(model, name):
    """
    Returns model's field with given name.
    """
    return model._meta.get_field(name)


def get_form_field(model, name, **kwargs):
    """
    Returns form field for given model field with ability to override some params.

    Example:

        class UserForm(forms.Form):
            email = get_form_field(User, 'email', required=True)

    """
    return get_field(model, name).formfield(**kwargs)


EXPRESSION_NODE_CALLBACKS = {
    ExpressionNode.ADD: operator.add,
    ExpressionNode.SUB: operator.sub,
    ExpressionNode.MUL: operator.mul,
    ExpressionNode.DIV: operator.div,
    ExpressionNode.MOD: operator.mod,
}

if all([hasattr(ExpressionNode, a) for a in ('AND', 'OR')]):
    EXPRESSION_NODE_CALLBACKS = dict(EXPRESSION_NODE_CALLBACKS, **{
        ExpressionNode.AND: operator.and_,
        ExpressionNode.OR: operator.or_,
    })


class CannotResolve(Exception):
    pass

def _resolve(instance, node):
    if isinstance(node, F):
        return getattr(instance, node.name)
    elif isinstance(node, ExpressionNode):
        return _resolve(instance, node)
    return node

def resolve_expression_node(instance, node):
    op = EXPRESSION_NODE_CALLBACKS.get(node.connector, None)
    if not op:
        raise CannotResolve
    runner = _resolve(instance, node.children[0])
    for n in node.children[1:]:
        runner = op(runner, _resolve(instance, n))
    return runner

def update_model(instance, **kwargs):
    """
    Atomically update instance, setting field/value pairs from kwargs.
            这个update方法主要是实现了原子级别的update。用法很简单，把你需要修改的字段和内容作为**kwargs传进去调用即可。这样就避免了使用save时产生的一些不必要的修改。eg:
    update(user, age=age)
    """
    # fields that use auto_now=True should be updated corrected, too!
    for field in instance._meta.fields:
        if hasattr(field, 'auto_now') and field.auto_now and field.name not in kwargs:
            kwargs[field.name] = field.pre_save(instance, False)
        if field.name in kwargs and isinstance(field, FileField):
            setattr(instance, field.name, kwargs[field.name])
            kwargs[field.name] = field.pre_save(instance, False) # commit files to storage

    rows_affected = instance.__class__._default_manager.filter(pk=instance.pk).update(**kwargs)

    # apply the updated args to the instance to mimic the change
    # note that these might slightly differ from the true database values
    # as the DB could have been updated by another thread. callers should
    # retrieve a new copy of the object if up-to-date values are required
    for k,v in kwargs.iteritems():
        if isinstance(v, ExpressionNode):
            v = resolve_expression_node(instance, v)
        setattr(instance, k, v)

    # If you use an ORM cache, make sure to invalidate the instance!
    #cache.set(djangocache.get_cache_key(instance=instance), None, 5)
    return rows_affected

def reload_model(instance):
    """
    Reloads model instance (passed instance gets updated with new data).
    """
    model = instance.__class__
    new_inst = model._default_manager.get(pk=instance.pk)
    dct = deepcopy(new_inst.__dict__)
    instance.__dict__ = dct
    return instance
