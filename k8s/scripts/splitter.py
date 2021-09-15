import os
import os.path
import sys

import yaml
from helpers import rewrite_literal

used_names = []


def split(document):
    if document is None:
        return
    if document["kind"] == "List":
        for item in document["items"]:
            for doc in split(item):
                yield doc
        return
    try:
        name = f"{document['metadata']['name']}-{document['kind']}"
        global used_names
        assert name not in used_names
        used_names.append(name)
    except (KeyError, AssertionError):
        print(document)
        raise
    document = rewrite_literal(document)
    yield (f"{name}.yaml", document)


def split_list(input, folder, fname):
    count = 0
    for document in yaml.load_all(input, Loader=yaml.SafeLoader):
        for newname, newdoc in split(document):
            newname = os.path.join(folder, newname)
            if newname != fname:
                count += 1
                print(newname)
                yaml.dump(newdoc, open(newname, "w"))

    return count


if __name__ == "__main___":
    for fname in sys.argv[1:]:
        used_names = []
        fname = os.path.abspath(fname)
        folder = os.path.dirname(fname)
        count = split_list(open(fname))
        if count == 1:
            os.unlink(fname)
