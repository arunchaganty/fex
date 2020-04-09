"""
The FastEx webserver
"""
import os
import webbrowser

import bottle
from bottle import Bottle, jinja2_view, static_file, abort
from fastex.config import Config
from fastex.util import FileBackedJsonList
from jinja2 import Template

#: The path to the fastex package directory
_mypath = os.path.dirname(__file__)
STATIC_DIR = os.path.join(_mypath, "static")
TEMPLATE_DIR = os.path.join(_mypath, "templates")


def serve(data: FileBackedJsonList, config: Config, port=8080):
    # Initializes a bottle server.
    app = Bottle()

    @app.get('/static/<path:path>')
    def static(path):
        return static_file(path, STATIC_DIR)

    @app.get('/view/')
    @app.get('/')
    @jinja2_view('view.html', template_lookup=[TEMPLATE_DIR])
    def view():
        return {"url": bottle.request.url}

    @app.get('/label/')
    @jinja2_view('label.html', template_lookup=[TEMPLATE_DIR])
    def label():
        return {"url": bottle.request.url}

    # API
    # @app.get('/autocomplete/')
    # def autocomplete():
    #    name = bottle.request.GET.get("name")

    #    bottle.response.content_type = 'application/json'
    #    ret = []
    #    if name in schema and schema[name].get("type") in ["multiclass", "multilabel"]:
    #        ret = sorted(schema[name]["values"])
    #    print(ret)
    #    return json.dumps(ret)
    @app.get('/count/')
    def count():
        return {"value": len(data)}

    @app.get('/schema/')
    def get_schema():
        if config.dirty:
            config.reload()
        return config.cfg.get("schema", {})

    @app.get('/render/')
    def render():
        if config.dirty:
            config.reload()

        start = int(bottle.request.query.get("start", 0))
        count_ = int(bottle.request.query.get("count", 10))
        if start > len(data):
            abort(400, "No more data")
        return {
            "html": [config.template.render(obj=obj) for obj in data[start: start + count_]],
            "obj": data[start: start + count_],
        }

    @app.post('/update/<idx:int>/')
    def update(idx):
        obj = bottle.request.json

        # Some server-side validation
        for key in obj:
            if key == "_fex":
                continue
            if obj[key] != data[idx][key]:
                abort(400, "Provided response has an object that does not correspond to this idx")

        data[idx] = obj
        return {}

    # TODO: reimplement search
    # @app.get('/search/<query>')
    # @app.post('/search/')
    # def search(query=None):
    #     if query is None:
    #         query_obj = bottle.request.json
    #         query = query_obj.get('query')
    #     results = find_record_indices(data, query, query_schema)
    #     bottle.response.content_type = 'application/json'
    #     return json.dumps(results)

    webbrowser.open_new_tab(f"http://localhost:{port}")
    app.run(reloader=False, port=port, debug=True)
    data.save()
