# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib import auth
from django.contrib.auth.forms import UserCreationForm
from django.template import Context
from django.core import serializers

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry, fromstr
from django.contrib.gis.shortcuts import render_to_kml
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from fixcity.bmabr.models import Rack, Comment, Steps
from fixcity.bmabr.models import Neighborhoods
from fixcity.bmabr.models import CommunityBoard
from fixcity.bmabr.models import RackForm, CommentForm, SupportForm
from fixcity.bmabr.models import StatementOfSupport

from django.contrib.gis.geos import fromstr
from django.contrib import auth

from django.contrib.auth.models import User 

#from reportlab.pdfgen import canvas 
from geopy import geocoders

cb_metric = 50.00 
GKEY="ABQIAAAApLR-B_RMiEN2UBRoEWYPlhTmTlZhMVUZVOGFgSe6Omf4DswcaBSLmUPer5a9LF8EEWHK6IrMgA62bg"
g = geocoders.Google(GKEY)
SRID=4326

def user_context(request):
    user = request.user
    first = getattr(user, 'first_name', None)
    last = getattr(user, 'last_name', None)
    if first and last:
        displayname = u'%s %s' % (user.first_name, user.last_name)
    else:
        displayname = first or last or user.username
    return {
        'request': request, 
        'user': request.user,
        'user_displayname': displayname,
    }

def index(request):
    return render_to_response('index.html',
       {'request':request},
       context_instance=RequestContext(request, processors=[user_context])
                              ) 
def about(request):
    return render_to_response('about.html',
       {'request':request},
       context_instance=RequestContext(request, processors=[user_context])
                              ) 

@login_required
def profile(request): 
    user = request.user
    racks = Rack.objects.filter(user=user.username)
    return render_to_response('profile.html',
       {'user': user,
       'racks': racks
        },
       context_instance=RequestContext(request, processors=[user_context])
                              ) 

    

def login(request): 
    next = request.GET.get('next')
    if request.method == 'POST': 
        username = request.POST.get('username')
        password = request.POST.get('password') 
        user = auth.authenticate(username=username,password=password)
        if user is not None and user.is_active: 
            auth.login(request, user)
            return HttpResponseRedirect(next)
        else: 
            return HttpResponseRedirect("/user/error/")
    else: 
        pass 
    return render_to_response('login.html', 
       context_instance=RequestContext(request, processors=[user_context])
                              )

def logout(request): 
    next = request.GET.get('next')
    auth.logout(request)
    return HttpResponseRedirect(next)


def built(request): 
    rack = Rack.objects.all()
    rack_extent = rack.extent()
    return render_to_response('built.html',{ 
            'rack_extent': rack_extent},
            context_instance=RequestContext(request, processors=[user_context])
            )


def get_communityboard(request):
    lat = request.POST['lat'] 
    lon = request.POST['lon'] 
    point = 'POINT(%s %s)' % (lon,lat)
    pnt = fromstr(point,srid=4326)
    cb = CommunityBoard.objects.get(the_geom__contains=pnt)  
    return HttpResponse(cb.gid)

def geocode(request): 
    location = request.POST['geocode_text']
    (place, point) = g.geocode(location)
    return HttpResponse(place, point)

def reverse_geocode(request): 
    lat = request.POST['lat'] 
    lon = request.POST['lon']
    point = (lat, lon)
    (new_place,new_point) = g.reverse(point)
    return HttpResponse(new_place)

def submit_all(request): 
    ''' 
    needs major re-working
    ''' 
    community_board_query = CommunityBoard.objects.filter() 
    return render_to_response('submit.html', {
            'community_board_query': community_board_query,
            })



def submit(request): 
    community_board_query = CommunityBoard.objects.filter(name='1')
    for communityboard in community_board_query:         
        racks_query = Rack.objects.filter(location__contained=communityboard.the_geom)
        racks_count = Rack.objects.filter(location__contained=communityboard.the_geom).count()
        cb_metric_percent = racks_count/cb_metric 
        cb_metric_percent = cb_metric_percent * 100 
        community_board_query_extent = community_board_query.extent()
    return render_to_response('submit.html', {
            'community_board_query': community_board_query,
            'cb_metric_percent':cb_metric_percent,
            'racks_query': racks_query,
            'racks_count': racks_count,
            'community_board_query_extent': community_board_query_extent,
            },
             context_instance=RequestContext(request, processors=[user_context])            
             )



def assess(request): 
    racks_query = Rack.objects.all()
    return render_to_response('assess.html', { 
            'rack_query': racks_query,
            },
            context_instance=RequestContext(request, processors=[user_context])) 

def assess_by_communityboard(request,cb_id): 
    rack_query = Rack.objects.filter(communityboard=cb_id)    
    return render_to_response('assess_communityboard.html', { 
            'rack_query':rack_query
            },
            context_instance=RequestContext(request, processors=[user_context]))


