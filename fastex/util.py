"""
Common utilities for FastEx
"""
import os
import json
from io import StringIO


# region: io
from typing import List, TextIO, Union, TypeVar

T = TypeVar('T')


def load_jsonl(fstream: Union[TextIO, str]) -> List[dict]:
    """
    Parses a JSONL file into a list of objects.

    Args:
        fstream: a filename or `TextIO` handle.

    Returns:
        A list of objects parsed from the file
    """
    if isinstance(fstream, str):
        with open(fstream) as fstream_:
            return load_jsonl(fstream_)

    return [json.loads(line) for line in fstream]


def test_load_jsonl():
    fstream = StringIO("""
{"str": "a value", "int": 1, "bool": true}
{"str": "another value", "int": 2, "bool": false}
    """)
    ret = load_jsonl(fstream)
    assert ret == [
        {"str": "a value", "int": 1, "bool": True},
        {"str": "another value", "int": 2, "bool": False},
    ]


def save_jsonl(fstream, objs):
    if isinstance(fstream, str):
        with open(fstream, "w") as fstream_:
            save_jsonl(fstream_, objs)
        return

    for obj in objs:
        fstream.write(json.dumps(obj, sort_keys=True))
        fstream.write("\n")


def test_save_jsonl():
    fstream = StringIO()
    objs = [
        {"str": "a value", "int": 1, "bool": True},
        {"str": "another value", "int": 2, "bool": False},
    ]
    save_jsonl(fstream, objs)
    assert fstream.getvalue() == """
{"str": "a value", "int": 1, "bool": true}
{"str": "another value", "int": 2, "bool": false}
    """


class FileBackedJson:
    def __init__(self, fname):
        self.fname = fname
        self.reload()

    def save(self):
        with open(self.fname, "w") as f:
            json.dump(self.obj, f, indent=2)

    def reload(self):
        if os.path.exists(self.fname):
            with open(self.fname) as f:
                self.obj = json.load(f)
        else:
            self.obj = {}

    def get(self, key, default=None):
        return self.obj.get(key, default)

    def __getitem__(self, key):
        return self.obj[key]

    def __setitem__(self, key, value):
        self.obj[key] = value
        self.save()

    def __len__(self):
        return len(self.obj)

    def items(self):
        return self.obj.items()

    def keys(self):
        return self.obj.keys()

    def values(self):
        return self.obj.values()

    def __iter__(self):
        return iter(self.obj)


class FileBackedJsonList:
    def __init__(self, fname, auto_save=True):
        self.fname = fname
        self.reload()
        self.auto_save = auto_save

    def save(self):
        with open(self.fname, "w") as f:
            save_jsonl(f, self.objs)

    def reload(self):
        if os.path.exists(self.fname):
            with open(self.fname) as f:
                self.objs = load_jsonl(f)
        else:
            self.objs = []

    def __len__(self):
        return len(self.objs)

    def extend(self, iterables):
        self.objs.extend(iterables)
        if self.auto_save:
            self.save()

    def __getitem__(self, idx):
        return self.objs[idx]

    def __setitem__(self, idx, obj):
        self.objs[idx] = obj
        if self.auto_save:
            self.save()


def prune_empty(lst: List[T]) -> List[T]:
    """
    Prunes empty entries in a list of values.
    """
    return [elem for elem in lst if elem]
