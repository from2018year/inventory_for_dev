# -*- coding: utf-8 -*- 
from django import http
from django.utils.translation import check_for_language
from django.conf import settings
from inventory.settings import MEDIA_ROOT
from django.http import HttpResponse
import traceback
from django.utils import translation
try: 
    from PIL import ImageFile
except:
    import ImageFile

def set_language(request):
    """
    Redirect to a given url while setting the chosen language in the
    session or cookie. The url and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = http.HttpResponseRedirect(next)
    
    lang_code = request.REQUEST.get('language', None)

    if lang_code and check_for_language(lang_code):
        translation.activate(lang_code)
        if hasattr(request, 'session'):
            request.session['django_language'] = lang_code  
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
    return response


