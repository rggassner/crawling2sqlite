#!/usr/bin/python3
import json
import flask
import sqlite3
import networkx as nx
width=1920
height=1080
G = nx.Graph()
con = sqlite3.connect("crawler.db", timeout=60)
try:
    cur = con.cursor()
    random_url = cur.execute(
        "select host,parent_host from urls where host != '' and parent_host != '' "
    ).fetchall()
except sqlite3.OperationalError as e:
        print("Error:", e)
for url in random_url:
    G.add_edge(url[0], url[1])
for n in G:
    G.nodes[n]["name"] = n
d = nx.json_graph.node_link_data(G)  
json.dump(d, open("force/force.json", "w"))

def db_count_urls():
    cur = con.cursor()
    url_count = cur.execute("select count(url) from urls").fetchone()[0]
    con.commit()
    return url_count

def db_get_unique_domain_count():
    cur = con.cursor()
    unique_domain_count = cur.execute(
        "select count(distinct host) from urls"
    ).fetchone()[0]
    con.commit()
    return unique_domain_count

def db_get_visit_count():
    cur = con.cursor()
    visit_count = cur.execute(
        "select count(url) from urls where visited =1"
    ).fetchone()[0]
    con.commit()
    return visit_count

def db_get_email_count():
    cur = con.cursor()
    email_count = cur.execute("select count(distinct email) from emails").fetchone()[0]
    con.commit()
    return email_count

def db_get_content_type_count():
    cur = con.cursor()
    content_type_count = cur.execute(
        "select content_type,count(content_type) as total from urls group by content_type order by total desc limit 10"
    ).fetchall()
    con.commit()
    return content_type_count

def db_get_top_domain():
    cur = con.cursor()
    domain_count = cur.execute(
        "select host,count(host) as total from urls group by host order by total desc limit 10"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_porn_domains():
    cur = con.cursor()
    domain_count = cur.execute(
        "select a,ph,c from (select avg(isnsfw) as a,parent_host as ph,count(*) as c from urls where isnsfw != '' and resolution >= 224*224 group by parent_host ) where a > .3 and c > 4 order by a"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_porn_urls():
    cur = con.cursor()
    domain_count = cur.execute(
        "select isnsfw, url from urls where resolution >= 224*224 and isnsfw != '' order by isnsfw desc limit 10"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_open_dir():
    cur = con.cursor()
    domain_count = cur.execute(
        "select url from urls where isopendir='1'"
    ).fetchall()
    con.commit()
    return domain_count

f = open('force/force.html', 'w')
f.write('''\
    <!doctype html>
    <html>
      <head>
        <title>Force-Directed Layout</title>
        <script type="text/javascript" src="https://d3js.org/d3.v4.min.js"></script>
        <link type="text/css" rel="stylesheet" href="force/force.css" />
      </head>
      <body>
        <svg width="{}" height="{}"></svg>
        <script type="text/javascript" src="force/force.js"></script>
        <br>Total urls/visited: {}/{}<br>
        <br>Domain count: {}<br>
        Total emails: {}<br>
        Top Urls:<br>
        <table>'''.format(width,height,db_count_urls(),db_get_visit_count(),db_get_unique_domain_count(),db_get_email_count()))
for line in db_get_top_domain():
    f.write('<tr><td>{}</td><td>{}</td></tr>'.format(line[0],line[1]))
f.write('</table><br>Top Content-Type:<br><table>')
for line in db_get_content_type_count():
    f.write('<tr><td>{}</td><td>{}</td></tr>'.format(line[0],line[1]))
f.write('</table><br>Open directories:<br><table>')
for line in db_get_open_dir():
    f.write('<tr><td>{}</td></tr>'.format(line[0]))
f.write('</table><br>Top porn domains:<br><table>')
for line in db_get_porn_domains():
    f.write('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(line[0],line[1],line[2]))
f.write('</table><br>Top porn urls:<br><table>')
for line in db_get_porn_urls():
    f.write('<tr><td>{}</td><td><a href={}>{}</a></td></tr>'.format(line[0],line[1],line[1]))
f.write('''\
        </table>
      </body>
    </html>
    '''.format(width,height,db_count_urls()))
f.close()
app = flask.Flask(__name__, static_folder="force")
@app.route("/")
def static_proxy():
    return app.send_static_file("force.html")
print("\nGo to http://localhost:8000 to see the network diagram\n")
app.run(port=8000)
#https://networkx.org/documentation/stable/auto_examples/external/javascript_force.html#sphx-glr-download-auto-examples-external-javascript-force-py
