"""
A one-time migration script to re-geocode all addresses,
since we weren't correctly doing it when users typed them in.

TO USE:
$ ./manage.py shell
... then at the prompt, type this:

>>> from .scripts.fix_rack_locations import fix
>>> fix()
"""
from fixcity.bmabr.views import g as geocoder
from fixcity.bmabr.models import Rack

def fix():
    for rack in Rack.objects.all():
        newloc = [x for x in geocoder.geocode(rack.address, exactly_one=False)]
        try:
            newloc = newloc[0]
        except IndexError:
            print "Got no results"
            print
            continue
        if newloc[1] != (rack.location.y, rack.location.x):
            rack.location = 'POINT(%f %f)' % (newloc[1][1], newloc[1][0])
            print "fixed", rack.title, rack.address, rack.location
            print
            rack.save()


