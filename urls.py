from django.conf.urls.defaults import *

from fixcity.bmabr import views 
from django.conf import settings

from django.views.generic.create_update import update_object

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    (r'^$', 'fixcity.bmabr.views.index'),
    (r'^about/$', 'fixcity.bmabr.views.about'), 

    # Accounts URLs
    (r'^accounts/login/$','fixcity.bmabr.views.login'),
    (r'^accounts/logout/$','fixcity.bmabr.views.logout'),
    (r'^profile/$', 'fixcity.bmabr.views.profile'),

    

    (r'^geocode/$', 'fixcity.bmabr.views.geocode'),
    (r'^reverse/$', 'fixcity.bmabr.views.reverse_geocode'),
    (r'^getcommunityboard/$', 'fixcity.bmabr.views.get_communityboard'),

    (r'assess/$','fixcity.bmabr.views.assess'),
    (r'assess/communityboard/(?P<cb_id>\d+)/$', 'fixcity.bmabr.views.assess_by_communityboard'),
    (r'submit/all/$','fixcity.bmabr.views.submit_all'),
    (r'submit/$','fixcity.bmabr.views.submit'),

    (r'built/$','fixcity.bmabr.views.built'),   
    (r'^rack/(?P<rack_id>\d+)/$', 'fixcity.bmabr.views.rack'),
    (r'^rack/(?P<rack_id>\d+)/edit/$', 'fixcity.bmabr.views.rack_edit'),

    (r'^rack/(?P<rack_id>\d+)/status/$', 'fixcity.bmabr.views.rack_status'),
    (r'^rack/(?P<rack_id>\d+)/support/$', 'fixcity.bmabr.views.support'),


     # KML URLs

    (r'rack/all.kml$', 'fixcity.bmabr.views.rack_all_kml'),
    (r'rack/requested.kml$', 'fixcity.bmabr.views.rack_requested_kml'),
    (r'rack/pendding.kml$', 'fixcity.bmabr.views.rack_pendding_kml'),
    (r'rack/built.kml$', 'fixcity.bmabr.views.rack_pendding_kml'),
    (r'rack/(?P<rack_id>\d+).kml', 'fixcity.bmabr.views.rack_by_id_kml'),
    (r'communityboards.kml','fixcity.bmabr.views.community_board_kml'),
    (r'communityboard/(?P<cb_id>\d+).kml','fixcity.bmabr.views.community_board_kml_by_id'),

    # different views for adding infomation, rack, comments. 

    (r'^rack/new/$', 'fixcity.bmabr.views.newrack_form'), # view for rack request form. 
    (r'^comment/add/$', 'fixcity.bmabr.views.add_comment'), 
                       
    # different ways of viewing information                   

    (r'^neighborhoods/$', 'fixcity.bmabr.views.neighborhoods'), 
    (r'^communityboard/$', 'fixcity.bmabr.views.communityboard'),

                                                                                                                                                                                
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
      {'document_root': settings.STATIC_DOC_ROOT,'show_indexes': True}),                                        
                                                                              

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     (r'^admin/(.*)', admin.site.root),
)
