#!/usr/bin/python
from item import Item
import sqlite3 as lite

db_name = 'la.db'

instance = None
def db():
    global instance
    if instance is None:
        instance = ItemStore()
        instance.connect_db()
    return instance


class ItemStore(object):

    def __init__(self):
        self.con = None

    def __del__(self):
        print('Destroying ItemStore')
        if self.con:
            print('Closing SQL connection')
            self.con.close()

    def connect_db(self):
        try:
            self.con = lite.connect(db_name)
            cur = self.con.cursor()
            cur.execute('SELECT SQLITE_VERSION()')

            data = cur.fetchone()
            print("SQLite version: %s" % data)
        except lite.Error as e:
            print("Error %s:" % e.args[0])

    # The methods below assume the database is connected
    def create_item(self, item):
        cur = self.con.cursor()
        cur.execute("INSERT INTO items (url, type) VALUES ('%s', '%s') ;" % (item.url, item.typ))
        self.con.commit()
        return cur.lastrowid

    def select_all(self):
        cur = self.con.cursor()
        cur.execute('SELECT * FROM items ;')
        rows = cur.fetchall()
        result = list()
        for row in rows:
            print(row)
            result.append(Item(row[0], row[2], row[1]))
        return result


def initialize_db():
    con = db().con
    con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, url VARCHAR UNIQUE, type VARCHAR) ;")
    return 'database initialized'
