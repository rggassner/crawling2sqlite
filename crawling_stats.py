#!/usr/bin/python3
import json
import sqlite3
import os
import time
from tornado import concurrent, gen, httpserver, ioloop, log, web, iostream
from config import *
import concurrent.futures
import ssl, os
os.system("openssl req -nodes -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -subj '/CN=mylocalhost'")

def db_count_urls(con):
    cur = con.cursor()
    url_count = cur.execute("select count(url) from urls").fetchone()[0]
    con.commit()
    return url_count

def db_get_unique_domain_count(con):
    cur = con.cursor()
    unique_domain_count = cur.execute(
        "select count(distinct host) from urls"
    ).fetchone()[0]
    con.commit()
    return unique_domain_count

def db_get_visit_count(con):
    cur = con.cursor()
    visit_count = cur.execute(
        "select count(url) from urls where visited =1"
    ).fetchone()[0]
    con.commit()
    return visit_count

def db_get_email_count(con):
    cur = con.cursor()
    email_count = cur.execute("select count(distinct email) from emails").fetchone()[0]
    con.commit()
    return email_count

def db_get_content_type_count(con):
    cur = con.cursor()
    content_type_count = cur.execute(
        "select content_type,count(content_type) as total from urls group by content_type order by total desc limit 10"
    ).fetchall()
    con.commit()
    return content_type_count

def db_get_top_domain(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "select host,count(host) as total from urls group by host order by total desc limit 10"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_porn_domains(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "select a,ph,c from (select avg(isnsfw) as a,parent_host as ph,count(*) as c from urls where isnsfw != '' and resolution >= 224*224 group by parent_host ) where a > .3 and c > 4 order by a"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_porn_urls(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "select isnsfw, url from urls where resolution >= 224*224 and isnsfw != '' order by isnsfw desc limit 10"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_open_dir(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "select url from urls where isopendir='1'"
    ).fetchall()
    con.commit()
    return domain_count

def db_get_all_hosts(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "select distinct(combined_column) from (SELECT parent_host AS combined_column FROM urls where parent_host != '' UNION ALL SELECT host FROM urls where host != '') "
    ).fetchall()
    con.commit()
    return domain_count

def db_get_all_relations(con):
    cur = con.cursor()
    domain_count = cur.execute(
        "SELECT parent_host,host FROM urls where host !='' and parent_host != ''"
    ).fetchall()
    con.commit()
    return domain_count

def update_data():
    con = sqlite3.connect("crawler.db", timeout=60)
    network={}
    network['nodes']=[]
    network['links']=[]
    links=set()
    for host in db_get_all_hosts(con):
        group='.'+str(host[0])
        group=group.split('.')[-GROUP_DOMAIN_LEVEL]
        network['nodes'].append({'id':host[0],'group':group})
    for relation in db_get_all_relations(con):
        links.add(frozenset([relation[0],relation[1]]))
    for link in links:
        y=list(link)
        if len(y) == 2:
            network['links'].append({'source':y[0],'target':y[1],'value':1})
    with open('network.json', 'w') as f:
        json.dump(network, f)
    f = open('network.html', 'w')
    f.write('''\
            <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dynamic Force Graph</title>
  <style>
    body { margin: 0; }
  </style>
  <script src="//unpkg.com/force-graph"></script>
</head>
<body>
  <div id="graph"></div>
  <button id="toggleButton">Stop/Restart</button> <!-- Add a button -->
  <script>
    let savedNodePositions = {}; // Object to store node positions
    let intervalId; // Variable to store interval ID

    // Function to fetch JSON data and render graph
    function renderGraph() {
      fetch('network.json')
        .then(res => res.json())
        .then(data => {
          // Check if the graph is already initialized
          if (window.Graph) {
            // Save current node positions
            window.Graph.graphData().nodes.forEach(node => {
              savedNodePositions[node.id] = { x: node.x, y: node.y };
            });
            window.Graph.graphData(data);
            // Apply saved node positions
            window.Graph.graphData().nodes.forEach(node => {
              if (savedNodePositions[node.id]) {
                node.x = savedNodePositions[node.id].x;
                node.y = savedNodePositions[node.id].y;
              }
            });
            window.Graph.refresh(); // Refresh the graph to apply changes
          } else {
            window.Graph = ForceGraph()(document.getElementById('graph'))
              .graphData(data)
              .nodeId('id')
              .nodeVal('val')
              .nodeLabel('id')
              .nodeAutoColorBy('group')
              .linkSource('source')
              .linkTarget('target');
          }
        })
        .catch(error => {
          console.error('Error fetching JSON data:', error);
        });
    }

    // Initial render of the graph
    renderGraph();

    // Function to start checking for updates
    function startCheckingForUpdates() {
      intervalId = setInterval(() => {
        renderGraph();
      }, 5000); // Adjust the interval as needed (e.g., every 5 seconds)
    }

    // Start checking for updates
    startCheckingForUpdates();

    // Function to stop checking for updates
    function stopCheckingForUpdates() {
      clearInterval(intervalId);
    }

    // Event listener for the toggle button
    document.getElementById('toggleButton').addEventListener('click', function() {
      if (intervalId) {
        // If intervalId is set, stop checking for updates
        stopCheckingForUpdates();
        intervalId = null;
      } else {
        // If intervalId is not set, start checking for updates
        startCheckingForUpdates();
      }
    });
  </script>
    ''')
    f.write('''
    <br>Total urls/visited: {}/{}<br>
    <br>Domain count: {}<br>
    Total emails: {}<br>
    Top Urls:<br>
    <table>'''.format(db_count_urls(con),db_get_visit_count(con),db_get_unique_domain_count(con),db_get_email_count(con)))
    for line in db_get_top_domain(con):
        f.write('<tr><td>{}</td><td>{}</td></tr>'.format(line[0],line[1]))
    f.write('</table><br>Top Content-Type:<br><table>')
    for line in db_get_content_type_count(con):
        f.write('<tr><td>{}</td><td>{}</td></tr>'.format(line[0],line[1]))
    f.write('</table><br>Open directories:<br><table>')
    for line in db_get_open_dir(con):
        f.write('<tr><td>{}</td></tr>'.format(line[0]))
    f.write('</table><br>Top porn domains:<br><table>')
    for line in db_get_porn_domains(con):
        f.write('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(line[0],line[1],line[2]))
    f.write('</table><br>Top porn urls:<br><table>')
    for line in db_get_porn_urls(con):
        f.write('<tr><td>{}</td><td><a href={}>{}</a></td></tr>'.format(line[0],line[1],line[1]))
    f.write('''\
    </table>
    </body>
    </html>
    '''.format(db_count_urls(con)))
    f.close()

class MainHandler(web.RequestHandler):
    def get(self):
        with open("network.html", "r") as file:
            html_content = file.read()
        self.set_header("Content-Type", "text/html")
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")
        self.write(html_content)

def periodic_task():
    update_data()

def make_app():
    return web.Application([
        (r"/", MainHandler),
        (r"/network.html", web.StaticFileHandler, {"path": os.getcwd()}), 
        (r"/(.*)", web.StaticFileHandler, {"path": os.getcwd()})
    ],
    debug=False)

def main():
    app = make_app()
    periodic_callback = ioloop.PeriodicCallback(periodic_task, 5000)
    periodic_callback.start()
    server = httpserver.HTTPServer(app, ssl_options={
        "certfile": "cert.pem",  
        "keyfile": "key.pem", 
    })
    server.listen(EMBED_PORT)  # HTTPS default port
    ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
