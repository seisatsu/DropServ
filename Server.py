# PyBoard - Like the moon hiding between the clouds.
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
import sys
import os
import time
import mimetypes
import traceback
import urllib
import imp
import warnings

import Database
import Objects
import Functions
import Pages

class Puush(object):
    """HA HA HA GO FUCK A SHIT UP YOUR ASS"""
    def __init__(self):
        t = time.time()
        self.Sessions = {}
        self.conf = Objects.Configuration()
        self.lang = Objects.Language(self.conf["Language"])
        print(self.lang["PB_STARTUP"].format(v=self.conf["__version"]))
        self.set_paths()
        self.func = Functions.Functions(self)
        self.bp = Pages.BasePages(self)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.load_extensions() # This raises RuntimeWarnings, which we really don't need to care about.
        if os.path.exists(self.workd+"/data/Puush.sqlite3"):
            self.Database = Database.DropDatabase(self.workd+"/data/Puush.sqlite3", self)
        else:
            self.Database = Database.DropDatabase(self.workd+"/data/Puush.sqlite3", self, init=True)
        mimetypes.init()
        t = time.time() - t
        print(self.lang["PB_DONE"].format(t="{:03.2f}".format(t)))

    def load_extensions(self):
        print(self.lang["PB_EXTENSION_LOAD_START"])
        self.Extensions, self._extm = [], []
        for i in os.listdir(self.workd+"/extensions"):
            if i.split(".")[-1] == "py":
                self.load_extension(i)
        print(self.lang["PB_EXTENSION_LOAD_DONE"].format(n=len(self.Extensions), s="s" if len(self.Extensions) > 1 or not self.Extensions else ""))

    def load_extension(self, i):
        print(self.lang["PB_IMPORTING_EXTENSION"].format(file=i))
        self._extm.append(imp.load_source("extensions.{0}".format("-".join(i.split(".")[:-1])), self.workd+"/extensions/{0}".format(i)))
        try:
            if not self._extm[-1].main.IDENTIFIER or self._extm[-1].main.IDENTIFIER == "net.pyboard.BaseExtension":
                del self._extm[-1]
                print(self.lang["PB_MISSING_IDENTIFIER"].format(e=i))
            elif self._extm[-1].main.IDENTIFIER.startswith("net.pyboard."):
                del self._extm[-1]
                print(self.lang["PB_BLACKLISTED_NS"].format(e=i))
            else:
                print(self.lang["PB_INIT_EXTENSION_CLASS"].format(id=self._extm[-1].main.IDENTIFIER))
                self.Extensions.append(self._extm[-1].main(self))
        except AttributeError:
            del self._extm[-1]
            print(self.lang["PB_INVALID_EXTENSION"].format(f=i))

    def set_paths(self):
        """Set up our working, serving, and remote directories, plus make sure that our dirs are all there"""
        self.workd = sys.path[0].rstrip("/")
        print(self.lang["PB_GOT_CWD"].format(d=self.workd))
        self.docroot = "{0}/{1}".format(self.workd, self.conf["DocumentRoot"])
        if not os.path.isdir(self.docroot):
            os.mkdir(self.docroot)
        for x in "extensions", "data/extdata":
            if not os.path.isdir("{0}/{1}".format(self.workd, x)):
                print(self.lang["PB_FOLDER_NONEXISTENT"].format(f=x))
                os.mkdir("{0}/{1}".format(self.workd, x))
        self.remote = "/"
        print(self.lang["PB_MAP_DIR"].format(loc=self.docroot, rem=self.remote))

    def wsgize(self, hdict):
        """Convert a dictionary of HTTP headers to the correct tuple-list WSGI format"""
        l = []
        for k, v in hdict.items():
            l.append((str(k), str(v)))
        return l

    def __call__(self, environ, start_response):
        """Main request handler."""
        Headers, StatusCode = {"Server": "PyBoard", "Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT")}, "200 OK"
        if environ["PATH_INFO"] is not "/":
            requested_resource = urllib.unquote(environ["PATH_INFO"]).rstrip('/');
        else:
            requested_resource = environ["PATH_INFO"]
        if self.conf["RealIPHeader"] and "HTTP_" + self.conf["RealIPHeader"].upper().replace("-", "_") in environ:
            request = Objects.Request(self, environ, environ["HTTP_" + self.conf["RealIPHeader"].upper().replace("-", "_")]);
        else:
            request = Objects.Request(self, environ)
        try:
            for e in self.Pages:
                if requested_resource in self.Pages[e]:
                    response = self.Pages[e][requested_resource](request);
                    Headers = dict(Headers.items() + response["headers"].items())
                    start_response(response["status"] or StatusCode, self.wsgize(Headers))
                    return response["rdata"]
            else:
                response = self.bp.serveFromFilesystem(request)
                Headers = dict(Headers.items() + response["headers"].items())
                start_response(response["status"] or StatusCode, self.wsgize(Headers))
                return response["rdata"]
        except Exception, e:
            print("\033[0;31m***\033[0m [ERROR] \033[0;31m***********************\033[0m")
            traceback.print_exc()
            print("\033[0;31m***********************************\033[0m")
            if self.conf["ShowErrorTraceback"]:
                ep = self.bp.generateError("500 Internal Server Error", etext="<h3 class='eth'>Unhandled exception: {1}</h3><pre class='et'>{0}</pre>".format(traceback.format_exc(), e))
                Headers = dict(Headers.items() + response["headers"].items())
                start_response(ep["status"] or StatusCode, self.wsgize(Headers))
                return ep["rdata"]
            else:
                response = self.bp.serveFromFilesystem(request, "{0}/{1}".format(self.docroot, self.conf["GenericErrorFile"]))
                Headers = dict(Headers.items() + response["headers"].items())
                start_response("500 Internal Server Error", self.wsgize(Headers))
                return response["rdata"]

application = py = Puush()