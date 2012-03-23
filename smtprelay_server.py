import sys
import tornado.options
import tornado.web
from tornado.escape import utf8
import settings
from settings import options, env
import logging
import simplejson as json
from lib.smtp import smtprelay
from tornadomail.message import EmailMessage, EmailMultiAlternatives


class BaseHandler(tornado.web.RequestHandler):
    def get_int_argument(self, name, default=None):
        value = self.get_argument(name, default=default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def error(self, status_code=500, status_txt=None, data=None):
        """write an api error in the appropriate response format"""
        self.api_response(status_code=status_code, status_txt=status_txt, data=data)

    def api_response(self, data, status_code=200, status_txt="OK"):
        """write an api response in json"""
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps(dict(data=data, status_code=status_code, status_txt=status_txt)) + "\n")


class PushHandler(BaseHandler):
    def get(self):
        '''
        N.B. x-smtpapi, headers and files not yet supported.
        '''
        attrs = frozenset(['to', 'toname', 'x-smtpapi', 'subject', 'text', 'html',
            'from', 'bcc', 'fromname', 'replyto', 'date', 'files', 'headers'])
        multi = frozenset(['to', 'toname', 'bcc', 'fromname', 'files'])
        required = frozenset(['to', 'subject', 'from'])
        missing = [y for y in required if y not in self.request.arguments]
        if missing:
            return self.error(status_code=400, status_txt="missing required arguments", data=missing)
                
        data = {}
        for key in attrs:
            if key in multi:
                data[key] = self.get_arguments(key, [])
            else:
                data[key] = self.get_argument(key, None)

        msg = EmailMultiAlternatives(data.get("subject"), data.get("text"), data.get("from"), data.get("to"),
            data.get("bcc"), connection=_smtp.connection)
        if data.get("html"):
            msg.attach_alternative(data.get("html"), "text/html")
        self.api_response(_smtp.send(msg))


class StatsHandler(BaseHandler):
    def get(self):
        self.api_response(_smtp.get_stats())


if __name__ == "__main__":
    tornado.options.define("port", default=8888, help="Listen on port", type=int)
    tornado.options.define("smtphost", default=None, help="smtp host", type=str)
    tornado.options.define("smtpport", default=25, help="smtp port", type=int)
    tornado.options.define("usetls", default=True, help="use TLS", type=bool)
    tornado.options.define("user", default=None, help="smtp user", type=str)
    tornado.options.define("password", default=None, help="smtp password", type=str)
    tornado.options.parse_command_line()
    ''' allow sensitive data to be passed on cmd line ( so everyone can see it w ps ) '''
    for key in ['smtphost', 'smtpport', 'user', 'password']:
        if key in tornado.options.options and tornado.options.options[key].value():
            options.get(env())[key] = tornado.options.options[key].value()

    logging.getLogger().setLevel(settings.get('logging_level'))

    _smtp = smtprelay(settings.get("smtphost"), settings.get("smtpport"),
        settings.get("user"), settings.get("password"), usetls=settings.get("usetls"))

    application = tornado.web.Application([
        (r"/push", PushHandler),
        (r"/stats", StatsHandler),
    ], debug=(env() == 'dev'))
    application.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
