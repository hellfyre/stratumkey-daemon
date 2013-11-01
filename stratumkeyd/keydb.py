import sqlite3

class KeyDB:
    def __init__(self, dbfile):
        self.conn = sqlite3.connect(dbfile)
  
    def __del__(self):
        self.conn.close()

    def createTable(self):
        self.conn.execute("CREATE TABLE keys (key_id INTEGER PRIMARY KEY, key BLOB, last_used TEXT, active INTEGER);")

    def tableMissing(self):
        result = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='keys';").fetchall()
        return len(result) == 0

    def getKeyTuple(self, keyid):
        return self.conn.execute("SELECT key, last_used, active FROM keys WHERE key_id = ?", (keyid,)).fetchone()

    def addKey(self, keyid, key):
        try:
            with self.conn:
                self.conn.execute("INSERT INTO keys VALUES (?,?)", (keyid, key))
        except sqlite3.IntegrityError as e:
            print("Database error:", e)

    def close(self):
        self.conn.close()

# vim: set expandtab shiftwidth=4 tabstop=4:
