"""
Send email to all beta users, asking them to register.
Create inactive accounts for them.

TO USE:
$ ./manage.py shell
... then at the prompt, type this:

>>> from .scripts.beta_email_registration import register_all
>>> register_all()

"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.utils.http import int_to_base36
from fixcity.bmabr.models import Rack
from registration.forms import RegistrationForm
from registration.models import RegistrationProfile


register_email_prefix = """
Hi %(email)s, thanks for taking part in the %(domain)s beta test.
We'd like to invite you to create an account on %(domain)s.

Registering for an account will allow you to correct and update any
bike rack submitted by you or any other user. You will also be able to
see all pages on the site; we will soon be blocking anonymous access
to some pages.
"""

register_email_postfix = """
Thanks again, and we hope to see you on %(domain)s!

- The Open Planning Project
"""

register_email_txt = register_email_prefix + """
You can create an account with the name \"%(name)s\" just by following
this link within %(activation_days)d days:
http://%(domain)s/accounts/activate/%(key)s/?uidb36=%(uidb36)s&token=%(password_reset_token)s

Or, if you want a different username than \"%(name)s\", that's almost
as easy. You can follow this link, fill out the form, then check your
email again for further instructions:
http://%(domain)s/accounts/register?email=%(email)s
""" + register_email_postfix



register_email_name_taken_txt = register_email_prefix + """
Just follow this link, fill out the form, then check your email again
for further instructions:
http://%(domain)s/accounts/register?email=%(email)s
""" + register_email_postfix



def send_email(template, email_func=send_mail, **kw):
    subject = 'Thanks for taking part in the %(domain)s beta!' % kw
    body = template % kw
    email_func(subject, body, settings.DEFAULT_FROM_EMAIL, ['%(email)s' % kw],
               fail_silently=False)
    print "Registration invite sent to %(email)s" % kw

def randpass(length=16):
    import random
    import string
    chars = string.letters + string.digits + string.punctuation
    output = random.choice(string.letters)
    while len(output) < length:
        output += random.choice(chars)
    return output


def register_all():
    # Monkeypatch to temporarily prevent other code from sending mail.
    import django.core.mail
    orig_send_mail = django.core.mail.send_mail
    def no_send_mail(*args, **kw):
        pass
    # Make sure *our* code can send mail.
    send_email.func_defaults = (orig_send_mail,)
    try:
        django.core.mail.send_mail = no_send_mail
        _register_all()
    finally:
        # Un-monkey.
        django.core.mail.send_mail = orig_send_mail

def _register_all():    
    anon_racks = Rack.objects.filter(user=u'')
    addrs = set([rack.email.strip() for rack in anon_racks])
    names_seen = set()
    current_site = Site.objects.get(id=settings.SITE_ID)
    for email in addrs:
        name = email.split('@', 1)[0]
        name = name.replace('+', '_')  # XXX do more cleanup
        if name in names_seen:
            raise ValueError("Oh crap, already saw name %r" % name)
        names_seen.add(name)
        password = randpass()  # Just so we always have a non-empty password.
        data = {'username': name, 'email': email,
                'password1': password, 'password2': password,}
        template_args = {'name': name, 'email': email, 'domain': current_site.domain,
                         'password': password,
                         'activation_days': settings.ACCOUNT_ACTIVATION_DAYS,
                         }
        form = RegistrationForm(data=data)
        if form.is_valid():
            # Register an inactive account and get the key.
            template = register_email_txt
            user = form.save()
            reg_profile = RegistrationProfile.objects.filter(user=user)[0]
            template_args['key'] = reg_profile.activation_key
            # We also need to provide a way to set your password.
            template_args['password_reset_token'] = default_token_generator.make_token(user)
            template_args['uidb36'] = int_to_base36(user.id)
            #user.delete(); reg_profile.delete() #XXX remove this when everything works
        else:
            if form.errors.get('username', [''])[0].count(u'already taken'):
                # Send an email without the link to the predetermined username.
                template = register_email_name_taken_txt
            else:
                print "Problem with address %s:" % email
                import pprint
                pprint.pprint(form.errors)
                continue
        send_email(template, **template_args)

