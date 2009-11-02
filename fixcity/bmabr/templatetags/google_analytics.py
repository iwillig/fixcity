from django import template
register = template.Library()
from django.conf import settings


@register.simple_tag
def google_analytics():
    tmpl = template.loader.get_template('google_analytics.html')
    code = settings.GOOGLE_ANALYTICS_KEY.strip()
    if not code:
        return ''
    c = template.Context({
        'analytics_code': code,
        })
    return tmpl.render(c)
