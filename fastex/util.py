import os
import json

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

class FileBackedJson():
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

    def __getitem__(self, key):
        return self.obj[key]

    def __setitem__(self, key, value):
        self.obj[key] = value
        self.save()

    def __len__(self):
        return len(self.obj)

    def items():
        return self.obj.items()

    def keys():
        return self.obj.keys()

    def values():
        return self.obj.values()

    def __iter__(self):
        return iter(self.obj)

class FileBackedJsonList():
    def __init__(self, fname):
        self.fname = fname
        self.reload()

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
        self.save()

    def __getitem__(self, idx):
        return self.objs[idx]
