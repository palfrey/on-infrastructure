# Rewrites nulls. See https://stackoverflow.com/a/41786451
from typing import Any

import yaml


def represent_none(self, _):
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)


# Literal dumper from https://stackoverflow.com/a/7445560
class literal_unicode(str):
    pass


def literal_unicode_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(literal_unicode, literal_unicode_representer)


def rewrite_literal(root: Any):
    if type(root) == str and root.find("\n") != -1:
        return literal_unicode(root)
    elif type(root) == dict:
        for k, v in root.items():
            root[k] = rewrite_literal(v)
    elif type(root) == list:
        return [rewrite_literal(item) for item in root]
    elif type(root) in [str, int, bool, type(None)]:
        pass
    else:
        raise Exception(type(root))
    return root


def rewrite_metadata(root: Any, namespace: str):
    if type(root) == dict:
        # Exit early so we don't try to rewrite the schema
        if "openAPIV3Schema" in root:
            return root
        if root.get("kind") in ["ClusterRoleBinding"]:
            return root
        if "spec" in root or root.get("kind") in [
            "ConfigMap",
            "ServiceAccount",
            "Role",
            "RoleBinding",
        ]:
            if root.get("kind") != "CustomResourceDefinition":
                if "metadata" not in root:
                    root["metadata"] = {}
                root["metadata"]["namespace"] = namespace
        for k, v in root.items():
            if k in ["roleRef", "subjects"]:
                continue
            root[k] = rewrite_metadata(v, namespace)
    elif type(root) == list:
        return [rewrite_metadata(item, namespace) for item in root]
    elif type(root) in [str, int, bool, type(None)]:
        pass
    else:
        raise Exception(type(root))
    return root
