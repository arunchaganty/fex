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
from bottle import Bottle, jinja2_view, static_file
from jinja2 import Template

from .util import save_jsonl, load_jsonl, FileBackedJson, FileBackedJsonList

logger = logging.getLogger(__name__)

def prune_empty(lst):
    return [elem for elem in lst if elem]

def or_filter(fieldnames, fieldvalue):
    # print('filter {} {}'.format(fieldnames, fieldvalue))
    def check_field(elem, path, searchvalue):
        if len(path) == 0:
            if searchvalue == '*':
                if elem is not None:
                    return True
            elif str(elem) == searchvalue:
                return True
        else:
            fieldname = path.pop()
            if isinstance(elem, dict):
                elem_value = elem.get(fieldname)
                if elem_value is not None:
                    if isinstance(elem_value, list):
                        # check any of the values
                        for v in elem_value:
                          if check_field(v, path, searchvalue):
                            return True
                    else:
                        return check_field(elem_value, path, searchvalue)
        return False
    def f(elem):
        for fieldname in fieldnames:
            path = fieldname.split('.')
            path.reverse()
            if check_field(elem, path, fieldvalue):
                return True
    return f

def find_records(lst, query_str, text_fields=[]):
    conditions = query_str.split(' ')
    filters = []
    for condition in conditions:
        parts = condition.split(':')
        if len(parts) == 1:
            filters.append(or_filter(text_fields, parts[0]))
        elif len(parts) == 2:
            filters.append(or_filter([parts[0]], parts[1]))
        else:
            raise Exception('Invalid query string to find_records')
    def filter_record(elem):
        for f in filters:
            if not f(elem):
                return False
        return True
    return [(i,rec) for i,rec in enumerate(lst) if filter_record(rec)]

def find_record_indices(lst, query_str, text_fields=[]):
    return [i for i,rec in find_records(lst, query_str, text_fields)]

def serve(data, template=None, port=8080, schema=None, labels=[]):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
    if not template or not os.path.exists(template):
        template = os.path.join(TEMPLATE_DIR, "template.html")

    # Start server.
    app = Bottle()

    # Initialize labels.
    if len(labels) < len(data):
        labels.extend([{} for _ in range(len(data) - len(labels))])
    assert len(labels) == len(data)

    label_values = defaultdict(set)
    for obj in labels:
        for key, vs in obj.items():
            label_values[key].update(vs)

    @app.get('/view/')
    @jinja2_view('view.html', template_lookup=[TEMPLATE_DIR])
    def view():
        return {'data_len': len(data)}

    @app.get('/')
    @app.get('/label/')
    @jinja2_view('label.html', template_lookup=[TEMPLATE_DIR])
    def label():
        return {"schema": schema.obj}

    # API
    @app.get('/autocomplete/')
    def autocomplete():
        name = bottle.request.GET.get("name")

        bottle.response.content_type = 'application/json'
        ret = []
        if name in schema and schema[name].get("type") in ["multiclass", "multilabel"]:
            ret = sorted(schema[name]["values"])
        print(ret)
        return json.dumps(ret)

    @app.get('/count/')
    def count():
        bottle.response.content_type = 'application/json'
        return json.dumps(len(data))

    @app.post('/update/')
    def update():
        obj = bottle.request.json
        idx = obj["_idx"]

        update = {}
        for key, value in obj.items():
            if key.startswith("_"): continue
            if key not in schema: continue

            if schema[key].get("type") == "multilabel":
                vs = prune_empty(value)
                labels[idx][key] = vs
                schema[key]["values"] = sorted(set(schema[key]["values"] + vs))
            elif schema[key].get("type") == "multiclass":
                labels[idx][key] = value
                schema[key]["values"] = sorted(set(schema[key]["values"] + [value]))
            elif schema[key].get("type") == "text":
                labels[idx][key] = value
            else:
                raise ValueError("Not supported type.")
        labels.save()
        schema.save()

        bottle.response.content_type = 'application/json'
        return json.dumps(True)

    @app.get('/get/<idx:int>')
    def get(idx):
        assert idx >= 0 and idx < len(labels)

        bottle.response.content_type = 'application/json'
        return json.dumps(labels[idx])

    @app.get('/search/<query>')
    @app.post('/search/')
    def search(query=None):
        if query is None:
            query_obj = bottle.request.json
            query = query_obj.get('query')
        results = find_record_indices(data, query)
        bottle.response.content_type = 'application/json'
        return json.dumps(results)

    @app.get('/static/<path:path>')
    def static(path):
        return static_file(path, STATIC_DIR)

    @app.get('/_/<idx:int>')
    @jinja2_view(template)
    def render(idx=0):
        idx = int(idx)
        if idx > len(data):
            return bottle.redirect("/_/0")
        obj = data[idx]

        return {'obj': obj}

    #webbrowser.open_new_tab('http://localhost:{}'.format(port))
    app.run(reloader=True, port=port, debug=True)


def do_init(args):
    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    shutil.copy(template_path, args.template)


def do_view(args):
    # 0. Find experiment dir.
    data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))
    serve(data, args.template, args.port)


def do_label(args):
    # 0. Find experiment dir.
    with args.input:
        data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))

    labels = FileBackedJsonList(args.output)
    schema = FileBackedJson(args.schema)

    serve(data, args.template, args.port, schema, labels)

def do_save(args):
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
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.set_defaults(func=do_init)

    command_parser = subparsers.add_parser('view', help='View an experiment')
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-p', '--port', type=int, default=8080, help="Port to use")
    command_parser.set_defaults(func=do_view)

    command_parser = subparsers.add_parser('label', help='Label an experiment')
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-o', '--output', type=str, default="labels.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-s', '--schema', type=str, default="schema.json", help="Template file to write")
    command_parser.add_argument('-p', '--port', type=int, default=8080, help="Port to use")
    command_parser.set_defaults(func=do_label)


    command_parser = subparsers.add_parser('save', help='Saves the rendered pages')
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-o', '--output', type=str, default="rendered", help="Output directory containing the rendered HTML.")
    command_parser.set_defaults(func=do_save)


    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
