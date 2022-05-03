#!/usr/bin/python3
import sqlite3
con = sqlite3.connect('crawler.db')
cur = con.cursor()
for row in cur.execute('SELECT * FROM urls'):
    print("Database: {}".format(row))
    pass
con.close()
