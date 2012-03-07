# jsdfsd dsgjsdbg sdffas
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
from __future__ import division
import time
import hashlib
import string
import random
import threading
import math
from collections import deque
allchars = "abcdefghijklmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ123456789"

class Functions(object):
    """
    Documentation is for losers
    """
    def __init__(self, PyBoard):
        self.instance = PyBoard
        self.TemplateCache = deque()
        self.TemplateConstants = {
            "VERSION": self.instance.conf["__version"],
            "STATIC": self.instance.conf["StaticDomain"].strip("/") or "/static",
        }
        self.file_locks = {};
        print(self.instance.lang["FUNC_LOADED"])

    def file_size(self, num):
        kb = num / 1024
        if kb > 1000:
            mb = kb / 1024
            return "{:03.2f} MB".format(mb)
        else:
            return "{:03.2f} KB".format(kb)

    def genAuthToken(self, user, origin):
        while True:
            sid = self.mkstring(5)
            if sid not in self.instance.Sessions:
                break
        times = int(math.floor(time.time()))
        token = hashlib.sha1(user["email"] + origin + self.instance.conf["LoginSalt"] + str(times)).hexdigest()
        self.instance.Sessions[sid] = (user["email"], times)
        for x, v in self.instance.Sessions.items():
            if times - v[1] >= 86400:
                del self.instance.Sessions[x]
        return "|".join([sid, token])

    def mkstring(self, length):
        s = ""
        for x in range(length):
            if x == 2:
                s += "l"
            else:
                s += random.choice(allchars)
        return s

    def page_format(self, v={}, template=None, TemplateString=""):
        """Format pages (obv)"""
        temp = None
        if template is not None:
            if len(self.TemplateCache) >= 5:
                print("Removed template: {0} from cache.".format(self.TemplateCache.popleft()[0]));
            for item in self.TemplateCache:
                if item[0] == template:
                    temp = string.Template(item[1]);
                    break;
            if not temp:
                if template not in self.file_locks:
                    self.file_locks[template] = threading.RLock();
                self.file_locks[template].acquire();
                try:
                    with open(self.instance.workd + "/templates/{0}".format(template), "r") as plate:
                        temp = plate.read();
                        self.TemplateCache.append((template, temp, time.time()));
                        print("Cached template: {0}".format(template));
                        temp = string.Template(temp);
                    self.file_locks[template].release();    
                except IOError:
                    if template in self.file_locks:
                        self.file_locks[template].release();
                        del self.file_locks[template];
                    return "";
        elif TemplateString != "":
            temp = string.Template(TemplateString);
        else:
            return "";
        for x in v:
            if isinstance(v[x], basestring):
                try:
                    v[x] = v[x].decode("utf-8")
                except:
                    pass
        formatted = temp.safe_substitute(dict(self.TemplateConstants.items() + self.instance.lang.getDict.items() + v.items()));
        return formatted.encode("utf-8");

    def read_faster(self, file, close=True):
        while True:
            c = file.read(16*4096)
            if c:
                yield c
            else:
                break
        if close:
            file.close()
        return

    def verifyLogin(self, crumb, origin):
        pair = crumb.split('|')
        if pair[0] not in self.instance.Sessions:
            return None
        elif hashlib.sha1(self.instance.Sessions[pair[0]][0] + origin + self.instance.conf["LoginSalt"] + str(self.instance.Sessions[pair[0]][1])).hexdigest() == pair[1]:
            return True
        else:
            return None
