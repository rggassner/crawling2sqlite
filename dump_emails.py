#!venv/bin/python3
import sqlite3
import pymysql
from config import *

def get_db_connection():
    """Returns a connection to either SQLite or MariaDB."""
    if DATABASE == 'sqlite':
        return sqlite3.connect(SQLITE_FILE)
    elif DATABASE == 'mariadb':
        return pymysql.connect(
            host=MARIADB_HOST,
            user=MARIADB_USER,
            password=MARIADB_PASSWORD,
            database=MARIADB_DATABASE,
            cursorclass=pymysql.cursors.Cursor  # Standard cursor
        )
    else:
        raise ValueError("Unsupported database type")

def fetch_emails():
    """Fetches all emails from the database, working for both SQLite and MariaDB."""
    con = get_db_connection()
    cur = con.cursor()

    cur.execute('SELECT * FROM emails')

    for row in cur.fetchall():
        print(row)

    cur.close()
    con.close()


if __name__ == "__main__":
    fetch_emails()