def newrack_form(request): 
    if request.method == 'POST':
        form = RackForm(request.POST,request.FILES)
        if form.is_valid(): 
            new_rack = form.save()
            # create steps status for new rack suggestion
            size_up = Steps(step_rack=new_rack,name="size-up",status="todo")
            size_up.save()
            photo_status = Steps(step_rack=new_rack,name="photo",status='todo')
            photo_status.save()
            statement = Steps(step_rack=new_rack,name="statement",status='todo')
            statement.save()
            return HttpResponseRedirect('/rack/%s' % new_rack.id)
    else:
        form = RackForm()
    return render_to_response('newrack.html', { 
            'form': form,
           },
           context_instance=RequestContext(request, processors=[user_context])) 



@login_required
def rack_status(request,rack_id):
    response = HttpResponse()
    response['Content-Type'] = "text/javascript"
    response.write(serializers.serialize('json', Steps.objects.filter(step_rack=rack_id)))    
    return response

@login_required
def change_status(request,rack_id): 
    id = request.POST['id']
    step = Steps.objects.get(id=id)
    if step.status == 'finished': 
        new_step = Steps(id=id,step_rack=step.step_rack,name=step.name,status='todo')
        new_step.save()
    else: 
        new_step = Steps(id=id,step_rack=step.step_rack,name=step.name,status='finished')
        new_step.save()
    return HttpResponse(step)



def support(request, rack_id): 
    """Add a statement of support."""
    if request.method == "POST":
        form_support = SupportForm(request.POST,request.FILES)
        if form_support.is_valid(): 
            new_support = form_support.save()
            return HttpResponseRedirect('/rack/%s' % rack_id)              
        else: 
            return HttpResponse('something went wrong')              
    else:         
        return HttpResponse('not allowed')  




    


@login_required
def rack_edit(request,rack_id):
    rack = Rack.objects.get(id=rack_id)
    if request.method == 'POST': 
        form = RackForm(request.POST,request.FILES)
        if form.is_valid(): 
            new_rack = form.save()
            return HttpResponseRedirect('/rack/%s' % rack.id)
    else: 
        form = RackForm()
    return render_to_response('update_rack.html', 
          {"rack": rack,
           "form": form },
          context_instance=RequestContext(request, processors=[user_context])) 

def rack(request,rack_id): 
    rack = Rack.objects.get(id=rack_id)    
    steps_query = Steps.objects.filter(step_rack=rack_id)
    comment_query = Comment.objects.filter(rack=rack_id)
    statement_query = StatementOfSupport.objects.filter(s_rack=rack_id)
    return render_to_response('rack.html', { 
            'rack': rack,            
            'comment_query': comment_query,
            'statement_query': statement_query,
            'steps_query': steps_query,
            },
             context_instance=RequestContext(request, processors=[user_context])) 
           
    

def add_comment(request): 
    form = CommentForm(request.POST)
    rack_id = request.POST['rack']
    if form.is_valid(): 
        new_comment = form.save()
        return HttpResponseRedirect('/rack/%s#comments'% rack_id )   
    else: 
        return HttpResponseRedirect('/error/comment') 


def updatephoto(request,rack_id): 
    rack_query = Rack.objects.get(id=rack_id) 
    rack_photo = request.FILES['photo']
    rack = Rack(id=rack_query.id,address=rack_query.address,title=rack_query.title,date=rack_query.date,description=rack_query.description,email=rack_query.email,communityboard=rack_query.communityboard,photo=rack_photo,status=rack_query.status,location=rack_query.location)
    rack.save()
    return HttpResponse(rack)

    
def rack_all_kml(request): 
    racks = Rack.objects.all()
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_requested_kml(requst): 
    racks = Rack.objects.all()
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 




def community_board_kml(request): 
    community_boards = CommunityBoard.objects.all()
    return render_to_kml("community_board.kml",{'community_boards': community_boards})
 

def community_board_kml_by_id(request,cb_id): 
    community_boards = CommunityBoard.objects.filter(gid=cb_id)
    return render_to_kml("community_board.kml",{'community_boards': community_boards})

def rack_pendding_kml(request): 
    racks = Rack.objects.filter(status='a')
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_built_kml(request): 
    racks = Rack.objects.filter(status='a')
    return render_to_kml("placemarkers.kml", {'racks' : racks}) 


def rack_by_id_kml(request, rack_id): 
    racks = Rack.objects.filter(id=rack_id)
    return render_to_kml("placemarkers.kml",{'racks':racks})


def neighborhoods(request): 
    neighborhood_list = Neighborhoods.objects.all()
    return render_to_response('neighborhoods.html', {'neighborhood_list': neighborhood_list})


def communityboard(request): 
    communityboard_list = CommunityBoard.objects.all()      
    return render_to_response('communityboard.html', { 
            "communityboard_list": communityboard_list  
            }
           )

