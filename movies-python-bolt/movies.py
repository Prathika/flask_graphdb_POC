#!/usr/bin/env python
import os
from json import dumps
from flask import Flask, g, Response, request
from flask_cors import CORS
from neo4j.v1 import GraphDatabase, basic_auth


app = Flask(__name__, static_url_path='/static/')
CORS(app)
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver('bolt://localhost',auth=basic_auth("neo4j", password))

def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()

@app.route("/")
def get_index():
    return app.send_static_file('emp_index.html')

def serialize_movie(movie):
    return {
        'id': movie['id'],
        'title': movie['title'],
        'summary': movie['summary'],
        'released': movie['released'],
        'duration': movie['duration'],
        'rated': movie['rated'],
        'tagline': movie['tagline']
    }

def serialize_emp(emp):
    return {
        'id': emp['id'],
        'name': emp['name'],
        'native': emp['native'],
        'contact': emp['phone'],
        'team': emp['team']
    }

def serialize_cast(cast):
    return {
        'name': cast[0],
        'job': cast[1],
        'role': cast[2]
    }

@app.route("/graph")
def get_graph():
    db = get_db()
    results = db.run("MATCH (m:Movie)<-[:ACTED_IN]-(a:Person) "
             "RETURN m.title as movie, collect(a.name) as cast "
             "LIMIT {limit}", {"limit": request.args.get("limit", 100)})
    nodes = []
    rels = []
    i = 0
    for record in results:
        nodes.append({"title": record["movie"], "label": "movie"})
        target = i
        i += 1
        for name in record['cast']:
            actor = {"title": name, "label": "actor"}
            try:
                source = nodes.index(actor)
            except ValueError:
                nodes.append(actor)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    #resp = Response(js, status=200, mimetype='application/json')
    #resp.headers['Link'] = 'http://luisrei.com'
    return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")


@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        db = get_db()
        query = "MATCH p=()-[r:PART_OF]->() RETURN p LIMIT 25"
        #query = "MATCH p=()-[r:EXPERTISE_AT]->() RETURN p LIMIT 25"
        #query = "MATCH (n:EmployeeDetails) RETURN n LIMIT 25"
        #results = db.run("MATCH (movie:Movie) "
        #         "WHERE movie.title =~ {title} "
        #         "RETURN movie", {"title": "(?i).*" + q + ".*"}
        #)
        results = db.run(query)
        return Response(dumps([serialize_emp(record['n']) for record in results]),
                        mimetype="application/json")


@app.route("/movie/<title>")
def get_movie(title):
    db = get_db()
    results = db.run("MATCH (movie:Movie {title:{title}}) "
             "OPTIONAL MATCH (movie)<-[r]-(person:Person) "
             "RETURN movie.title as title,"
             "collect([person.name, "
             "         head(split(lower(type(r)), '_')), r.roles]) as cast "
             "LIMIT 1", {"title": title})

    result = results.single();
    return Response(dumps({"title": result['title'],
                           "cast": [serialize_cast(member)
                                    for member in result['cast']]}),
                    mimetype="application/json")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
