# dkfhfksdfkjsdh sdlkjhsdg dfjsdfsjdkg gs
# This code is copyright (c) 2011 - 2012 by the PyBoard Dev Team <stal@pyboard.net>
# All rights reserved.
import sqlite3
import threading
import hashlib
import os

if __name__ == '__main__':
    import sys
    sys.exit("Nope!")

class SQLiteBase(object):
    """Base class for DropDatabase."""
    def __init__(self, fn, PyBoard):
        self.instance = PyBoard
        self._db = sqlite3.connect(fn, check_same_thread=False)
        print(self.instance.lang["DB_CONNECTED"].format(fn=fn))
        self.dblock = threading.RLock()
        self.version = self.instance.conf["__version"]
        self.Functions = self.instance.func

    def runCustomQuery(self, query, arguments=None, requiresCommit=True, lock=False):
        """Wrapper for cursor.execute()."""
        if lock:
            self.dblock.acquire()
        try:
            c = self._db.cursor()
            if not arguments:
                c.execute(query)
            else:
                if isinstance(arguments, tuple):
                    c.execute(query, arguments)
                elif isinstance(arguments, list):
                    c.executemany(query, arguments)
            if requiresCommit:
                self._db.commit()
            op = c.fetchall()
            c.close()
            if lock:
                self.dblock.release()
            return op
        except:
            if lock:
                self.dblock.release()
            raise

class DropDatabase(SQLiteBase):
    """Database for drops and users."""
    def __init__(self, fn, PyBoard, **kwargs):
        SQLiteBase.__init__(self, fn, PyBoard)
        if "init" in kwargs and kwargs["init"]:
            self.setup_db()
            self.setup = True

    def __getitem__(self, item):
        try:
            s = self.runCustomQuery("SELECT * FROM files WHERE url=?", (item,), requiresCommit=False)
        except sqlite3.OperationalError:
            raise KeyError(item)
        if s:
            return s
        else:
            raise KeyError(item)

    def addUser(self, name, password):
        ph = hashlib.sha512(password).hexdigest()
        apikey = hashlib.md5(name+ph).hexdigest().upper()
        self.runCustomQuery("INSERT INTO users VALUES (NULL,?,?,?,0)", (name.strip(), ph, apikey), lock=True)

    def getUser(self, name=None, apikey=None):
        if apikey:
            s = self.runCustomQuery("SELECT * FROM users WHERE apikey=?", (apikey,), requiresCommit=False)
        elif name:
            s = self.runCustomQuery("SELECT * FROM users WHERE email=?", (name,), requiresCommit=False)
        else:
            return None
        if not s:
            return None
        else:
            return {
                "id": s[0][0],
                "email": s[0][1],
                "pass": s[0][2],
                "apikey": s[0][3],
                "usage": s[0][4]
            }

    def changeUserPassword(self, user, newPass):
        newHash = hashlib.sha512(newPass).hexdigest()
        apikey = hashlib.md5(user + newPass).hexdigest().upper()
        self.runCustomQuery("UPDATE users SET passwordHash=? WHERE email=?", (newHash, user), lock=True)
        self.runCustomQuery("UPDATE users SET apikey=? WHERE email=?", (apikey, user), lock=True)
        return user

    def getDrop(self, method, data):
        s = self.runCustomQuery("SELECT * FROM files WHERE ?=?", (method, data,), requiresCommit=False)
        if not s:
            return None
        else:
            return {
                "id": s[0][0],
                "owner": s[0][1],
                "url": s[0][2],
                "mimetype": s[0][3],
                "filename": s[0][4],
                "size": s[0][5],
                "views": s[0][6],
                "timestamp": s[0][7]
            }

    def getDropsByUser(self, userName, limit=-1, sort_by="id"):
        b = []
        s = self.runCustomQuery("SELECT * FROM files WHERE owner=? LIMIT ?", (userName, int(limit)), requiresCommit=False)
        if s:
            for d in s:
                b.append({
                    "id": d[0],
                    "owner": d[1],
                    "url": d[2],
                    "type": d[3],
                    "name": d[4],
                    "size": d[5],
                    "views": d[6],
                    "timestamp": d[7],
                })
            return sorted(b, key=lambda x: x[sort_by])
        else:
            return []

    def getAllDrops(self):
        b = []
        s = self.runCustomQuery("SELECT * FROM files", requiresCommit=False)
        if s:
            for d in s:
                b.append({
                    "id": d[0],
                    "owner": d[1],
                    "url": d[2],
                    "type": d[3],
                    "name": d[4],
                    "size": d[5],
                    "views": d[6],
                    "timestamp": d[7],
                })
            return sorted(b, key=lambda x: x["id"])
        else:
            return []

    def bumpViews(self, dropId):
        self.runCustomQuery("UPDATE files SET views=views+1 WHERE id=?", (int(dropId),), lock=True)
        return dropId

    def deleteDrop(self, drop):
        s = getDrop("url", drop)
        self.runCustomQuery("UPDATE users SET usage=usage-? WHERE email=?;", (s[0][5], s[0][1],), lock=True)
        self.runCustomQuery("DELETE FROM files WHERE url=?", (str(drop),), lock=True)
        try:
            os.remove("{0}/{1}".format(self.instance.docroot, drop))
        except OSError:
            pass
        return drop

    def insertFileRecord(self, table):
        self.runCustomQuery("INSERT INTO drops VALUES (NULL,?,?,?,?,?,0,?)",
            (table["email"], table["drop"], table["mimetype"],
            table["realname"], table["size"], table["ts"]), lock=True)

    def setup_db(self):
        self.runCustomQuery("CREATE TABLE files (id INTEGER PRIMARY KEY AUTOINCREMENT, "\
            "owner TEXT, url TEXT, mimetype TEXT, filename TEXT," \
            "size INTEGER, views INTEGER, timestamp INTEGER);", lock=True)
        self.runCustomQuery("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, "\
            "email TEXT, passwordHash TEXT, apikey TEXT, usage INTEGER);", lock=True)
