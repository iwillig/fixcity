import os
import sys
import site

# Some libraries (eg. geopy) have an annoying habit of printing to stdout,
# which is a no-no under mod_wsgi.
# Workaround as per http://code.google.com/p/modwsgi/wiki/ApplicationIssues
sys.stdout = sys.stderr

# This may need to be adjusted based on your installation path.
env_root = os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', '..')
env_root = os.path.abspath(env_root)

sitepackages_root = os.path.join(env_root, 'lib')
for d in os.listdir(sitepackages_root):
    if d.startswith('python'):
      
        site.addsitedir(
         os.path.join(sitepackages_root, d, 'site-packages'))
        break
else:
    raise RuntimeError("Could not find any site-packages to add in %r" % env_root)

os.environ['DJANGO_SETTINGS_MODULE'] = 'fixcity.settings'
os.environ['PYTHON_EGG_CACHE'] = '/tmp/fixcity-python-eggs'

import django.core.handlers.wsgi
from wsgilog import WsgiLog

application = django.core.handlers.wsgi.WSGIHandler()

# Log uncaught exceptions to stderr via WSGI middleware.
#
# This isn't usually necessary: when settings.DEBUG is true, the
# default behavior is to dump errors to stdout and show them nicely in
# the browser; when settings.DEBUG is false, our custom 500 error view
# takes care of logging. But if for any reason *that* view blows up,
# we fall back to this.  (I wouldn't have bothered except I figured
# out how to get this working before I hooked up logging in that
# view.)

application = WsgiLog(application, tohtml=False, tofile=False,
                      tostream=True, toprint=False)
