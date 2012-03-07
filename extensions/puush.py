import Objects
import re
import json
import time
import urllib2

class main(Objects.Extension):
    """Implement the puush client API."""
    IDENTIFIER = "na.leijo.PuushClient"
    def __init__(self, rootClass):
        self.PluginConfiguration = {
            "forwardUpdateChecks": True,
        }
        Objects.Extension.__init__(self, rootClass)
        self.addPage("/dl/puush.xml", self.updateCheck)
        self.addPage("/dl/puush-win.txt", self.updateCheck)
        self.addPage("/dl/puush.zip", self.updatePayload)
        self.addPage("/dl/puush-win.zip", self.updatePayload)
        self.addPage("/api/hist", self.history)
        self.addPage("/api/auth", self.authAPI)
        self.addPage("/api/up", self.upload)
        self.addPage("/api/del", self.delete)
        self.addPage("/api/oshi", self.er)
        
        def updateCheck(self, request):
            try:
                version = urllib2.urlopen("http://puush.me{0}".format(request.url)).read()
                return Objects.Response(s="200 OK", h={}, r=version)
            except urllib2.URLError:
                return Objects.Response(s="200 OK", h={}, r="\( ._.)/")
        
        def updatePayload(self, request):
            try:
                update = urllib2.urlopen("http://puush.me{0}".format(request.url)).read()
                return Objects.Response(s="200 OK", h={}, r=update)
            except:
                return Objects.Response(s="404 Not Found", h={}, r="404")
        
        def er(self, request):
            return Objects.Response(s="200 OK", h={}, r="")
        
        def history(self, request):
            if request.post and "k" in request.form:
                user = self.instance.Database.getUserByKey(request.form["k"].value.decode("utf-8"))
                if not user:
                    return Objects.Response(s="200 OK", h={"Content-Type": "text/html"}, r="-1")
                else:
                    lastdrops = self.instance.Database.getDropsByUser(user["email"], limit=10, sort_by="uploaded_on")
                    lastdrops.reverse()
                    
            else:
                return Objects.Response(s="200 OK", h={"Content-Type": "text/html"}, r="-1")
                
