# kjdfbsd sdfnsdf sdf sdf df
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
import cgi
import imp
import urllib
import sys
import os

class Configuration(object):
    """Stores configuration values."""
    version = "0.2"

    def __init__(self):
        print("* Reading configuration.")
        self._config = imp.load_source("data.config", sys.path[0]+"/data/config.py")
        self._default = imp.load_source("data.defaultcfg", sys.path[0]+"/data/config.default.py")

    def reload(self):
        """Re-imports the configuration."""
        del self._config
        self.__init__()

    def __getitem__(self, item):
        if isinstance(item, int):
            raise TypeError("Nope!")
        elif item == "__version":
            return self.version
        elif item.startswith("__"):
            return getattr(self._default, item)
        else:
            try:
                return getattr(self._config, item)
            except:
                return getattr(self._default, item)

    def __delattr__(self, item):
        raise self.MCHammer("Can't touch this!")

    class MCHammer(Exception):
        pass

class Language(object):
    def __init__(self, code):
        if not isinstance(code, basestring):
            raise TypeError("Nope!")
        print("* Loading language " + code)
        if "/" in code or "\\" in code:
            raise NameError("Nope!")
        self.code = code
        self._lang = imp.load_source("data.lang."+code, "{1}/data/lang/{0}.py".format(code, sys.path[0]))
        del self._lang.__builtins__

    def reload(self):
        """Re-imports the language."""
        del self._lang
        self.__init__(self.code)

    @property
    def getDict(self):
        return self._lang.__dict__

    def __getitem__(self, item):
        if isinstance(item, int):
            raise TypeError("Nope!")
        else:
            try:
                return getattr(self._lang, item)
            except:
                return item

    def __delattr__(self, item):
        if item != "_lang":
            raise self.MCHammer("Can't touch this!")

    class MCHammer(Exception):
        pass

class Extension(object):
    """Why"""
    IDENTIFIER = "net.pyboard.BaseExtension"
    PERMISSIONS = []
    def __init__(self, PyBoard):
        self.instance = PyBoard
        if not os.path.exists(self.instance.workd + "/data/extdata/"):
            os.mkdir(self.instance.workd + "/data/extdata/")
        self.dataFolder = self.instance.workd + "/data/extdata/" + self.IDENTIFIER
        if not os.path.exists(self.dataFolder):
            os.mkdir(self.dataFolder)

    def addPage(self, uri, function, host=""):
        try:
            self.instance.Pages
        except AttributeError:
            self.instance.Pages = {}
        if self.IDENTIFIER not in self.instance.Pages:
            self.instance.Pages[self.IDENTIFIER] = {}
        for key in self.instance.Pages:
            if "{0}/{1}".format(host.lower().strip("/"), uri.strip("/")) in self.instance.Pages[key]:
                self.log("There is already a function bound to this URI!")
        else:
            self.instance.Pages[self.IDENTIFIER]["{0}/{1}".format(host.lower().strip("/ "), uri.strip("/ "))] = function
            self.log("Bound {0} -> {1}".format("{0}/{1}".format(host.lower().strip("/ "), uri.strip("/ ")), function))

    def __str__(self):
        return "<PBExtension {0}>".format(self.IDENTIFIER)
    
    __repr__ = __str__

    def log(self, message):
        print("["+self.IDENTIFIER+"]: "+str(message))

    def redirect(self, location, headers=None):
        if not headers:
            headers = {}
        return Response(s="303 See Other", h=dict(headers.items() + [("Location", location)]), r="")

    def page_format(self, v={}, template=None, TemplateString=""):
        return self.instance.func.page_format(v=v, template=template, TemplateString="", root=self.dataFolder)

    def generateError(self, status="500 Internal Server Error", heading="Error", return_to="/", etext="An unspecified error occurred."):
        error = {
            "heading": unicode(heading),
            "errmsg": unicode(etext),
            "retlocation": unicode(return_to)
        }
        return Response(s=status, h={"Content-Type": "text/html"}, r=self.instance.func.page_format(v=error, template="error.pyb"))

class Request(object):
    """PyBoard HTTP request."""
    def __init__(self, instance, environ, origin=None):
        self.instance = instance
        self.environ = environ;
        self._authenticated, self._user = None, None
        self.url = urllib.unquote(environ["PATH_INFO"]);
        self.query = environ["QUERY_STRING"];
        self.origin = origin or environ["REMOTE_ADDR"]
        if environ["REQUEST_METHOD"] == "POST":
            self.form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ);
            self.post = True;
        else:
            self.post = False;
        self.cookies = {};
        self.has_cookies = False;
        if "HTTP_COOKIE" in environ:
            c = environ["HTTP_COOKIE"].split(';');
            try:
                for cookie in c:
                    this = cookie.split('=');
                    self.cookies[this[0].strip()] = urllib.unquote(this[1]);
            except IndexError:
                pass;
            if len(self.cookies) > 0:
                self.has_cookies = True;

    @property
    def authenticated(self):
        if self._authenticated == None:
            self.__performAuth__()
        return self._authenticated

    @property
    def user(self):
        if self._user == None:
            self.__performAuth__()
        return self._user

    def __performAuth__(self):
        if "pypAuthToken" in self.cookies:
            self._authenticated = self.instance.func.verifyLogin(self.cookies["pypAuthToken"], self.origin)
            if self._authenticated:
                self._user = self.instance.Sessions[self.cookies["pypAuthToken"].split("|")[0]][0]
        else:
            self._authenticated, self._user = 0, ""

    def contains(self, item):
        return "HTTP_"+item.upper().replace("-", "_") in self.environ

    __contains__ = contains

    def __getitem__(self, item):
        try:
            return self.environ["HTTP_"+item.upper().replace("-", "_")]
        except KeyError:
            raise NameError("HTTP header not found.")

class Response(object):
    def __init__(self, s="200 OK", h=None, r=""):
        self.status = s;
        self.headers = h or {};
        self.rdata = r;
        if "Content-Length" not in self.headers:
            self.headers["Content-Length"] = len(r)
        
    def __getitem__(self, key):
        if key == 0 or key == "status":
            return self.status;
        if key == 1 or key == "headers":
            return self.headers;
        if key == 2 or key == "rdata":
            return self.rdata;
    
    def __repr__(self):
        return "PyBoardResponse: {0}, {1} headers".format(self.status, len(self.headers));

    __str__ = __repr__;
