import json
import os
from threading import Lock


class PersistedDict:
    def __init__(self, path):
        self.path = path
        self.data = dict()
        self.lock = Lock()
        self.load()

    def __getitem__(self, item):
        with self.lock:
            return self.data[str(item)]

    def __setitem__(self, key, value):
        with self.lock:
            self.data[str(key)] = value

    def __iter__(self):
        return self.data.__iter__()

    def __contains__(self, item):
        with self.lock:
            return str(item) in self.data

    def __str__(self):
        return json.dumps(self.data)

    def __repr__(self):
        return self.data.__repr__()

    def __len__(self):
        return len(self.data)

    def load(self):
        if os.path.exists(self.path):
            with self.lock, open(self.path, 'r', encoding='utf8') as fin:
                self.data = json.load(fin)

    def keys(self):
        return self.data.keys()

    def save(self):
        with self.lock, open(self.path, 'w', encoding='utf8') as fout:
            json.dump(self.data, fout, ensure_ascii=False)
