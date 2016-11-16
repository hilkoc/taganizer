#!/usr/bin/python
from item import Item
import sqlite3 as sqlite

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
            self.con = sqlite.connect(db_name)
            # Foreign keys are disabled by default, so we need to turn them on every time.
            self.con.cursor().execute("PRAGMA foreign_keys=ON")
        except sqlite.Error as e:
            print("Error %s:" % e.args[0])
            raise

    def dump_db(self, dump_file):
        """ dump_file is of type io.TextIOWrapper. """
        for line in self.con.iterdump():
            print(line)
            dump_file.write('%s\n' % line)
        return 'Database exported'

    # The methods below assume the database is connected
    def create_item(self, item):
        cur = self.con.cursor()
        cur.execute("INSERT INTO items (url, type) VALUES ('%s', '%s') ;" % (item.url, item.typ))
        self.con.commit()
        return cur.lastrowid

    def rename_item(self, old_name, new_name):
        cur = self.con.cursor()
        cur.execute("UPDATE items set url = :new_url WHERE items.url = :old_url ;" ,
            {'new_url': new_name, 'old_url': old_name})
        self.con.commit()
        return cur.rowcount

    def delete_item(self, name):
        cur = self.con.cursor()
        cur.execute("DELETE from items where url = :name ;", {'name': name})
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
        return 1

    def all_associations(self):
        cur = self.con.cursor()
        cur.execute('SELECT parent, child FROM associations ;')
        result = cur.fetchall()
        return result

    def select_all(self):
        cur = self.con.cursor()
        cur.execute('SELECT * FROM items ;')
        rows = cur.fetchall()
        result = dict()
        for row in rows:
            result[row[0]] = Item(row[0], row[2], row[1])
        return result

    def search(self, query):
        cur = self.con.cursor()
        # Get the associations.
        query_descendents = (
        "WITH RECURSIVE descendents(p, c, anc_url) AS ( "
        "  select parent, child, url from ASSOCIATIONS join items ON items.id = parent "
        "  where items.url IN (" + ", ".join(["?"] * len(query)) + " ) "
        " UNION ALL "
        "  SELECT parent, child, anc_url "
        "  FROM ASSOCIATIONS join descendents ON parent = c ) ")

        query_intersect = (" SELECT c as child from descendents as d"
        " WHERE d.anc_url = ? ")
        # query_pairs = query_descendents + " INTERSECT ".join([query_intersect] * len(query))
        # cur.execute(query_pairs, query*2)
        pairs_list = []  # cur.fetchall()
        query_matches = " INTERSECT ".join([query_intersect] * len(query))
        query_items = query_descendents + " , matched_ids as (" + query_matches + ") SELECT items.* FROM items JOIN matched_ids ON id = child ; "

        item_dict = dict()
        cur.execute(query_items, query * 2)
        rows = cur.fetchall()
        for row in rows:
            item_dict[row[0]] = Item(row[0], row[2], row[1])
        return item_dict, pairs_list

def initialize_db(db_instance):
    con = db_instance.con
    # con.execute("DROP TABLE items ;")
    # con.execute("DROP TABLE associations ;")
    con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, url VARCHAR UNIQUE, type VARCHAR) ;")
    con.execute("CREATE TABLE associations ( "
        "parent INTEGER REFERENCES items (id) ON DELETE CASCADE , "
        "child INTEGER REFERENCES items (id) ON DELETE CASCADE, "
        "PRIMARY KEY (parent, child) ) WITHOUT ROWID ; ")
    cr_trig_no_cycles = ("CREATE TRIGGER nocycles BEFORE INSERT ON associations"
        " BEGIN"
        " WITH RECURSIVE anc(x) AS ("
        "   SELECT NEW.parent"
        "   UNION ALL"
        "   SELECT parent FROM associations, anc WHERE child = x"
        " )"
        " SELECT RAISE(ABORT, \"Item is already a descendent\")"
        " FROM anc WHERE EXISTS ("
        " 	SELECT 1 FROM anc WHERE x = NEW.child"
        " );"
        " END;")
    con.execute(cr_trig_no_cycles)
    return 'database initialized'

#with p as (select id from items where url = 'A'), c as (select id from items where url = 'ab' ) INSERT INTO associations (parent, child) select p.id, c.id from p, c ;
