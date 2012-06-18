# HURR DURR IM A TRIPFAG LOOK AT ME BEING A BAKA
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
import Objects
import rfc822
import os
import time
import magic
import mimetypes
mimetypes.init()
import math
import hashlib
import re
import urllib

class BasePages(Objects.Extension):
    """Base web functionality for PyBoard."""
    IDENTIFIER = "net.pyboard"
    PERMISSIONS = ["base"]
    def __init__(self, PyBoard):
        Objects.Extension.__init__(self, PyBoard)
        self.magic = magic.Magic(mime=True)
        self.addPage("/", self.checkAuth)
        self.addPage("/upload", self.doPost)
        self.addPage("/delete", self.contentDestructor)
        self.addPage("/login", self.loginUser)
        self.addPage("/register", self.registerUser)
        self.addPage("/manage", self.listDrops)
        self.addPage("/changePass", self.changePassword)

    def checkAuth(self, request):
        if request.authenticated:
            return Objects.Response(s="200 OK", h={"Cache-Control": "no-cache; max-age=0"}, r=self.instance.func.page_format(v={}, template="index.pyb"))
        else:
            return Objects.Response(s="303 See Other", h={"Location": "/login"}, r="")
    
    def changePassword(self, request):
        if request.authenticated:
            if request.post:
                for x in ["oldpass", "newpass", "newpass2"]:
                    if x not in request.form:
                        return self.generateError("400 Bad Request", etext="wat", return_to="/manage")
                user = self.instance.Database.getUser(request.user)
                if (self.instance.func.hashPassword(request.form["oldpass"].value.decode("utf-8"), salt=user["salt"])[0] != user["pass"]):
                    return self.generateError("400 Bad Request", etext="Password incorrect.", return_to="/manage")
                elif len(request.form["newpass"].value.decode("utf-8").strip()) <= 4:
                    return self.generateError("400 Bad Request", etext="Passwords must be 5 or more characters in length.", return_to="/manage")
                elif request.form["newpass"].value.decode("utf-8").strip() != request.form["newpass2"].value.decode("utf-8").strip():
                    return self.generateError("400 Bad Request", etext="Passwords didn't match.", return_to="/manage")
                else:
                    self.instance.Database.changeUserPassword(request.user, request.form["newpass"].value.decode("utf-8").strip())
                    return self.generateError("200 OK", heading="OK", etext="Password updated.", return_to="/manage")
        else:
            return Objects.Response(s="303 See Other", h={"Location": "/login"}, r="")
    
    def contentDestructor(self, request):
        if request.post:
            if request.authenticated:
                toDelete = []
                for derp in request.form:
                    if derp.startswith("del_") and len(derp) > 4:
                        toDelete.append(derp[4:])
                for drop in toDelete:
                    try:
                        r = self.instance.Database[drop]
                        if r:
                            if (request.user in self.instance.conf["Admins"]) or (r[0][1] == request.user):
                                self.instance.Database.deleteDrop(drop)
                            else:
                                return self.generateError("400 Bad Request", etext="You don't have permission to delete this.")
                        else:
                            return self.generateError("400 Bad Request", etext="Nope")
                    except KeyError:
                        pass
                return Objects.Response(s="303 See Other", h={"Location": "/manage"}, r="")
            else:
                return Objects.Response(s="303 See Other", h={"Location": "/login"}, r="")
        else:
            return self.generateError("400 Bad Request", etext="You can't GET this page.")

    def listDrops(self, request):
        o = []
        if request.authenticated:
            if request.user in self.instance.conf["Admins"]:
                l = self.instance.Database.getAllDrops()
            else:
                l = self.instance.Database.getDropsByUser(request.user)
            akey = self.instance.Database.getUser(request.user)["apikey"]
            for dropstr in l:
                o.append(u"""\
<tr class="ms">
    <td class="cbc"><input class="ub-check" type="checkbox" name="del_{0[url]}"></td>
    <td><a href='/{0[url]}'>/{0[url]}</a></td>
    <td>{0[owner]}</td>
    <td>{0[name]}</td>
    <td>{0[type]}</td>
    <td>{time}</td>
    <td>{size}</td>
    <td>{0[views]}</td>
</tr>
                """.format(dropstr, time=time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(dropstr["timestamp"])), size=self.instance.func.file_size(dropstr["size"])))
            return Objects.Response(s="200 OK", h={"Cache-Control": "no-cache; max-age=0"}, r=self.instance.func.page_format(v={"DROPS": "".join(o), "APIKEY": akey}, template="manage.pyb"))
        else:
            return Objects.Response(s="303 See Other", h={"Location": "/login"}, r="")

    def loginUser(self, request):
        if request.post:
            for x in ["email", "password"]:
                if x not in request.form:
                    return self.generateError("400 Bad Request", etext="Login failed.", return_to="/login")
            user = self.instance.Database.getUser(request.form["email"].value.decode("utf-8"))
            if not user or (self.instance.func.hashPassword(request.form["password"].value.decode("utf-8"), salt=user["salt"])[0] != user["pass"]):
                return self.generateError("400 Bad Request", etext="Invalid username and/or password.", return_to="/login")
            elif self.instance.func.hashPassword(request.form["password"].value.decode("utf-8"), salt=user["salt"])[0] == user["pass"]:
                authToken = self.instance.func.genAuthToken(user, request.origin)
                return Objects.Response(s="303 See Other", h={"Set-Cookie": "pypAuthToken=" + authToken, "Location": "/"}, r="")
        else:
            return Objects.Response(s="200 OK", h={"Cache-Control": "no-cache; max-age=0"}, r=self.instance.func.page_format(v={}, template="login.pyb"))

    def registerUser(self, request):
        if request.post:
            if not request.authenticated:
                if not self.instance.conf["OpenRegistration"]:
                    return self.generateError("400 Bad Request", etext="Sorry, registration isn't currently open.", return_to="/")
                for field in ["email", "password", "password2"]:
                    if field not in request.form:
                        return self.generateError("400 Bad Request", etext="Please fill out the form.", return_to="/register")
                # Check fields
                em = request.form["email"].value.decode("utf-8").strip()
                pw = request.form["password"].value.decode("utf-8").strip()
                pw2 = request.form["password2"].value.decode("utf-8").strip()
                if len(em.split("@")) != 2 or len(em) >= 256 or "." not in em:
                    return self.generateError("400 Bad Request", etext="Invalid e-mail address.", return_to="/register")
                elif self.instance.Database.getUser(em):
                    return self.generateError("400 Bad Request", etext="This e-mail address has already been used.", return_to="/register")
                elif len(pw) <= 4:
                    return self.generateError("400 Bad Request", etext="Passwords must be 5 or more characters in length.", return_to="/register")
                elif pw != pw2:
                    return self.generateError("400 Bad Request", etext="Passwords didn't match.", return_to="/register")
                else:
                    self.instance.Database.addUser(em, pw)
                    return self.generateError("200 OK", heading="Success", etext="Your API key is: {0}".format(self.instance.Database.getUser(em)["apikey"]))
            else:
                return Objects.Response(s="303 See Other", h={"Location": "/"}, r="")
        else:
            return Objects.Response(s="200 OK", h={"Cache-Control": "no-cache; max-age=0"}, r=self.instance.func.page_format(v={}, template="register.pyb"))

    def doPost(self, request):
        if request.post:
            if "file" not in request.form:
                return self.generateError("400 Bad Request", etext="derp")
            # OK.
            if not request.form["file"].filename:
                return self.generateError("400 Bad Request", etext="Didn't upload anything.")
            else:
                if request.authenticated:
                    if len(request.form["file"].value) > self.instance.conf["MaxFileSize"]:
                        return self.generateError("400 Bad Request", etext="Your file is too large.", return_to="/upload")
                    mime = self.magic.from_buffer(request.form["file"].value)
                    table = {
                        "mimetype": mime,
                        "realname": request.form["file"].filename.decode("utf-8"),
                        "ts": int(math.floor(time.time())),
                        "email": request.user,
                        "size": len(request.form["file"].value)
                    }
                    if "long" in request.form and request.form["long"].value == "on":
                        a = self.instance.conf["LongDropURLLength"]
                    else:
                        a = self.instance.conf["DropURLLength"]
                    while True:
                        table["drop"] = self.instance.func.mkstring(a)
                        try:
                            self.instance.Database[table["drop"]]
                        except KeyError:
                            break
                    with open("{0}/{1}".format(self.instance.docroot, table["drop"]), "w+") as fi:
                        for x in self.instance.func.read_faster(request.form["file"].file, False):
                            fi.write(x)
                    self.instance.Database.insertFileRecord(table)
                    return self.generateError("200 OK", heading="Success", etext="<a href=\"{1}/{0}\">{1}/{0}</a>".format(table["drop"], self.instance.conf["SiteName"]))
                else:
                    return Objects.Response(s="303 See Other", h={"Location": "/login"}, r="")
        else:
            return Objects.Response(s="200 OK", h={"Cache-Control": "no-cache; max-age=0"}, r=self.instance.func.page_format(v={}, template="upload.pyb"))

    def serveFromFilesystem(self, request, override=None):
        Headers = {}
        if "/".join(request.url.split('/')[:-1]) in self.instance.conf["DirectoryBlacklist"] or ".." in request.url.split('/'):
            # Prevent people from accessing all files on the filesystem using relative paths
            return self.generateError('913 Nope', etext="Nope!");
        else:
            filepath = self.instance.docroot + "/" + request.url.lstrip("/")
            if override:
                filepath = override
            if os.path.isdir(filepath):
                filepath = filepath + "/index.html"
            if os.path.isfile(filepath):
                if os.access(filepath, os.R_OK):
                    if re.match(r"/([A-Za-z0-9])+$", request.url):
                        try:
                            dropdata = self.instance.Database[request.url.strip("/")]
                        except KeyError:
                            dropdata = None
                        if dropdata:
                            Headers["Content-Type"] = dropdata[0][3]
                            try:
                                dropdata[0][4].decode('ascii')
                                Headers["Content-Disposition"] = "inline; filename={0}".format(urllib.quote(dropdata[0][4].decode("ascii")))
                            except UnicodeEncodeError:
                                Headers["Content-Disposition"] = "inline; filename={0}".format(urllib.quote(dropdata[0][4].encode("utf-8")))
                            self.instance.Database.bumpViews(dropdata[0][0])
                    else:
                        Headers["Content-Type"] = mimetypes.guess_type(filepath, strict=True)[0] or "text/plain"
                    moddate = time.gmtime(os.path.getmtime(filepath))
                    if request.contains("If-Modified-Since") and not filepath.endswith('.html'):
                        sincets = time.mktime(rfc822.parsedate(request['If-Modified-Since']));
                        if sincets >= time.mktime(moddate):
                            return Objects.Response("304 Not Modified", Headers, "");
                    Headers["Last-Modified"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", moddate);
                    Headers["Content-Length"] = os.stat(filepath).st_size;
                    res = open(filepath, 'rb');
                    if request.url.endswith('.html'):
                        # don't cache html
                        Headers["Cache-Control"] = "no-cache";
                    return Objects.Response("200 OK", Headers, self.instance.func.read_faster(res));
                else:
                    return self.generateError('403 Forbidden', etext="You are not allowed to view this page.");
            else:
                return self.generateError('404 Not Found', etext="The requested page was not found on the server.");
    