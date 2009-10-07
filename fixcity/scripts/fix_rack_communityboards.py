"""
A one-time migration script to fix up all the community boards,
since we hardcoded many of them to Brooklyn CB1.

TO USE:
$ ./manage.py shell
... then at the prompt, type this:

>>> from fixcity.scripts.fix_rack_communityboards import fix
>>> fix()
"""

from fixcity.bmabr.models import Rack, CommunityBoard
from fixcity.bmabr.views import _get_communityboard_id

def fix():
    for rack in Rack.objects.all():
        lon, lat = rack.location.x, rack.location.y
        cbid = _get_communityboard_id(lon, lat)
        cb = CommunityBoard.objects.filter(gid=cbid)
        assert len(cb) == 1
        cb = cb[0]
        if cb == rack.communityboard:
            print "OK", rack.title, rack.address, rack.communityboard
        else:
            rack.communityboard = cb
            rack.save()
            print "fixed", rack.title, rack.address, rack.communityboard
            print


