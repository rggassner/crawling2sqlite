#!venv/bin/python3
import sqlite3
con = sqlite3.connect('crawler.db')
cur = con.cursor()
for row in cur.execute('SELECT * from emails'):
    print("{}".format(row))
con.close()
