from django.http import HttpResponse, HttpResponseRedirect 
from django.shortcuts import get_object_or_404, render_to_response

from django.contrib.gis.geos import GEOSGeometry, fromstr 
from django.contrib.gis.shortcuts import render_to_kml
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from fixcity.bmabr.models import Rack, Comment
from fixcity.bmabr.models import Neighborhoods
from fixcity.bmabr.models import CommunityBoard
from fixcity.bmabr.models import RackForm, CommentForm

from geopy import geocoders

def get_nearist(point): 
    close_racks = Rack.objects.filter(location__distance_lte=(point,D(km=.2)))
    return close_racks


def index(request):   
    communityboard_list = CommunityBoard.objects.all()      
    rack = Rack.objects.all()
    rack_extent = rack.extent()
    return render_to_response('index.html', {
            'communityboard_list' : communityboard_list,
            'rack_extent': rack_extent,
            })    


def assess(requests): 
    racks_query = Rack.objects.all()
    return render_to_response('assess.html', { 
            'rack_query': racks_query,
            }) 


def newrack_form(request):         
    address = request.GET['address']
    g = geocoders.Google()
    place, (lat, lng) = g.geocode(address)        
    point = Point((lng,lat))    
    close_racks = Rack.objects.filter(location__distance_lte=(point,D(km=.5)))
    form = RackForm()
    return render_to_response('newrack.html', { 
            'form': form,
            'address': place, 
            'lat': lat,
            'lng': lng,
            'close_racks': close_racks,
           })



def add_rack(request): 
    form = RackForm(request.POST,request.FILES)
    if form.is_valid(): 
        new_rack = form.save()
        return HttpResponseRedirect('/assess/')  
    else: 
        return HttpResponseRedirect('/error/rack') 

def rack(request,rack_id): 
    rack_query = Rack.objects.filter(id=rack_id)    
    comment_query = Comment.objects.filter(rack=rack_id)
    return render_to_response('rack.html', { 
            'rack_query': rack_query,            
            'comment_query': comment_query,
            })
    


def add_comment(request): 
    form = CommentForm(request.POST)
    rack_id = request.POST['rack']
    if form.is_valid(): 
        new_comment = form.save()
        return HttpResponseRedirect('/rack/%s#comments'% rack_id )   
    else: 
        return HttpResponseRedirect('/error/comment') 

        

def rack_all_kml(request): 
    racks = Rack.objects.all()
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_requested_kml(requst): 
    racks = Rack.objects.filter(status='r')
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 

def rack_json(requst): 
    racks = Rack.objects.filter(status='r').json()
    return HttpResponse(racks)



def rack_pendding_kml(request): 
    racks = Rack.objects.filter(status='a')
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_built_kml(request): 
    racks = Rack.objects.filter(status='a')
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_by_id_kml(request, rack_id): 
    racks = Rack.objects.filter(id=rack_id)
    return render_to_kml("placemarkers.kml",{'racks':racks})

'''
def rack_by_id_json(request, rack_id): 
    racks = Rack.objects.filter(id=rack_id)
    
'''    


def neighborhoods(request): 
    neighborhood_list = Neighborhoods.objects.all()
    return render_to_response('neighborhoods.html', {'neighborhood_list': neighborhood_list})


def communityboard(request): 
    communityboard_list = CommunityBoard.objects.all()      
    return render_to_response('communityboard.html', { 
            "communityboard_list": communityboard_list  
            }
           )

