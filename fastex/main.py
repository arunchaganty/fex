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

from bottle import Bottle, jinja2_view, redirect, request, static_file
from jinja2 import Template

logger = logging.getLogger(__name__)

def load_jsonl(fstream):
    if isinstance(fstream, str):
        with open(fstream) as fstream_:
            return load_jsonl(fstream_)

    return [json.loads(line) for line in fstream]

def save_jsonl(fstream, objs):
    if isinstance(fstream, str):
        with open(fstream, "w") as fstream_:
            save_jsonl(fstream_, objs)
        return

    for obj in objs:
        fstream.write(json.dumps(obj, sort_keys=True))
        fstream.write("\n")

def do_init(args):
    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    shutil.copy(template_path, args.template)

def serve(data, template=None, port=8080):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
    if not template or not os.path.exists(template):
        template = os.path.join(TEMPLATE_DIR, "template.html")

    # Start server.
    app = Bottle()
    @app.route('/view/')
    @jinja2_view('view.html', template_lookup=[TEMPLATE_DIR])
    def view():
        return {'data_len': len(data)}

    @app.route('/')
    @app.route('/label/')
    @jinja2_view('label.html', template_lookup=[TEMPLATE_DIR])
    def label():
        return {'data_len': len(data)}

    @app.route('/autocomplete/')
    def autocomplete():
        return json.dumps(["apples", "bananas"])

    @app.route('/count/')
    def count():
        return json.dumps(len(data))

    @app.route('/static/<path:path>')
    def static(path):
        return static_file(path, STATIC_DIR)

    @app.route('/_/<idx:int>')
    @jinja2_view(template)
    def render(idx=0):
        idx = int(idx)
        if idx > len(data):
            return redirect("/_/0")
        obj = data[idx]

        return {'obj': obj}

    #webbrowser.open_new_tab('http://localhost:{}'.format(port))
    app.run(reloader=True, port=port, debug=True)

def do_view(args):
    # 0. Find experiment dir.
    data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))
    serve(data, args.template, args.port)


def do_label(args):
    # 0. Find experiment dir.
    data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))
    serve(data, args.template, args.port)

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
    command_parser.add_argument('-i', '--input', type=argparse.FileType("r+"), default="data.jsonl", help="Data file with a list of JSON lines")
    command_parser.add_argument('-t', '--template', type=str, default="template.html", help="Template file to write")
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
