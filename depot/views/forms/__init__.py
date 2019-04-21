# -*- coding: utf-8 -*- 
from django.forms.widgets import Select
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape, escape
from itertools import chain

class TreeSelect(Select):
    def __init__(self, attrs=None):
        super(Select, self).__init__(attrs)
        
    def render_option(self, selected_choices,obj, option_value, option_label):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return u'<option root_id="%s" value="%s"%s>%s</option>' % (
            obj and obj.get_root().pk or 0,
            escape(option_value), selected_html,
            conditional_escape('---'*(obj and obj.level or 0)+' '+force_unicode(option_label)).replace(' ', ' '))
            
    def render_options(self, choices, selected_choices):
        selected_choices = set(force_unicode(v) for v in selected_choices)
        
        q=list(self.choices.queryset)
        if self.choices.field.empty_label:
            q.insert(0,None)
            
        output = []
        for obj,(option_value, option_label) in zip(q,chain(self.choices, choices)):
            if isinstance(option_label, (list, tuple)):
                output.append(u'<optgroup label="%s">' % escape(force_unicode(option_value)).replace(' ', ' '))
                for option in option_label:
                    output.append(self.render_option(selected_choices, obj , *option))
                output.append(u'</optgroup>')
            else:
                output.append(self.render_option(selected_choices,obj, option_value, option_label))
        return u'\n'.join(output)
    
    
class GoodUnitSelect(Select):
        
    def render_option(self, selected_choices, option_value,option_rate, option_label):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return u'<option rate="%s" value="%s"%s>%s</option>' % (
            option_rate,
            escape(option_value), selected_html,
            conditional_escape(force_unicode(option_label)).replace(' ', ' '))
            
    def render_options(self, choices, selected_choices):
        selected_choices = set(force_unicode(v) for v in selected_choices)
            
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                output.append(u'<optgroup label="%s">' % escape(force_unicode(option_value)).replace(' ', ' '))
                for option in option_label:
                    output.append(self.render_option(selected_choices , *option))
                output.append(u'</optgroup>')
            else:
                if isinstance(option_value, (list, tuple)):
                    output.append(self.render_option(selected_choices, option_value[0],option_value[1], option_label))
                else:
                    output.append(self.render_option(selected_choices, option_value,option_value, option_label))
        return u'\n'.join(output)