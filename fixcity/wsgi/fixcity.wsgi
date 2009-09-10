import os
import sys
import site

env_root = os.environ['BIKERACTION_PYTHONHOME']
sitepackages_root = os.path.join(env_root, 'lib')
for d in os.listdir(sitepackages_root):
    if d.startswith('python'):
        site.addsitedir(os.path.join(sitepackages_root, d))
        break
else:
    raise RuntimeError("Could not find any site-packages to add in %r"
                       % env_root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplevoter.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
