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

from bottle import Bottle, jinja2_view, redirect

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

def serve(data, template=None):
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "view.html")
    if not template or not os.path.exists(template):
        template = os.path.join(os.path.dirname(__file__), "template.html")

    # Start server.
    app = Bottle()
    @jinja2_view(TEMPLATE_PATH)
    def view():
        return {'data_len': len(data)}

    @jinja2_view(template)
    def render(idx=0):
        idx = int(idx)
        if idx > len(data):
            return redirect("/_/0")
        obj = data[idx]

        return {'obj': obj}

    app.route('/_/<idx:int>', 'GET', render)
    app.route('/', 'GET', view)
    webbrowser.open_new_tab('http://localhost:8080')
    app.run(reloader=True)

def do_view(args):
    # 0. Find experiment dir.
    data = load_jsonl(args.input)
    logger.info("Serving %d inputs ", len(data))
    serve(data, args.template)

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
    command_parser.set_defaults(func=do_view)

    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
