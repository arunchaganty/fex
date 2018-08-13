#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turk experiment helper.
"""
import copy
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
from .search import find_record_indices

logger = logging.getLogger(__name__)

def prune_empty(lst):
    return [elem for elem in lst if elem]

def serve(data, template=None, port=8080, annotation_schema=None, labels=[], query_schema=None):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
    if not template or not os.path.exists(template):
        template = os.path.join(TEMPLATE_DIR, "template.html")

    # Do some processing with the annotation schema
    schema_metadata = annotation_schema.get('_schema_metadata_')
    basic_types = ["text", "multilabel", "multiclass", "record"]
    if schema_metadata is not None:
        schema_types = {t.get('name'):t for t in annotation_schema.get('types')}
        for f in annotation_schema.get('fields'):
            t = f.get('type')
            if t in basic_types and f['name'] not in schema_types:
                schema_types[f['name']] = f
        # print(json.dumps(schema_types, indent=4, separators=(',', ': ')))
        def convert_fields(fields):
            res = {}
            for f in fields:
                t = f.get('type')
                if t in basic_types:
                    # okay
                    if t == 'record':
                        f = copy.deepcopy(f)
                        f['fields'] = convert_fields(f.get('fields'))
                    res[f['name']] = f
                elif t in schema_types:
                    f = copy.deepcopy(f)
                    f['type'] = copy.deepcopy(schema_types[t])
                    if f['type'].get('type') == 'record':
                        f['type']['fields'] = convert_fields(f['type'].get('fields'))
                    res[f['name']] = f
                else:
                    logger.warning("Unsupported type {}".format(t))
            return res
        # print(json.dumps(schema_types, indent=4, separators=(',', ': ')))
        schema_fields = { f['name']: f for f in annotation_schema.get('fields') }
        schema_fields_expanded = convert_fields(copy.deepcopy(annotation_schema.get('fields')))
        # print(json.dumps(annotation_schema.obj, indent=4, separators=(',', ': ')))
    else:
        schema_types = annotation_schema.obj
        schema_fields = annotation_schema.obj
        schema_fields_expanded = annotation_schema.obj

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
        return {"schema": schema_fields_expanded}

    # API
    @app.get('/autocomplete/')
    def autocomplete():
        name = bottle.request.GET.get("name")

        bottle.response.content_type = 'application/json'
        ret = []
        if name in schema_types and schema_types[name].get("type") in ["multiclass", "multilabel"]:
            ret = sorted(schema_types[name]["values"])
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

        # print(json.dumps(obj, indent=4, separators=(',', ': ')))
        # basic_types = ["text", "multilabel", "multiclass", "record"]
        def update_field_values(value, field_type):
            if field_type.get("type") == "multilabel":
                vs = prune_empty(value)
                field_type["values"] = sorted(set(field_type["values"] + vs))
                return vs
            elif field_type.get("type") == "multiclass":
                field_type["values"] = sorted(set(field_type["values"] + [value]))
                return value
            elif field_type.get("type") == "text":
                return value
            elif field_type.get("type") == "record":
                output = {}
                process_record(value, output, field_type.get("fields"))
                return output
            else:
                raise ValueError("Not supported type {}.".format(field_type.get("type")))
        def process_record(input, output, known_fields):
            if isinstance(known_fields, list):
                known_fields = { f.get('name') : f for f in known_fields }
            for key, value in input.items():
                if key.startswith("_"): continue
                if key not in known_fields:
                    print('dropping {} not in known_fields {}'.format(key, known_fields))
                    continue

                field = known_fields[key]
                field_type_name = field.get("type")
                if isinstance(field_type_name, dict):
                    field_type = field_type_name
                else:
                    field_type = schema_types.get(field_type_name, field)
                # print('field type')
                # print(json.dumps(field_type, indent=4, separators=(',', ': ')))
                if field.get("repeated", False):
                    if  field.get("useMap", False):
                        output[key] = {}
                        for i,v in value.items():
                            output[key][i] = update_field_values(v, field_type)
                    else:
                        output[key] = []
                        for i,v in enumerate(value):
                            output[key][i] = update_field_values(v, field_type)
                else:
                    output[key] = update_field_values(value, field_type)
            return output

        process_record(obj, labels[idx], schema_fields)
        # print(json.dumps(schema_types, indent=4, separators=(',', ': ')))
        labels.save()
        annotation_schema.save()

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
        results = find_record_indices(data, query, query_schema)
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

    if args.query_schema:
        from .search import QuerySchema
        query_schema = QuerySchema(FileBackedJson(args.query_schema))
    else:
        query_schema = None

    serve(data, args.template, args.port, query_schema=query_schema)


def do_label(args):
    # 0. Find experiment dir.
    with args.input:
        data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))

    labels = FileBackedJsonList(args.output)
    schema = FileBackedJson(args.schema)

    if args.query_schema:
        from .search import QuerySchema
        query_schema = QuerySchema(FileBackedJson(args.query_schema))
    else:
        query_schema = None

    serve(data, args.template, args.port, schema, labels, query_schema=query_schema)

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
    command_parser.add_argument('-q', '--query_schema', type=str, help="Schema for querying")
    command_parser.set_defaults(func=do_view)

    command_parser = subparsers.add_parser('label', help='Label an experiment')
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-o', '--output', type=str, default="labels.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
    command_parser.add_argument('-s', '--schema', type=str, default="schema.json", help="Template file to write")
    command_parser.add_argument('-q', '--query_schema', type=str, help="Schema for querying")
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
