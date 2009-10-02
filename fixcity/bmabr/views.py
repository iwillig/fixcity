# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core import serializers
from django.core.files.uploadhandler import FileUploadHandler
from django.core.paginator import Paginator, InvalidPage, EmptyPage

from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.http import base36_to_int

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import fromstr
from django.contrib.gis.shortcuts import render_to_kml

from fixcity.bmabr.models import Rack, Comment, Steps
from fixcity.bmabr.models import Neighborhoods
from fixcity.bmabr.models import CommunityBoard
from fixcity.bmabr.models import RackForm, CommentForm, SupportForm
from fixcity.bmabr.models import StatementOfSupport

from geopy import geocoders

from django.utils import simplejson as json
from django.conf import settings

import logging
import sys
import traceback

cb_metric = 50.00 
GKEY="ABQIAAAApLR-B_RMiEN2UBRoEWYPlhTmTlZhMVUZVOGFgSe6Omf4DswcaBSLmUPer5a9LF8EEWHK6IrMgA62bg"
g = geocoders.Google(GKEY)
SRID=4326


def flash(astring, request):
    """add a string to the session's flash store"""
    request.session.setdefault('_flash', []).append(astring)
    request.session.modified = True

def iter_flash_messages(request):
    """yield all the session's flash messages, and remove them from
    the session. LIFO."""
    flash_messages = request.session.get('_flash', [])
    while flash_messages:
        request.session.modified = True
        yield flash_messages.pop()


def user_context(request):
    # Complicated a bit because AnonymousUser doesn't have some attributes.
    user = request.user
    first = getattr(user, 'first_name', '')
    last = getattr(user, 'last_name', '')
    email = getattr(user, 'email', '')
    if first and last:
        displayname = u'%s %s' % (first, last)
    else:
        displayname = first or last or user.username
    return {
        'request': request, 
        'user': request.user,
        'user_displayname': displayname,
        'user_email': email,
        'flash_messages': iter_flash_messages(request),
    }

def index(request):
    racks_query = Rack.objects.order_by('-date', '-id')[:13]
    return render_to_response('index.html',
       {'request':request,
        'recent_racks': racks_query,
        },
       context_instance=RequestContext(request, processors=[user_context])
                              ) 
def about(request):
    return render_to_response('about.html',
       {'request':request},
       context_instance=RequestContext(request, processors=[user_context])
                              )

