#!/usr/bin/env python
import os
from json import dumps
from flask import Flask, g, Response, request

from neo4j.v1 import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')

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

@app.route("/search")
def get_data():
        return Response(dumps([serialize_movie(record['movie']) for record in results]),
                        mimetype="application/json")


def serialize_emp(emp):
    import pdb;pdb.set_trace()
    return {
        'id': emp['id'],
        'name': emp['name'],
        'native': emp['native'],
        'contact': emp['phone'],
        'team': emp['team']
    }


def serialize_employee_details(movie):
    return {
            'name': 'Prathika',
            'native':'Chennai',
            'contact': '9941222707' 
    }
    return {
        'id': movie['id'],
        'name': movie['name'],
        'native': movie['native'],
        'email': movie['mail_id'],
        'contact': movie['phone'],
        'mailing address': movie['address'],
        'employment type': movie['emp_type']
    }

def serialize_cast(cast):
    return {
        'name': cast[0],
        'job': cast[1],
        'role': cast[2]
    }

@app.route("/graph")
def get_emp_graph():
    db = get_db()
    results = db.run("MATCH (e:EmployeeDetails)<-[:WORKS_FOR]-(p:Project) "
             "RETURN m.name as name"
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
        query = "MATCH (n:EmployeeDetails) RETURN n LIMIT 25"
        #results = db.run("MATCH (movie:Movie) "
        #         "WHERE movie.title =~ {title} "
        #         "RETURN movie", {"title": "(?i).*" + q + ".*"}
        #)
        results = db.run(query)
        import pdb;pdb.set_trace()
        return Response(dumps([serialize_emp(record['n']) for record in results]),
                        mimetype="application/json")

@app.route("/search1")
def get_search1():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        db = get_db()
        results = db.run("MATCH (movie:Movie) "
                 "WHERE movie.title =~ {title} "
                 "RETURN movie", {"title": "(?i).*" + q + ".*"}
        )
        return Response(dumps([serialize_movie(record['movie']) for record in results]),
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
    app.run(host='0.0.0.0', port=8081)
