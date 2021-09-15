import pathlib
import shutil
import subprocess

import yaml
from helpers import rewrite_literal, rewrite_metadata

data = yaml.safe_load(open("helms.yaml"))


config_folder = pathlib.Path(".helm")
for (name, info) in data["deps"].items():
    print(name, info)
    short_name = info["chart"].split("/")[1]
    path = config_folder.joinpath(short_name)
    chart_path = path.joinpath("Chart.yaml")
    if chart_path.exists():
        chart = yaml.safe_load(open(chart_path))
        existing_version = chart["version"]
        if existing_version != info["version"]:
            print(f"Removing version {existing_version}")
            shutil.rmtree(path)
    else:
        existing_version = None
    if not path.exists():
        cmd = f"./helm pull {info['chart']} --untar --destination {config_folder} --version {info['version']}"
        print(cmd)
        subprocess.check_call(cmd.split(" "))

    external = pathlib.Path("external")

    cmd = f"./helm template --include-crds {short_name} {path}"
    if "namespace" in info:
        cmd += f" --namespace {info['namespace']}"
        ns = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": info["namespace"]},
        }
        yaml.dump(
            ns,
            open(
                external.joinpath("namespaces").joinpath(f"{info['namespace']}.yaml"),
                "w",
            ),
        )

    split_cmd = cmd.split(" ")
    if "values" in info:
        to_set = []
        for (k, v) in info["values"].items():
            # if isinstance(v, str):
            #     v = v.replace("\n", "\\n").strip()
            to_set.append(f"{k}={v}")
        split_cmd += ["--set", ",".join(to_set)]

    print(split_cmd)
    resources = subprocess.check_output(split_cmd)
    used_names = []
    root = external.joinpath(name)
    if not root.exists():
        root.mkdir()
    crds = external.joinpath("crds").joinpath(name)
    for document in yaml.safe_load_all(resources):
        if document is None:
            continue
        try:
            if document["kind"] == "CustomResourceDefinition":
                resource_name = document["metadata"]["name"]
                if not crds.exists():
                    crds.mkdir()
                resource_path = crds.joinpath(f"{resource_name}.yaml")
            else:
                resource_name = f"{document['metadata']['name']}-{document['kind']}"
                resource_path = root.joinpath(f"{resource_name}.yaml")
            assert resource_name not in used_names
        except (KeyError, AssertionError):
            print(document)
            raise
        if "namespace" in info:
            document = rewrite_metadata(document, info["namespace"])
        document = rewrite_literal(document)
        yaml.dump(document, open(resource_path, "w"), default_flow_style=False)