def faq(request):
    return render_to_response('faq.html',
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
    results = g.geocode(location, exactly_one=False)
    response = HttpResponse(content_type='application/json')
    response.write(json.dumps([x for x in results]))
    return response

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



def verify(request): 
    racks_query = Rack.objects.order_by('-date', '-id')
    paginator = Paginator(racks_query, 5)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    # If page request (9999) is out of range, deliver last page of results.
    try:
        racks_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        racks_page = paginator.page(paginator.num_pages)

    # Pagination link clustering logic. Tried doing this purely in the
    # template, it was hideous.  The goal is to have page links like
    # (when eg. viewing page 7): '1 ... 5 6 7 8 9 ... 18' with a
    # cluster in the middle.    
    # It's a bit easier if we just generate a list of page numbers that
    # the UI should show, and have the template only deal with markup.
    page_numbers = []
    pagination_cluster_size = 5
    if paginator.num_pages <= pagination_cluster_size + 2:
        # There's not enough pages to need clustering.
        page_numbers = range(1, paginator.num_pages + 1)
    else:
        page_numbers.append(1)
        cluster_start = max(2,
                            racks_page.number - (pagination_cluster_size / 2))
        cluster_start = min(cluster_start,
                            paginator.num_pages - pagination_cluster_size)
        cluster_end = min(cluster_start + pagination_cluster_size,
                          paginator.num_pages)
        middle_cluster = range(cluster_start, cluster_end)
        if middle_cluster[0] > 2:
            # There's a gap here.
            page_numbers.append('...')
        page_numbers.extend(middle_cluster)
        if middle_cluster[-1] < (paginator.num_pages - 1):
            # There's a gap here.
            page_numbers.append('...')
        page_numbers.append(paginator.num_pages)
    if page_numbers == [1]:
        page_numbers = []
    return render_to_response('verify.html', { 
            'rack_query': racks_query,
            'racks_page': racks_page,
            'page_numbers': page_numbers,
            },
            context_instance=RequestContext(request, processors=[user_context])) 

def verify_by_communityboard(request,cb_id): 
    rack_query = Rack.objects.filter(communityboard=cb_id)    
    return render_to_response('verify_communityboard.html', { 
            'rack_query':rack_query
            },
            context_instance=RequestContext(request, processors=[user_context]))

def _maybe_geocode(request):
    """Handle an edge case where the address is the last thing the
    user types before submitting, so the client-side geocoding
    function never gets time to return."""
    if request.POST['geocoded'] != u'1':
        results = list(g.geocode(request.POST['address'], exactly_one=False))
        # XXX handle multiple (or zero) results.
        lat, lon = results[0][1]
        request.POST['location'] = u'POINT(%.9f %.9f)' % (lon, lat)

def newrack_form(request):
    if request.method == 'POST':
        _maybe_geocode(request)
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
            message = '''
            Thank you for your suggestion! Racks can take six months
            or more for the DOT to install, but we\'ll be in touch
            about its progress. <a href="/rack/new/">Add another
            rack</a> or continue to see other suggestions.
            '''
            flash(message, request)
            return HttpResponseRedirect('/verify/')
        else:
            flash('Please correct the following errors.', request)
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
        _maybe_geocode(request)
        form = RackForm(request.POST, request.FILES, instance=rack)
        if form.is_valid():
            form.save()
            flash('Your changes have been saved.', request)
            return HttpResponseRedirect('/rack/%s/edit' % rack.id)
        else:
            flash('Please correct the following errors.', request)
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


def contact(request):
    return render_to_response(
        'contact.html', {},
        context_instance=RequestContext(request, processors=[user_context]),
        )

def verification_kit(request):
    return render_to_response(
        'verification-kit.html',
        {},
        context_instance=RequestContext(request, processors=[user_context]),
        )

def activate(request, activation_key,
             template_name='registration/activate.html',
             extra_context=None):
    # Activate, then add this account to any Racks that were created
    # anonymously with this user's email address.  I would prefer to
    # simply wrap the registration.views.activate function from
    # django-registration, but I can't really do that because I can't
    # get at the activated user - it just returns rendered HTML. So,
    # I'm copy-pasting its code.

    context_instance = RequestContext(request)

    from registration.models import RegistrationProfile
    # -- Begin copy-pasted code from django-registration.
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    
    account = RegistrationProfile.objects.activate_user(activation_key)
    if extra_context is None:
        extra_context = {}
    for key, value in extra_context.items():
        context_instance[key] = callable(value) and value() or value
    # -- End copy-pasted code from django-registration.

    # Let the user know if activation failed, and why.
    context_instance['key_status'] = 'Activation failed. Double-check your URL'
    if account:
        context_instance['key_status'] = 'Activated'
    else:
        from registration.models import SHA1_RE
        if not SHA1_RE.search(activation_key):
            context_instance['key_status'] = ('Malformed activation key. '
                                              'Make sure you got the URL right!')
        else:
            reg_profile = RegistrationProfile.objects.filter(
                activation_key=activation_key)
            if reg_profile: 
                reg_profile = reg_profile[0]
                if reg_profile.activation_key_expired():
                    context_instance['key_status'] = 'Activation key expired'
            else:
                # Unfortunately it's impossible to be sure if the user already
                # activated, because activation causes the key to be reset.
                # We could do it if we knew who the user was at this point,
                # but we don't.
                context_instance['key_status'] = ('No such activation key.'
                                                  ' Maybe you already activated?')

    # Now see if we need to reset the password.
    token = request.REQUEST.get('token')
    context_instance['valid_reset_token'] = False
    if token:
        uidb36 = request.REQUEST['uidb36']
        # Copy-paste-and-hack code from django.contrib.auth.views, yay.
        try:
            uid_int = base36_to_int(uidb36)
        except ValueError:
            raise Http404
        user = get_object_or_404(User, id=uid_int)
        context_instance['token'] = token
        context_instance['uidb36'] = uidb36
        context_instance['username'] = user.username
        if token_generator.check_token(user, token):
            context_instance['valid_reset_token'] = True
            if request.method == 'POST':
                form = SetPasswordForm(user, request.POST)
                if form.is_valid():
                    form.save()
                    flash('Password changed.', request)
                    from django.contrib.auth import login, authenticate
                    user = authenticate(username=user.username,
                                        password=request.POST['new_password1'])
                    if user:
                        login(request, user)
                        return HttpResponseRedirect('/')

    # Post-activation: Modify anonymous racks.
    context_instance['activation_key'] = activation_key
    if account:
        for rack in Rack.objects.filter(email=account.email, user=u''):
            rack.user = account.username
            rack.save()

    return render_to_response(template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS },
                              context_instance=context_instance)


class QuotaExceededError(Exception):
    pass

class QuotaUploadHandler(FileUploadHandler):
    """
    This upload handler terminates the connection if a file larger than
    the specified quota is uploaded.
    """

    QUOTA_MB = 5  # Should be a setting in settings.py?
    QUOTA =  QUOTA_MB * 1024 * 1024

    def __init__(self, request=None):
        super(QuotaUploadHandler, self).__init__(request)
        self.total_upload = 0
    
    def receive_data_chunk(self, raw_data, start):
        self.total_upload += len(raw_data)
        if self.total_upload >= self.QUOTA:
            raise QuotaExceededError('Maximum upload size is %.2f MB'
                                     % self.QUOTA_MB)
        # Delegate to the next handler.
        return raw_data
            
    def file_complete(self, file_size):
        return None

def server_error(request, template_name='500.html'):
    """
    500 error handler.
    This ONLY gets used if settings.DEBUG==False.

    Templates: `500.html`
    Context: None
    """
    info = sys.exc_info()
    exc_type = info[1].__class__.__name__
    exc_value = str(info[1])
    logger = logging.getLogger('')
    logger.error('at %r:' % request.build_absolute_uri())
    # This is fairly ugly in the apache error log, as each line gets
    # its own log entry, but hey it's way better than nothing.
    logger.error(traceback.format_exc())
    return render_to_response(
        template_name,
        {'exc_type': exc_type, 
         'exc_value': exc_value,
         },
        context_instance = RequestContext(request)
    )
