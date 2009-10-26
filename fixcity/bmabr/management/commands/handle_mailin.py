# based on email2trac.py, which is Copyright (C) 2002 under the GPL v2 or later
"""
How to use
----------
 * See https://subtrac.sara.nl/oss/email2trac/

 * Create an config file:
    [DEFAULT]                        # REQUIRED
    project      : /data/trac/test   # REQUIRED
    debug        : 1                 # OPTIONAL, if set print some DEBUG info
    trac_version : 0.9               # OPTIONAL, default is 0.11

    [jouvin]                         # OPTIONAL project declaration, if set both fields necessary
    project      : /data/trac/jouvin # use -p|--project jouvin.

 * default config file is : /etc/email2trac.conf

 * Commandline opions:
                -h,--help
                -f,--file  <configuration file>
                -n,--dry-run
                -p, --project <project name>
                -t, --ticket_prefix <name>

"""
import os
import sys
import string
import stat
import time
#import email
import email.Header
import re
import urllib
import unicodedata
#from stat import *
from stat import S_IRWXU, S_IRWXG, S_IRWXO
import mimetypes
import traceback


# Will fail where unavailable, e.g. Windows
#
try:
    import syslog
    SYSLOG_AVAILABLE = True
except ImportError:
    SYSLOG_AVAILABLE = False

from datetime import tzinfo, timedelta, datetime
from trac import config as trac_config

# Some global variables
#
trac_default_version = '0.11'
m = None

# A UTC class needed for trac version 0.11, added by
# tbaschak at ktc dot mb dot ca
#
class UTC(tzinfo):
    """UTC"""
    ZERO = timedelta(0)
    HOUR = timedelta(hours=1)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO


