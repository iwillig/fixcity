'''
This is a manage.py command for django which handles incoming email,
typically via stdin.

To hook this up with postfix, set up an alias along the lines of:

myaddress: "|PYTHON_EGG_CACHE=/tmp/my-egg-cache /PATH/TO/VENV/bin/python /PATH/TO/VENV/src/fixcity/fixcity/manage.py handle_mailin -u http://MYDOMAIN/rack/ --debug=9 - >> /var/log/MYLOGS/mailin.log 2>&1""
'''

# based on email2trac.py, which is Copyright (C) 2002 under the GPL v2 or later

from datetime import datetime
from optparse import make_option
from poster.encode import multipart_encode
from stat import S_IRWXU, S_IRWXG, S_IRWXO
import email.Header
import httplib2
import mimetypes
import os
import re
import socket
import string
import sys
import time
import traceback
import unicodedata
import urlparse

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import simplejson as json

class EmailParser(object):
    env = None
    comment = '> '
    msg = None
    
    def __init__(self, parameters):

        # Save parameters
        #
        self.parameters = parameters

        # Some useful mail constants
        #
        self.author = None
        self.email_addr = None
        self.email_from = None
        self.id = None

        # XXX Cull stuff that just stores a value, we should just
        # store all the parameters instead.
        if parameters.has_key('debug'):
            self.DEBUG = int(parameters['debug'])
        else:
            self.DEBUG = 0

        if parameters.has_key('email_quote'):
            self.EMAIL_QUOTE = str(parameters['email_quote'])
        else:
            self.EMAIL_QUOTE = '> '

        if parameters.has_key('email_header'):
            self.EMAIL_HEADER = int(parameters['email_header'])
        else:
            self.EMAIL_HEADER = 0

        if parameters.has_key('reply_all'):
            self.REPLY_ALL = int(parameters['reply_all'])
        else:
            self.REPLY_ALL = 0

        if parameters.has_key('rack_update'):
            self.RACK_UPDATE = int(parameters['rack_update'])
        else:
            self.RACK_UPDATE = 0

        if parameters.has_key('drop_alternative_html_version'):
            self.DROP_ALTERNATIVE_HTML_VERSION = int(parameters['drop_alternative_html_version'])
        else:
            self.DROP_ALTERNATIVE_HTML_VERSION = 0

        if parameters.has_key('strip_signature'):
            self.STRIP_SIGNATURE = int(parameters['strip_signature'])
        else:
            self.STRIP_SIGNATURE = 0

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

        # Use OS independend functions
        #
        self.TMPDIR = os.path.normcase('/tmp')
        if parameters.has_key('tmpdir'):
            self.TMPDIR = os.path.normcase(str(parameters['tmpdir']))


        self.MAX_ATTACHMENT_SIZE = int(parameters.get('max-attachment-size', -1))


    def email_to_unicode(self, message_str):
        """
        Email has 7 bit ASCII code, convert it to unicode with the charset
that is encoded in 7-bit ASCII code and encode it as utf-8.
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
            body_file = tempfile.mktemp('.handle_mailin')
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


    def get_sender_info(self):
        """
        Get the default author name and email address from the message
        """
        message = self.msg
        self.email_to = self.email_to_unicode(message['to'])
        self.to_name, self.to_email_addr = email.Utils.parseaddr (self.email_to)

        self.email_from = self.email_to_unicode(message['from'])
        self.author, self.email_addr  = email.Utils.parseaddr(self.email_from)

        # Trac can not handle author's name that contains spaces
        # XXX do we care about author's name for fixcity? prob not.
        self.author = self.email_addr



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


    def new_rack(self, title, address, spam):
        """
        Create a new rack
        """
        msg = self.msg
        if self.DEBUG:
            print "TD: new_rack"

        message_parts = self.get_message_parts()
        message_parts = self.unique_attachment_names(message_parts)

        description = self.description = self.body_text(message_parts)
        attachments = self.attachments(message_parts)
        # We don't bother with microsecond precision because
        # Django datetime fields can't parse it anyway.
        now = datetime.fromtimestamp(int(time.time()))
        data = dict(title=title,
                    description=description,
                    date=now.isoformat(' '),
                    address=address,
                    geocoded=0,  # Do server-side location processing.
                    got_communityboard=0,   # Ditto.
                    email=self.email_addr,
                    )
        
        if self.parameters.get('dry-run') and self.DEBUG:
            print "TD: would save rack here"
            return

        # This is the one thing i apparently can't do
        # when running as `nobody`.
        # And getting postfix to run this script as another user
        # seems to be a PITA.
        #rack = rackform.save()

        # So instead, let's POST our data to some URL...
        url = self.parameters['url']
        jsondata = json.dumps(data)
        http = httplib2.Http()
        headers = {'Content-type': 'application/json'}
        try:
            response, content = http.request(url, 'POST',
                                             headers=headers,
                                             body=jsondata)
        except socket.error:
            self.bounce('Sorry, the FixCity server appears to be down',
                        'Please try again later.')
            return

        if self.DEBUG:
            print "TD: server responded with:\n%s" % content

        if response.status >= 500:
            msg = 'Sorry, the server gave a %d error while handling your email.' % response.status
            msg += '\nThis is our fault, not yours!\n'
            msg += '\n\nResponse from the server:\n\n'
            msg += content  # XXX This isn't very useful, as it's raw HTML
            self.bounce('Server error! Could not add your bike rack', msg)
            return

        result = json.loads(content)
        if result.has_key('errors'):
            err_msg = "Please correct these errors and try again:\n"
            for k, v in sorted(result['errors'].items()):
                err_msg += "%s: %s\n" % (k, '; '.join(v))
            self.bounce("Please correct errors in your bike rack submission.",
                        err_msg)
            return

        if attachments.has_key('photo'):
            parsed_url = urlparse.urlparse(url)
            base_url = parsed_url[0] + '://' + parsed_url[1]
            photo_url = base_url + result['photo_url']

            datagen, headers = multipart_encode({'photo':
                                                 attachments['photo']})
            # httplib2 doesn't like poster's integer headers.
            headers['Content-Length'] = str(headers['Content-Length'])
            body = ''.join([s for s in datagen])
            response, content = http.request(photo_url, 'POST',
                                             headers=headers, body=body)
            # XXX handle errors
            if self.DEBUG:
                print "TD: result from photo upload:"
                print content
        # XXX need to add links per https://projects.openplans.org/fixcity/wiki/EmailText
        reply = "Thanks for your rack suggestion!\n\n"
        reply += "You must verify that your spot meets DOT requirements\n"
        reply += "before we can submit it.\n"
        reply += "To verify, go to: http://fixcity.org/verify\n\n"
        reply += "Thanks!\n\n"
        reply += "-The Open Planning Project & Livable Streets Initiative\n"
        self.reply("Thanks for your bike rack suggestion!", reply)


    def parse(self, fp):
        self.msg = email.message_from_file(fp)
        if not self.msg:
            if self.DEBUG:
                print "TD: This is not a valid email message format"
            return

        # Work around lack of header folding in Python; see http://bugs.python.org/issue4696
        self.msg.replace_header('Subject', self.msg['Subject'].replace('\r', '').replace('\n', ''))

        if self.DEBUG > 1:        # save the entire e-mail message text
            message_parts = self.get_message_parts()
            message_parts = self.unique_attachment_names(message_parts)
            self.save_email_for_debug(self.msg, True)
            body_text = self.body_text(message_parts)
            self.debug_body(body_text, True)
            self.debug_attachments(message_parts)

        self.get_sender_info()

        if not self.msg['Subject']:
            return False
        else:
            subject  = self.email_to_unicode(self.msg['Subject'])

        spam_msg = False #XXX not sure what this should be

        subject_re = re.compile(r'(?P<title>[^\@]*)\s*@(?P<address>.*)')
        subject_match = subject_re.search(subject)
        if subject_match:
            title = subject_match.group('title').strip()
            address = subject_match.group('address')
        else:
            address_re = re.compile(r'@(?P<address>.+)$', re.MULTILINE)
            address_match = address_re.search(body_text)
            if address_match:
                address = address_match.group('address')
            else:
                address = ''  # Let the server deal with lack of address.
            title = subject

        address = address.strip()
        self.new_rack(title, address, spam_msg)
            
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


    def get_message_parts(self):
        """
        parses the email message and returns a list of body parts and attachments
        body parts are returned as strings, attachments are returned as tuples of (filename, Message object)
        """
        msg = self.msg
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

                if self.STRIP_SIGNATURE:
                    body_text = self.strip_signature(body_text)

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

            # Make the filename unique for this rack
            num = 0
            unique_filename = filename
            filename, ext = os.path.splitext(filename)

            while unique_filename in attachment_names:
                num += 1
                unique_filename = "%s-%s%s" % (filename, num, ext)

            if self.DEBUG:
                print 'TD: Attachment with filename %s will be saved as %s' % (filename, unique_filename)

            attachment_names.add(unique_filename)

            renamed_parts.append((filename, unique_filename, part))

        return renamed_parts

    def inline_part(self, part):
        return part.get_param('inline', None, 'Content-Disposition') == '' or not part.has_key('Content-Disposition')



    def body_text(self, message_parts):
        body_text = []

        for part in message_parts:
            # Plain text part, append it
            if not isinstance(part, tuple):
                body_text.extend(part.strip().splitlines())
                body_text.append("")
                continue

        body_text = '\r\n'.join(body_text)
        self._body_text = body_text
        return body_text


    def attachments(self, message_parts):
        """save an attachment as a single photo
        """
        # Get Maxium attachment size
        #
        max_size = self.MAX_ATTACHMENT_SIZE
        status   = ''
        results = {}
        
        for part in message_parts:
            # Skip text body parts
            if not isinstance(part, tuple):
                continue

            (original, filename, part) = part
            text = part.get_payload(decode=1)
            if not text:
                continue
            file_size = len(text)

            # Check if the attachment size is allowed
            #
            if (max_size != -1) and (file_size > max_size):
                status = '%s\nFile %s is larger then allowed attachment size (%d > %d)\n\n' \
                        %(status, original, file_size, max_size)
                continue

            results[u'photo'] = SimpleUploadedFile.from_dict(
                {'filename': filename, 'content': text,
                 'content-type': 'image/jpeg'})
            # XXX what to do if there's more than one attachment?
            # we just ignore 'em.
            break
        return results


    def bounce(self, subject, body):
        if self.DEBUG:
            print "TD: Bouncing message to %s" % self.email_addr
        body += '\n\n------------ original message follows ---------\n\n'
        body += '\n'.join(['%s: %s' % h for h in self.msg._headers])
        body += '\n\n' + self.description  # XXX what else do we want?
        return self.reply(subject, body)
        
    def reply(self, subject, body):
        send_mail(subject, body, self.msg['to'], [self.email_addr],
                  fail_silently=False)
        


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--url', '-u', help="URL to post racks to", action="store"),
        make_option('--dry-run', action="store_true",
                    help="Don't save any data.", dest="dry_run"),
        make_option('--debug', type="int", default=0,
                    help="Add some verbosity and save any problematic data."),
        make_option('--strip-signature', action="store_true", default=True,
                    help="Remove signatures from incoming mail"),
        make_option('--max-attachment-size', type="int",
                    help="Max size of uploaded files."),

    )

    def handle(self, *args, **options):
        assert options['url'] is not None
        parser = EmailParser(options)
        did_stdin = False
        for filename in args:
            if filename == '-':
                if did_stdin:
                    continue
                thisfile = sys.stdin
                did_stdin = True
            else:
                thisfile = open(filename)
            try:
                parser.parse(thisfile)
            except Exception, error:
                traceback.print_exc()
                if parser.msg:
                    parser.save_email_for_debug(parser.msg, True)
                sys.exit(1) # XXX do a more informative bounce?
