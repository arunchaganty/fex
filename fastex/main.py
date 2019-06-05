#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turk experiment helper.
"""
import os
import sys
import pdb
import json
import shutil
import logging
from collections import defaultdict
import webbrowser

import bottle
from bottle import Bottle, jinja2_view, static_file, abort
from jinja2 import Template

from .util import save_jsonl, load_jsonl, FileBackedJson, FileBackedJsonList
from .search import find_record_indices

logger = logging.getLogger(__name__)


def prune_empty(lst):
    return [elem for elem in lst if elem]


def validate_annotation(schema, ann):
    for key, value in ann.items():
        if key not in schema["fields"]:
            abort(400, f"Invalid field provided {key}")
        # TODO: Further type validation.                


def serve(data, template=None, port=8080, schema=None):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
    if not template:
        template = os.path.join(TEMPLATE_DIR, "template.html")
    # Inititalize template
    with open(template) as f:
        template = Template(f.read())

    # Start server.
    app = Bottle()

    # External endpoints

    @app.get('/static/<path:path>')
    def static(path):
        return static_file(path, STATIC_DIR)

    @app.get('/view/')
    @app.get('/')
    @jinja2_view('view.html', template_lookup=[TEMPLATE_DIR])
    def view():
        return {}
    
    @app.get('/label/')
    @jinja2_view('label.html', template_lookup=[TEMPLATE_DIR])
    def label():
        return {}


    # API
    #@app.get('/autocomplete/')
    #def autocomplete():
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
        return schema.obj

    @app.get('/render/')
    def render():
        start = int(bottle.request.query.get("start", 0))
        count = int(bottle.request.query.get("count", 10))
        if start > len(data):
            abort(400, "No more data")
        return {
                "html": [template.render(obj=obj) for obj in data[start: start+count]],
                "obj": data[start: start+count],
                }

    @app.post('/update/<idx:int>/')
    def update(idx):
        obj = bottle.request.json

        # Some server-side validation
        for key in obj:
            if key == "_fex": continue
            if obj[key] != data[idx][key]:
                abort(400, "Provided response has an object that does not correspond to this idx")
        validate_annotation(schema, obj["_fex"])

        data[idx] = obj
        data.save()
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

    #webbrowser.open_new_tab('http://localhost:{}'.format(port))
    app.run(reloader=True, port=port, debug=True)


def do_init(args):
    for f in ["template.html", "config.yaml"]:
        shutil.copy(os.path.join(os.path.dirname(__file__), f), f)

def do_serve(args):
    # 0. Find experiment dir.
    data = FileBackedJsonList(args.input)
    # TODO: save a backup
    logger.info("Serving %d inputs ", len(data))
    schema = FileBackedJson(args.schema)

    serve(data, template=args.template, port=args.port, schema=schema)

def do_export(args):
    # 0. Find experiment dir.
    data = load_jsonl(args.input)
    logger.info("Saving %d inputs ", len(data))
    with open(args.template) as f:
        template = Template(f.read())

    if not os.path.exists(args.output):
        os.makedirs(args.output)
    elif not os.path.isdir(args.output):
        raise RuntimeError("Expected {} to be directory but it is not".format(args.output))

    for i, obj in enumerate(data):
        with open(os.path.join(args.output, "{}.html".format(i)), "w") as f:
            f.write(template.render(obj=obj))

def main():
    logging.basicConfig(level=logging.INFO)

    import argparse
    parser = argparse.ArgumentParser(description='tex.py: a tool to manage Amazon Mechanical Turk experiments')
    #parser.add_argument('-C', '--config', default='config.json', type=JsonFile("r"), help="Global configuration json file.")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('init', help='Initialize a new experiment of a particular type')
    command_parser.set_defaults(func=do_init)

    # TODO: make this the single default "run" entry point.
    command_parser = subparsers.add_parser('serve', help='Label an experiment')
    command_parser.add_argument('-i', '--input', type=str, default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-s', '--schema', type=str, default="schema.json", help="Template file to write")
    command_parser.add_argument('-p', '--port', type=int, default=8080, help="Port to use")
    command_parser.set_defaults(func=do_serve)


    command_parser = subparsers.add_parser('export', help='Saves the rendered pages')
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-o', '--output', type=str, default="rendered", help="Output directory containing the rendered HTML.")
    command_parser.set_defaults(func=do_export)


    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