class TicketEmailParser(object):
    env = None
    comment = '> '

    def __init__(self, env, parameters, version):
        self.env = env

        # Database connection
        #
        self.db = None

        # Save parameters
        #
        self.parameters = parameters

        # Some useful mail constants
        #
        self.author = None
        self.email_addr = None
        self.email_from = None
        self.id = None

        self.VERSION = version
        self.DRY_RUN = parameters['dry_run']

        self.get_config = self.env.config.get

        if parameters.has_key('umask'):
            os.umask(int(parameters['umask'], 8))

        if parameters.has_key('quote_attachment_filenames'):
            self.QUOTE_ATTACHMENT_FILENAMES = int(parameters['quote_attachment_filenames'])
        else:
            self.QUOTE_ATTACHMENT_FILENAMES = 1

        if parameters.has_key('debug'):
            self.DEBUG = int(parameters['debug'])
        else:
            self.DEBUG = 0

        if parameters.has_key('mailto_link'):
            self.MAILTO = int(parameters['mailto_link'])
            if parameters.has_key('mailto_cc'):
                self.MAILTO_CC = parameters['mailto_cc']
            else:
                self.MAILTO_CC = ''
        else:
            self.MAILTO = 0

        if parameters.has_key('spam_level'):
            self.SPAM_LEVEL = int(parameters['spam_level'])
        else:
            self.SPAM_LEVEL = 0

        if parameters.has_key('spam_header'):
            self.SPAM_HEADER = parameters['spam_header']
        else:
            self.SPAM_HEADER = 'X-Spam-Score'

        if parameters.has_key('email_quote'):
            self.EMAIL_QUOTE = str(parameters['email_quote'])
        else:
            self.EMAIL_QUOTE = '> '

        if parameters.has_key('email_header'):
            self.EMAIL_HEADER = int(parameters['email_header'])
        else:
            self.EMAIL_HEADER = 0

        if parameters.has_key('alternate_notify_template'):
            self.notify_template = str(parameters['alternate_notify_template'])
        else:
            self.notify_template = None

        if parameters.has_key('alternate_notify_template_update'):
            self.notify_template_update = str(parameters['alternate_notify_template_update'])
        else:
            self.notify_template_update = None

        if parameters.has_key('reply_all'):
            self.REPLY_ALL = int(parameters['reply_all'])
        else:
            self.REPLY_ALL = 0

        if parameters.has_key('ticket_update'):
            self.TICKET_UPDATE = int(parameters['ticket_update'])
        else:
            self.TICKET_UPDATE = 0

        if parameters.has_key('drop_spam'):
            self.DROP_SPAM = int(parameters['drop_spam'])
        else:
            self.DROP_SPAM = 0

        if parameters.has_key('verbatim_format'):
            self.VERBATIM_FORMAT = int(parameters['verbatim_format'])
        else:
            self.VERBATIM_FORMAT = 1

        if parameters.has_key('reflow'):
            self.REFLOW = int(parameters['reflow'])
        else:
            self.REFLOW = 1

        if parameters.has_key('drop_alternative_html_version'):
            self.DROP_ALTERNATIVE_HTML_VERSION = int(parameters['drop_alternative_html_version'])
        else:
            self.DROP_ALTERNATIVE_HTML_VERSION = 0

        if parameters.has_key('strip_signature'):
            self.STRIP_SIGNATURE = int(parameters['strip_signature'])
        else:
            self.STRIP_SIGNATURE = 0

        if parameters.has_key('strip_quotes'):
            self.STRIP_QUOTES = int(parameters['strip_quotes'])
        else:
            self.STRIP_QUOTES = 0

        if parameters.has_key('use_textwrap'):
            self.USE_TEXTWRAP = int(parameters['use_textwrap'])
        else:
            self.USE_TEXTWRAP = 0

        if parameters.has_key('binhex'):
            self.BINHEX = parameters['binhex']
        else:
            self.BINHEX = 'warn'

        if parameters.has_key('applesingle'):
            self.APPLESINGLE = parameters['applesingle']
        else:
            self.APPLESINGLE = 'warn'

        if parameters.has_key('appledouble'):
            self.APPLEDOUBLE = parameters['appledouble']
        else:
            self.APPLEDOUBLE = 'warn'

        if parameters.has_key('python_egg_cache'):
            self.python_egg_cache = str(parameters['python_egg_cache'])
            os.environ['PYTHON_EGG_CACHE'] = self.python_egg_cache

        self.WORKFLOW = None
        if parameters.has_key('workflow'):
            self.WORKFLOW = parameters['workflow']

        # Use OS independend functions
        #
        self.TMPDIR = os.path.normcase('/tmp')
        if parameters.has_key('tmpdir'):
            self.TMPDIR = os.path.normcase(str(parameters['tmpdir']))

        if parameters.has_key('ignore_trac_user_settings'):
            self.IGNORE_TRAC_USER_SETTINGS = int(parameters['ignore_trac_user_settings'])
        else:
            self.IGNORE_TRAC_USER_SETTINGS = 0

    def spam(self, message):
        """
        # X-Spam-Score: *** (3.255) BAYES_50,DNS_FROM_AHBL_RHSBL,HTML_
        # Note if Spam_level then '*' are included
        """
        spam = False
        if message.has_key(self.SPAM_HEADER):
            spam_l = string.split(message[self.SPAM_HEADER])

            try:
                number = spam_l[0].count('*')
            except IndexError, detail:
                number = 0

            if number >= self.SPAM_LEVEL:
                spam = True

        # treat virus mails as spam
        #
        elif message.has_key('X-Virus-found'):
            spam = True

        # How to handle SPAM messages
        #
        if self.DROP_SPAM and spam:
            if self.DEBUG > 2 :
                print 'This message is a SPAM. Automatic ticket insertion refused (SPAM level > %d' % self.SPAM_LEVEL

            return 'drop'

        elif spam:

            return 'Spam'

        else:

            return False

    def email_header_acl(self, keyword, header_field, default):
        """
        This function wil check if the email address is allowed or denied
        to send mail to the ticket list
    """
        try:
            mail_addresses = self.parameters[keyword]

            # Check if we have an empty string
            #
            if not mail_addresses:
                return default

        except KeyError, detail:
            if self.DEBUG > 2 :
                print 'TD: %s not defined, all messages are allowed.' %(keyword)

            return default

        mail_addresses = string.split(mail_addresses, ',')

        for entry in mail_addresses:
            entry = entry.strip()
            TO_RE = re.compile(entry, re.VERBOSE|re.IGNORECASE)
            result =  TO_RE.search(header_field)
            if result:
                return True

        return False

    def email_to_unicode(self, message_str):
        """
        Email has 7 bit ASCII code, convert it to unicode with the charset
that is encoded in 7-bit ASCII code and encode it as utf-8 so Trac
        understands it.
        """
        results =  email.Header.decode_header(message_str)
        str = None
        for text,format in results:
            if format:
                try:
                    temp = unicode(text, format)
                except UnicodeError, detail:
                    # This always works
                    #
                    temp = unicode(text, 'iso-8859-15')
                except LookupError, detail:
                    #text = 'ERROR: Could not find charset: %s, please install' %format
                    #temp = unicode(text, 'iso-8859-15')
                    temp = message_str

            else:
                temp = string.strip(text)
                temp = unicode(text, 'iso-8859-15')

            if str:
                str = '%s %s' %(str, temp)
            else:
                str = '%s' %temp

        #str = str.encode('utf-8')
        return str

    def debug_body(self, message_body, tempfile=False):
        if tempfile:
            import tempfile
            body_file = tempfile.mktemp('.email2trac')
        else:
            body_file = os.path.join(self.TMPDIR, 'body.txt')

        print 'TD: writing body (%s)' % body_file
        fx = open(body_file, 'wb')
        if not message_body:
            message_body = '(None)'

        message_body = message_body.encode('utf-8')
        #message_body = unicode(message_body, 'iso-8859-15')

        fx.write(message_body)
        fx.close()
        try:
            os.chmod(body_file,S_IRWXU|S_IRWXG|S_IRWXO)
        except OSError:
            pass

    def debug_attachments(self, message_parts):
        n = 0
        for part in message_parts:
            # Skip inline text parts
            if not isinstance(part, tuple):
                continue

            (original, filename, part) = part

            n = n + 1
            print 'TD: part%d: Content-Type: %s' % (n, part.get_content_type())
            print 'TD: part%d: filename: %s' % (n, part.get_filename())

            part_file = os.path.join(self.TMPDIR, filename)
            #part_file = '/var/tmp/part%d' % n
            print 'TD: writing part%d (%s)' % (n,part_file)
            fx = open(part_file, 'wb')
            text = part.get_payload(decode=1)
            if not text:
                text = '(None)'
            fx.write(text)
            fx.close()
            try:
                os.chmod(part_file,S_IRWXU|S_IRWXG|S_IRWXO)
            except OSError:
                pass

    def email_header_txt(self, m):
        """
        Display To and CC addresses in description field
        """
        str = ''
        #if m['To'] and len(m['To']) > 0 and m['To'] != 'hic@sara.nl':
        if m['To'] and len(m['To']) > 0:
            str = "'''To:''' %s\r\n" %(m['To'])
        if m['Cc'] and len(m['Cc']) > 0:
            str = "%s'''Cc:''' %s\r\n" % (str, m['Cc'])

        return  self.email_to_unicode(str)


    def get_sender_info(self, message):
        """
        Get the default author name and email address from the message
        """

        self.email_to = self.email_to_unicode(message['to'])
        self.to_name, self.to_email_addr = email.Utils.parseaddr (self.email_to)

        self.email_from = self.email_to_unicode(message['from'])
        self.author, self.email_addr  = email.Utils.parseaddr(self.email_from)

        # Trac can not handle author's name that contains spaces
        #
        self.author = self.email_addr

        if self.IGNORE_TRAC_USER_SETTINGS:
            return

        # Is this a registered user, use email address as search key:
        # result:
        #   u : login name
        #   n : Name that the user has set in the settings tab
        #   e : email address that the user has set in the settings tab
        #
        users = [ (u,n,e) for (u, n, e) in self.env.get_known_users(self.db)
                if e and (e.lower() == self.email_addr.lower()) ]

        if len(users) == 1:
            self.email_from = users[0][0]
            self.author = users[0][0]

    def set_reply_fields(self, ticket, message):
        """
        Set all the right fields for a new ticket
        """

        ## Only use name or email adress
        #ticket['reporter'] = self.email_from
        ticket['reporter'] = self.author


        # Put all CC-addresses in ticket CC field
        #
        if self.REPLY_ALL:
            #tos = message.get_all('to', [])
            ccs = message.get_all('cc', [])

            addrs = email.Utils.getaddresses(ccs)
            if not addrs:
                return

            # Remove reporter email address if notification is
            # on
            #
            if self.notification:
                try:
                    addrs.remove((self.author, self.email_addr))
                except ValueError, detail:
                    pass

            for name,mail in addrs:
                try:
                    mail_list = '%s, %s' %(mail_list, mail)
                except UnboundLocalError, detail:
                    mail_list = mail

            if mail_list:
                ticket['cc'] = self.email_to_unicode(mail_list)

    def save_email_for_debug(self, message, tempfile=False):
        if tempfile:
            import tempfile
            msg_file = tempfile.mktemp('.email2trac')
        else:
            #msg_file = '/var/tmp/msg.txt'
            msg_file = os.path.join(self.TMPDIR, 'msg.txt')

        print 'TD: saving email to %s' % msg_file
        fx = open(msg_file, 'wb')
        fx.write('%s' % message)
        fx.close()
        try:
            os.chmod(msg_file,S_IRWXU|S_IRWXG|S_IRWXO)
        except OSError:
            pass

    def str_to_dict(self, str):
        """
        Transfrom a str of the form [<key>=<value>]+ to dict[<key>] = <value>
        """

        fields = string.split(str, ',')

        result = dict()
        for field in fields:
            try:
                index, value = string.split(field, '=')

                # We can not change the description of a ticket via the subject
                # line. The description is the body of the email
                #
                if index.lower() in ['description']:
                    continue

                if value:
                    result[index.lower()] = value

            except ValueError:
                pass

        return result

    def update_ticket_fields(self, ticket, user_dict, use_default=None):
        """
        This will update the ticket fields. It will check if the
        given fields are known and if the right values are specified
        It will only update the ticket field value:
                - If the field is known
                - If the value supplied is valid for the ticket field.
                  If not then there are two options:
                   1) Skip the value (use_default=None)
                   2) Set default value for field (use_default=1)
        """

        # Build a system dictionary from the ticket fields
        # with field as index and option as value
        #
        sys_dict = dict()
        for field in ticket.fields:
            try:
                sys_dict[field['name']] = field['options']

            except KeyError:
                sys_dict[field['name']] = None
                pass

        # Check user supplied fields an compare them with the
        # system one's
        #
        for field,value in user_dict.items():
            if self.DEBUG >= 10:
                print  'user_field\t %s = %s' %(field,value)

            if sys_dict.has_key(field):

                # Check if value is an allowed system option, if TypeError then
                # every value is allowed
                #
                try:
                    if value in sys_dict[field]:
                        ticket[field] = value
                    else:
                        # Must we set a default if value is not allowed
                        #
                        if use_default:
                            value = self.get_config('ticket', 'default_%s' %(field) )
                            ticket[field] = value

                except TypeError:
                    ticket[field] = value

                if self.DEBUG >= 10:
                    print  'ticket_field\t %s = %s' %(field,  ticket[field])

    def ticket_update(self, m, id, spam):
        """
        If the current email is a reply to an existing ticket, this function
        will append the contents of this email to that ticket, instead of
        creating a new one.
        """
        if self.DEBUG:
            print "TD: ticket_update: %s" %id

        # Must we update ticket fields
        #
        update_fields = dict()
        try:
            id, keywords = string.split(id, '?')

            # Skip the last ':' character
            #
            keywords = keywords[:-1]
            update_fields = self.str_to_dict(keywords)

            # Strip '#'
            #
            self.id = int(id[1:])

        except ValueError:
            # Strip '#' and ':'
            #
            self.id = int(id[1:-1])


        # When is the change committed
        #
        #
        if self.VERSION == 0.11:
            utc = UTC()
            when = datetime.now(utc)
        else:
            when = int(time.time())

        try:
            tkt = Ticket(self.env, self.id, self.db)
        except util.TracError, detail:
            # Not a valid ticket
            self.id = None
            return False

        # reopen the ticket if it is was closed
        # We must use the ticket workflow framework
        #
        if tkt['status'] in ['closed']:

            #print controller.actions['reopen']
            #
            # As reference
            # req = Mock(href=Href('/'), abs_href=Href('http://www.example.com/'), authname='anonymous', perm=MockPerm(), args={})
            #
            #a = controller.render_ticket_action_control(req, tkt, 'reopen')
            #print 'controller : ', a
            #
            #b = controller.get_all_status()
            #print 'get all status: ', b
            #
            #b = controller.get_ticket_changes(req, tkt, 'reopen')
            #print 'get_ticket_changes :', b

            if self.WORKFLOW and (self.VERSION in ['0.11']) :
                from trac.ticket.default_workflow import ConfigurableTicketWorkflow
                from trac.test import Mock, MockPerm

                req = Mock(authname='anonymous', perm=MockPerm(), args={})

                controller = ConfigurableTicketWorkflow(self.env)
                fields = controller.get_ticket_changes(req, tkt, self.WORKFLOW)

                if self.DEBUG:
                    print 'TD: Workflow ticket update fields: ', fields

                for key in fields.keys():
                    tkt[key] = fields[key]

            else:
                tkt['status'] = 'reopened'
                tkt['resolution'] = ''

        # Must we update some ticket fields properties
        #
        if update_fields:
            self.update_ticket_fields(tkt, update_fields)

        message_parts = self.get_message_parts(m)
        message_parts = self.unique_attachment_names(message_parts)

        if self.EMAIL_HEADER:
            message_parts.insert(0, self.email_header_txt(m))

        body_text = self.body_text(message_parts)

        if body_text.strip() or update_fields:
            if self.DRY_RUN:
                print 'DRY_RUN: tkt.save_changes(self.author, comment) ', self.author
            else:
                tkt.save_changes(self.author, body_text, when)

        if self.VERSION  == 0.9:
            str = self.attachments(message_parts, True)
        else:
            str = self.attachments(message_parts)

        if self.notification and not spam:
            self.notify(tkt, False, when)

        return True

    def set_ticket_fields(self, ticket):
        """
        set the ticket fields to value specified
                - /etc/email2trac.conf with <prefix>_<field>
                - trac default values, trac.ini
        """
        user_dict = dict()

        for field in ticket.fields:

            name = field['name']

            # skip some fields like resolution
            #
            if name in [ 'resolution' ]:
                continue

            # default trac value
            #
            if not field.get('custom'):
                value = self.get_config('ticket', 'default_%s' %(name) )
            else:
                value = field.get('value')
                options = field.get('options')
                if value and options and value not in options:
                    value = options[int(value)]

            if self.DEBUG > 10:
                print 'trac.ini name %s = %s' %(name, value)

            prefix = self.parameters['ticket_prefix']
            try:
                value = self.parameters['%s_%s' %(prefix, name)]
                if self.DEBUG > 10:
                    print 'email2trac.conf %s = %s ' %(name, value)

            except KeyError, detail:
                pass

            if self.DEBUG:
                print 'user_dict[%s] = %s' %(name, value)

            user_dict[name] = value

        self.update_ticket_fields(ticket, user_dict, use_default=1)

        # Set status ticket
        #`
        ticket['status'] = 'new'



    def new_ticket(self, msg, subject, spam, set_fields = None):
        """
        Create a new ticket
        """
        if self.DEBUG:
            print "TD: new_ticket"

        tkt = Ticket(self.env)
        self.set_ticket_fields(tkt)

        # Old style setting for component, will be removed
        #
        if spam:
            tkt['component'] = 'Spam'

        elif self.parameters.has_key('component'):
            tkt['component'] = self.parameters['component']

        if not msg['Subject']:
            tkt['summary'] = u'(No subject)'
        else:
            tkt['summary'] = subject

        self.set_reply_fields(tkt, msg)

        if set_fields:
            rest, keywords = string.split(set_fields, '?')

            if keywords:
                update_fields = self.str_to_dict(keywords)
                self.update_ticket_fields(tkt, update_fields)

        # produce e-mail like header
        #
        head = ''
        if self.EMAIL_HEADER > 0:
            head = self.email_header_txt(msg)

        message_parts = self.get_message_parts(msg)
        message_parts = self.unique_attachment_names(message_parts)

        if self.EMAIL_HEADER > 0:
            message_parts.insert(0, self.email_header_txt(msg))

        body_text = self.body_text(message_parts)

        tkt['description'] = body_text

        #when = int(time.time())
        #
        utc = UTC()
        when = datetime.now(utc)

        if not self.DRY_RUN:
            self.id = tkt.insert()

        changed = False
        comment = ''

        # some routines in trac are dependend on ticket id
        # like alternate notify template
        #
        if self.notify_template:
            tkt['id'] = self.id
            changed = True

        # Rewrite the description if we have mailto enabled
        #
        if self.MAILTO:
            changed = True
            comment = u'\nadded mailto line\n'
            mailto = self.html_mailto_link( m['Subject'], body_text)

            tkt['description'] = u'%s\r\n%s%s\r\n' \
                    %(head, mailto, body_text)

        str =  self.attachments(message_parts)
        if str:
            changed = True
            comment = '%s\n%s\n' %(comment, str)

        if changed:
            if self.DRY_RUN:
                print 'DRY_RUN: tkt.save_changes(self.author, comment) ', self.author
            else:
                tkt.save_changes(self.author, comment)
                #print tkt.get_changelog(self.db, when)

        if self.notification and not spam:
            self.notify(tkt, True)

    def parse(self, fp):
        global m

        m = email.message_from_file(fp)

        if not m:
            if self.DEBUG:
                print "TD: This is not a valid email message format"
            return

        # Work around lack of header folding in Python; see http://bugs.python.org/issue4696
        m.replace_header('Subject', m['Subject'].replace('\r', '').replace('\n', ''))

        if self.DEBUG > 1:        # save the entire e-mail message text
            message_parts = self.get_message_parts(m)
            message_parts = self.unique_attachment_names(message_parts)
            self.save_email_for_debug(m, True)
            body_text = self.body_text(message_parts)
            self.debug_body(body_text, True)
            self.debug_attachments(message_parts)

        self.db = self.env.get_db_cnx()
        self.get_sender_info(m)

        if not self.email_header_acl('white_list', self.email_addr, True):
            if self.DEBUG > 1 :
                print 'Message rejected : %s not in white list' %(self.email_addr)
            return False

        if self.email_header_acl('black_list', self.email_addr, False):
            if self.DEBUG > 1 :
                print 'Message rejected : %s in black list' %(self.email_addr)
            return False

        if not self.email_header_acl('recipient_list', self.to_email_addr, True):
            if self.DEBUG > 1 :
                print 'Message rejected : %s not in recipient list' %(self.to_email_addr)
            return False

        # If drop the message
        #
        if self.spam(m) == 'drop':
            return False

        elif self.spam(m) == 'spam':
            spam_msg = True
        else:
            spam_msg = False

        if self.get_config('notification', 'smtp_enabled') in ['true']:
            self.notification = 1
        else:
            self.notification = 0

        if not m['Subject']:
            return False
        else:
            subject  = self.email_to_unicode(m['Subject'])

        #
        # [hic] #1529: Re: LRZ
        # [hic] #1529?owner=bas,priority=medium: Re: LRZ
        #
        TICKET_RE = re.compile(r"""
                |(?P<new_fields>[#][?].*)
                |(?P<reply>[#][\d]+:)
                |(?P<reply_fields>[#][\d]+\?.*?:)
                """, re.VERBOSE)

        result =  TICKET_RE.search(subject)

        if result:
            # update ticket + fields
            #
            if result.group('reply_fields') and self.TICKET_UPDATE:
                self.ticket_update(m, result.group('reply_fields'), spam_msg)

            # Update ticket
            #
            elif result.group('reply') and self.TICKET_UPDATE:
                self.ticket_update(m, result.group('reply'), spam_msg)

            # New ticket + fields
            #
            elif result.group('new_fields'):
                self.new_ticket(m, subject[:result.start('new_fields')], spam_msg, result.group('new_fields'))

        # Create ticket
        #
        else:
            self.new_ticket(m, subject, spam_msg)

    def strip_signature(self, text):
        """
        Strip signature from message, inspired by Mailman software
        """
        body = []
        for line in text.splitlines():
            if line == '-- ':
                break
            body.append(line)

        return ('\n'.join(body))

    def reflow(self, text, delsp = 0):
        """
        Reflow the message based on the format="flowed" specification (RFC 3676)
        """
        flowedlines = []
        quotelevel = 0
        prevflowed = 0

        for line in text.splitlines():
            from re import match

            # Figure out the quote level and the content of the current line
            m = match('(>*)( ?)(.*)', line)
            linequotelevel = len(m.group(1))
            line = m.group(3)

            # Determine whether this line is flowed
            if line and line != '-- ' and line[-1] == ' ':
                flowed = 1
            else:
                flowed = 0

            if flowed and delsp and line and line[-1] == ' ':
                line = line[:-1]

            # If the previous line is flowed, append this line to it
            if prevflowed and line != '-- ' and linequotelevel == quotelevel:
                flowedlines[-1] += line
            # Otherwise, start a new line
            else:
                flowedlines.append('>' * linequotelevel + line)

            prevflowed = flowed


        return '\n'.join(flowedlines)

    def strip_quotes(self, text):
        """
        Strip quotes from message by Nicolas Mendoza
        """
        body = []
        for line in text.splitlines():
            if line.startswith(self.EMAIL_QUOTE):
                continue
            body.append(line)

        return ('\n'.join(body))

    def wrap_text(self, text, replace_whitespace = False):
        """
        Will break a lines longer then given length into several small
        lines of size given length
        """
        import textwrap

        LINESEPARATOR = '\n'
        reformat = ''

        for s in text.split(LINESEPARATOR):
            tmp = textwrap.fill(s,self.USE_TEXTWRAP)
            if tmp:
                reformat = '%s\n%s' %(reformat,tmp)
            else:
                reformat = '%s\n' %reformat

        return reformat

        # Python2.4 and higher
        #
        #return LINESEPARATOR.join(textwrap.fill(s,width) for s in str.split(LINESEPARATOR))
        #


    def get_message_parts(self, msg):
        """
        parses the email message and returns a list of body parts and attachments
        body parts are returned as strings, attachments are returned as tuples of (filename, Message object)
        """
        message_parts = []

        # This is used to figure out when we are inside an AppleDouble container
        # AppleDouble containers consists of two parts: Mac-specific file data, and platform-independent data
        # We strip away Mac-specific stuff
        appledouble_parts = []

        ALTERNATIVE_MULTIPART = False

        for part in msg.walk():
            if self.DEBUG:
                print 'TD: Message part: Main-Type: %s' % part.get_content_maintype()
                print 'TD: Message part: Content-Type: %s' % part.get_content_type()


            # Check whether we just finished processing an AppleDouble container
            if part not in appledouble_parts:
                appledouble_parts = []

            ## Check content type
            #
            if part.get_content_type() == 'application/mac-binhex40':
                #
                # Special handling for BinHex attachments. Options are drop (leave out with no warning), warn (and leave out), and keep
                #
                if self.BINHEX == 'warn':
                    message_parts.append("'''A BinHex attachment named '%s' was ignored (use MIME encoding instead).'''" % part.get_filename())
                    continue
                elif self.BINHEX == 'drop':
                    continue

            elif part.get_content_type() == 'application/applefile':
                #
                # Special handling for the Mac-specific part of AppleDouble/AppleSingle attachments. Options are strip (leave out with no warning), warn (and leave out), and keep
                #

                if part in appledouble_parts:
                    if self.APPLEDOUBLE == 'warn':
                        message_parts.append("'''The resource fork of an attachment named '%s' was removed.'''" % part.get_filename())
                        continue
                    elif self.APPLEDOUBLE == 'strip':
                        continue
                else:
                    if self.APPLESINGLE == 'warn':
                        message_parts.append("'''An AppleSingle attachment named '%s' was ignored (use MIME encoding instead).'''" % part.get_filename())
                        continue
                    elif self.APPLESINGLE == 'drop':
                        continue

            elif part.get_content_type() == 'multipart/appledouble':
                #
                # If we entering an AppleDouble container, set up appledouble_parts so that we know what to do with its subparts
                #
                appledouble_parts = part.get_payload()
                continue

            elif part.get_content_type() == 'multipart/alternative':
                ALTERNATIVE_MULTIPART = True
                continue

            # Skip multipart containers
            #
            if part.get_content_maintype() == 'multipart':
                if self.DEBUG:
                    print "TD: Skipping multipart container"
                continue

            # Check if this is an inline part. It's inline if there is co Cont-Disp header, or if there is one and it says "inline"
            inline = self.inline_part(part)

            # Drop HTML message
            if ALTERNATIVE_MULTIPART and self.DROP_ALTERNATIVE_HTML_VERSION:
                if part.get_content_type() == 'text/html':
                    if self.DEBUG:
                        print "TD: Skipping alternative HTML message"

                    ALTERNATIVE_MULTIPART = False
                    continue

            # Inline text parts are where the body is
            if part.get_content_type() == 'text/plain' and inline:
                if self.DEBUG:
                    print 'TD:               Inline body part'

                # Try to decode, if fails then do not decode
                #
                body_text = part.get_payload(decode=1)
                if not body_text:
                    body_text = part.get_payload(decode=0)

                format = email.Utils.collapse_rfc2231_value(part.get_param('Format', 'fixed')).lower()
                delsp = email.Utils.collapse_rfc2231_value(part.get_param('DelSp', 'no')).lower()

                if self.REFLOW and not self.VERBATIM_FORMAT and format == 'flowed':
                    body_text = self.reflow(body_text, delsp == 'yes')

                if self.STRIP_SIGNATURE:
                    body_text = self.strip_signature(body_text)

                if self.STRIP_QUOTES:
                    body_text = self.strip_quotes(body_text)

                if self.USE_TEXTWRAP:
                    body_text = self.wrap_text(body_text)

                # Get contents charset (iso-8859-15 if not defined in mail headers)
                #
                charset = part.get_content_charset()
                if not charset:
                    charset = 'iso-8859-15'

                try:
                    ubody_text = unicode(body_text, charset)

                except UnicodeError, detail:
                    ubody_text = unicode(body_text, 'iso-8859-15')

                except LookupError, detail:
                    ubody_text = 'ERROR: Could not find charset: %s, please install' %(charset)

                if self.VERBATIM_FORMAT:
                    message_parts.append('{{{\r\n%s\r\n}}}' %ubody_text)
                else:
                    message_parts.append('%s' %ubody_text)
            else:
                if self.DEBUG:
                    print 'TD:               Filename: %s' % part.get_filename()

                message_parts.append((part.get_filename(), part))

        return message_parts

    def unique_attachment_names(self, message_parts):
        renamed_parts = []
        attachment_names = set()
        for part in message_parts:

            # If not an attachment, leave it alone
            if not isinstance(part, tuple):
                renamed_parts.append(part)
                continue

            (filename, part) = part
            # Decode the filename
            if filename:
                filename = self.email_to_unicode(filename)
            # If no name, use a default one
            else:
                filename = 'untitled-part'

                # Guess the extension from the content type, use non strict mode
                # some additional non-standard but commonly used MIME types
                # are also recognized
                #
                ext = mimetypes.guess_extension(part.get_content_type(), False)
                if not ext:
                    ext = '.bin'

                filename = '%s%s' % (filename, ext)

            # Discard relative paths in attachment names
            filename = filename.replace('\\', '/').replace(':', '/')
            filename = os.path.basename(filename)

            # We try to normalize the filename to utf-8 NFC if we can.
            # Files uploaded from OS X might be in NFD.
            # Check python version and then try it
            #
            if sys.version_info[0] > 2 or (sys.version_info[0] == 2 and sys.version_info[1] >= 3):
                try:
                    filename = unicodedata.normalize('NFC', unicode(filename, 'utf-8')).encode('utf-8')
                except TypeError:
                    pass

            if self.QUOTE_ATTACHMENT_FILENAMES:
                try:
                    filename = urllib.quote(filename)
                except KeyError, detail:
                    filename = urllib.quote(filename.encode('utf-8'))

            # Make the filename unique for this ticket
            num = 0
            unique_filename = filename
            filename, ext = os.path.splitext(filename)

            while unique_filename in attachment_names or self.attachment_exists(unique_filename):
                num += 1
                unique_filename = "%s-%s%s" % (filename, num, ext)

            if self.DEBUG:
                print 'TD: Attachment with filename %s will be saved as %s' % (filename, unique_filename)

            attachment_names.add(unique_filename)

            renamed_parts.append((filename, unique_filename, part))

        return renamed_parts

    def inline_part(self, part):
        return part.get_param('inline', None, 'Content-Disposition') == '' or not part.has_key('Content-Disposition')


    def attachment_exists(self, filename):

        if self.DEBUG:
            print "TD: attachment_exists: Ticket number : %s, Filename : %s" %(self.id, filename)

        # We have no valid ticket id
        #
        if not self.id:
            return False

        try:
            att = attachment.Attachment(self.env, 'ticket', self.id, filename)
            return True
        except attachment.ResourceNotFound:
            return False

    def body_text(self, message_parts):
        body_text = []

        for part in message_parts:
            # Plain text part, append it
            if not isinstance(part, tuple):
                body_text.extend(part.strip().splitlines())
                body_text.append("")
                continue

            (original, filename, part) = part
            inline = self.inline_part(part)

            if part.get_content_maintype() == 'image' and inline:
                body_text.append('[[Image(%s)]]' % filename)
                body_text.append("")
            else:
                body_text.append('[attachment:"%s"]' % filename)
                body_text.append("")

        body_text = '\r\n'.join(body_text)
        return body_text

    def notify(self, tkt, new=True, modtime=0):
        """
        A wrapper for the TRAC notify function. So we can use templates
        """
        if self.DRY_RUN:
            print 'DRY_RUN: self.notify(tkt, True) ', self.author
            return
        try:
            # create false {abs_}href properties, to trick Notify()
            #
            if not self.VERSION == 0.11:
                self.env.abs_href = Href(self.get_config('project', 'url'))
                self.env.href = Href(self.get_config('project', 'url'))

            tn = TicketNotifyEmail(self.env)

            if self.notify_template:

                if self.VERSION == 0.11:

                    from trac.web.chrome import Chrome

                    if self.notify_template_update and not new:
                        tn.template_name = self.notify_template_update
                    else:
                        tn.template_name = self.notify_template

                    tn.template = Chrome(tn.env).load_template(tn.template_name, method='text')

                else:

                    tn.template_name = self.notify_template;

            tn.notify(tkt, new, modtime)

        except Exception, e:
            print 'TD: Failure sending notification on creation of ticket #%s: %s' %(self.id, e)

    def html_mailto_link(self, subject, body):
        """
        This function returns a HTML mailto tag with the ticket id and author email address
        """
        if not self.author:
            author = self.email_addr
        else:
            author = self.author

        # use urllib to escape the chars
        #
        str = 'mailto:%s?Subject=%s&Cc=%s' %(
               urllib.quote(self.email_addr),
                   urllib.quote('Re: #%s: %s' %(self.id, subject)),
                   urllib.quote(self.MAILTO_CC)
                   )

        str = '\r\n{{{\r\n#!html\r\n<a\r\n href="%s">Reply to: %s\r\n</a>\r\n}}}\r\n' %(str, author)
        return str

    def attachments(self, message_parts, update=False):

        """save any attachments as files in the ticket's directory
        """
        if self.DRY_RUN:
            print "DRY_RUN: no attachments saved"
            return ''

        count = 0

        # Get Maxium attachment size
        #
        max_size = int(self.get_config('attachment', 'max_size'))
        status   = ''

        for part in message_parts:
            # Skip body parts
            if not isinstance(part, tuple):
                continue

            (original, filename, part) = part
            #
            # Must be tuneables HvB
            #
            path, fd =  util.create_unique_file(os.path.join(self.TMPDIR, filename))
            text = part.get_payload(decode=1)
            if not text:
                text = '(None)'
            fd.write(text)
            fd.close()

            # get the file_size
            #
            stats = os.lstat(path)
            file_size = stats[stat.ST_SIZE]

            # Check if the attachment size is allowed
            #
            if (max_size != -1) and (file_size > max_size):
                status = '%s\nFile %s is larger then allowed attachment size (%d > %d)\n\n' \
                        %(status, original, file_size, max_size)

                os.unlink(path)
                continue
            else:
                count = count + 1

            # Insert the attachment
            #
            fd = open(path, 'rb')
            att = attachment.Attachment(self.env, 'ticket', self.id)

            # This will break the ticket_update system, the body_text is vaporized
            # ;-(
            #
            if not update:
                att.author = self.author
                att.description = self.email_to_unicode('Added by email2trac')

            att.insert(filename, fd, file_size)
            #except  util.TracError, detail:
            #       print detail

            # Remove the created temporary filename
            #
            fd.close()
            os.unlink(path)

        # Return how many attachments
        #
        status = 'This message has %d attachment(s)\n%s' %(count, status)
        return status


