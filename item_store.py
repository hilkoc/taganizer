#!/usr/bin/python
from item import Item
import sqlite3 as lite

db_name = 'la.db'

instance = None
def db():
    global instance
    if instance is None:
        instance = ItemStore()
        instance.connect_db(db_name)
    return instance


class ItemStore(object):

    def __init__(self):
        self.con = None

    def __del__(self):
        if self.con:
            # print('Closing SQL connection')
            self.con.close()

    def connect_db(self, db_name):
        try:
            self.con = lite.connect(db_name)
        except lite.Error as e:
            print("Error %s:" % e.args[0])
            raise

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
        result = dict()
        for row in rows:
            # print(row)
            result[row[0]] = Item(row[0], row[2], row[1])
        return result

    def rename_item(self, old_name, new_name):
        cur = self.con.cursor()
        cur.execute("UPDATE items set url = :new_url WHERE items.url = :old_url ;" ,
            {'new_url': new_name, 'old_url': old_name})
        self.con.commit()
        return cur.rowcount

    # query = "with p as (select id from items where url = :purl), "
    #     "c as (select id from items where url = :curl ) select p.id, c.id from p, c ;"
    def associate(self, parent_name, child_name):
        insert_select = ("with p as (select id from items where url = :purl), "
        "c as (select id from items where url = :curl ) "
        "INSERT INTO associations (parent, child) select p.id, c.id from p, c ;")
        cur = self.con.cursor()
        cur.execute(insert_select, {'purl': parent_name, 'curl': child_name})
        self.con.commit()
        return cur.rowcount

    def all_associations(self):
        cur = self.con.cursor()
        cur.execute('SELECT parent, child FROM associations ;')
        result = cur.fetchall()
        print('rows type is ' + str(type(result)))
        return result


def initialize_db(db_instance):
    con = db_instance.con
    # con.execute("DROP TABLE items ;")
    # con.execute("DROP TABLE associations ;")
    con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, url VARCHAR UNIQUE, type VARCHAR) ;")
    con.execute("CREATE TABLE associations ( "
        "parent INTEGER REFERENCES items (id) ON DELETE CASCADE , "
        "child INTEGER REFERENCES items (id) ON DELETE CASCADE, "
        "PRIMARY KEY (parent, child) ) WITHOUT ROWID ; ")
    return 'database initialized'

#with p as (select id from items where url = 'A'), c as (select id from items where url = 'ab' ) INSERT INTO associations (parent, child) select p.id, c.id from p, c ;
