#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast Explore.

Fastex (or fex) helps you quickly visualize and annotate structured data in
JSONL format. To get started, simply run:

    `fex view <file.jsonl>`

which will launch a local web-server to view each object in `<file.jsonl>`.

Customizing the visualization is easy: running `fex init` will install a local
'fex.yaml' file which contains a 'template' field that can be edited as
arbitrary HTML. By default, we import Bootstrap4 to style the page.

Finally, if you would like to label data, simply describe its schema in
`fex.yaml`.
"""
import logging
import os
import shutil
import sys

import yamale
from bottle import abort
from fastex.config import Config
from fastex.server import serve
from jinja2 import Template

from .util import load_jsonl, FileBackedJsonList

logger = logging.getLogger(__name__)

#: The path to the fastex package directory
_mypath = os.path.dirname(__file__)


def do_init(args):
    """
    Initialize a FastEx configuration

    This command will create a 'fex.yaml' file in the current directory that can be used to
    configure FastEx.
    """
    if os.path.exists("fex.yaml") and not args.force:
        logger.error("A 'fex.yaml' file already exists in this directory. Run 'fex init -f' "
                     "if you would like to overwrite it with the default file.")
        sys.exit(1)
    shutil.copy(os.path.join(_mypath, "templates", "fex.yaml"), "fex.yaml")
    logger.info("A fex configuration file has been copied to 'fex.yaml'. Edit it to change the "
                "template used to render objects and the annotation schema")


def do_serve(args):
    """
    Start the FastEx webserver
    """
    # 0. Find experiment dir.
    if os.path.exists("fex.yaml"):
        config = Config.load("fex.yaml")
    else:
        config = Config.load(os.path.join(_mypath, "templates", "fex.yaml"))

    data = FileBackedJsonList(args.input, auto_save=False)
    # TODO: save a backup
    logger.info("Serving %d inputs ", len(data))

    serve(data, config, port=args.port)


def do_export(args):
    """
    Renders the provided input to individual HTML files
    """
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
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--log-level', choices=["debug", "info", "warn", "error"], default="info",
                        help="The granularity of logs to report")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('init', help=do_init.__doc__)
    command_parser.add_argument('-f', '--force', action="store_true",
                                help="If set, this script will overwrite an existing fex.yaml")
    command_parser.set_defaults(func=do_init)

    command_parser = subparsers.add_parser('export', help=do_export.__doc__)
    command_parser.add_argument('-o', '--output', type=str, default="rendered",
                                help="Output directory to save the rendered HTML to.")
    command_parser.add_argument('input', type=str, help="Path to the data file in JSONL format")
    command_parser.set_defaults(func=do_export)

    command_parser = subparsers.add_parser('run', help=do_serve.__doc__)
    command_parser.add_argument('-p', '--port', type=int, default=8080, help="Port to use")
    command_parser.add_argument('input', type=str, help="Path to the data file in JSONL format")
    command_parser.set_defaults(func=do_serve)

    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        logging.basicConfig(level=args.log_level.upper())
        args.func(args)


if __name__ == "__main__":
    main()