def mkdir_p(dir, mode):
    '''do a mkdir -p'''

    arr = string.split(dir, '/')
    path = ''
    for part in arr:
        path = '%s/%s' % (path, part)
        try:
            stats = os.stat(path)
        except OSError:
            os.mkdir(path, mode)

def ReadConfig(file, name):
    """
    Parse the config file
    """
    if not os.path.isfile(file):
        print 'File %s does not exist' %file
        sys.exit(1)

    config = trac_config.Configuration(file)

    # Use given project name else use defaults
    #
    if name:
        sections = config.sections()
        if not name in sections:
            print "Not a valid project name: %s" %name
            print "Valid names: %s" %sections
            sys.exit(1)

        project =  dict()
        for option, value in  config.options(name):
            project[option] = value

    else:
        # use some trac internals to get the defaults
        #
        project = config.parser.defaults()

    return project


from django.core.management.base import BaseCommand
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        #make_option("-d", "--daemon", dest="daemonize", action="store_true"),
    )

    def handle(self, *args, **options):
        import pdb; pdb.set_trace()
        print "whee"
        version = '0.1' #XXX
        settings = {}
        from trac.env import Environment
        env = Environment(settings['project'], create=0)
        tktparser = TicketEmailParser(env, settings, float(version))
        try:
            tktparser.parse(sys.stdin)
        except Exception, error:
            traceback.print_exc()
            if m:
                tktparser.save_email_for_debug(m, True)

            sys.exit(1)
