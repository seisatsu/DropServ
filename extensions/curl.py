import Objects
import re
import json
import time
import magic

class main(Objects.Extension):
    IDENTIFIER = "na.leijo.SuperSimpleAPI"
    def __init__(self, rootClass):
        Objects.Extension.__init__(self, rootClass)
        self.magic = magic.Magic(mime=True)
        self.addPage("/up", self.simpleUpload)

    def simpleUpload(self, request):
        if not request.post:
            return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="must be post")
        else:
            for i in ["k", "u", "f"]:
                if i not in request.form:
                    return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="invalid request\n")
            udata = self.instance.Database.getUser(request.form["u"].value.decode("utf-8"))
            if not udata or request.form["k"].value.decode("utf-8") != udata["apikey"]:
                return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="auth failed\n")
            if not request.form["f"].filename:
                return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="no file\n")
            request.form["f"].file.seek(0, 2)
            fsize = request.form["f"].file.tell()
            request.form["f"].file.seek(0, 0)
            if fsize > self.instance.conf["MaxFileSize"]:
                return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="file too large\n")
            mime = self.magic.from_buffer(request.form["f"].file.read(1024))
            request.form["f"].file.seek(0, 0)
            table = {
                "mimetype": mime,
                "realname": request.form["f"].filename.decode("utf-8"),
                "ts": int(time.time()),
                "email": request.form["u"].value.decode("utf-8"),
                "size": fsize
            }
            if "l" in request.form and request.form["l"].value.isdigit():
                a = self.instance.conf["LongDropURLLength"]
            else:
                a = self.instance.conf["DropURLLength"]
            success = 0
            for x in xrange(100):
                table["drop"] = self.instance.func.mkstring(a)
                try:
                    self.instance.Database[table["drop"]]
                except KeyError:
                    success = 1
                    break
            if not success:
                return Objects.Response(s="400 Bad Request", h={"Content-Type": "text/plain"}, r="error\n")
            with open("{0}/{1}".format(self.instance.docroot, table["drop"]), "w+") as fi:
                for x in self.instance.func.read_faster(request.form["f"].file, False):
                    fi.write(x)
            self.instance.Database.insertFileRecord(table)
            return Objects.Response(s="201 Created", h={"Content-Type": "text/plain"}, r="{1}/{0}\n".format(table["drop"], self.instance.conf["SiteName"]))
