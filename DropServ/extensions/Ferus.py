import Objects
import re
import json
import time

class main(Objects.Extension):
    IDENTIFIER = "na.leijo.WhergCompatibility"
    def __init__(self, rootClass):
        Objects.Extension.__init__(self, rootClass)
        self.addPage("/api", self.info)
    
    def info(self, request):
        if re.match(r"^file\=[A-Za-z0-9]{4}$", request.query):
            dropname = re.findall(r"^file\=([A-Za-z0-9]{4})$", request.query)[0]
            try:
                db_data = self.instance.Database[dropname][0]
            except KeyError:
                return Objects.Response(s="404 Not Found", h={"Content-Type": "application/json"}, r="{}")
            js_data = {
                          "mimetype": db_data[3],
                          "filename": db_data[4],
                          "views": db_data[6],
                          "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(db_data[7])),
                      }
            return Objects.Response(s="200 OK", h={"Content-Type": "application/json"}, r=json.dumps(js_data))
        else:
            return self.generateError("400 Bad Request", etext="No query was made.")
