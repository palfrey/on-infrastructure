import argparse
import os
import pathlib
import subprocess

from splitter import split_list


def exec(cmd):
    print(cmd)
    return subprocess.check_output(cmd.split(" "))


def all_files(folder, calico=False):
    ret = []
    for root, folders, files in os.walk(folder):
        for f in list(folders):
            if f.startswith("."):
                folders.remove(f)
        r = pathlib.Path(root)
        ret += [
            str(r.joinpath(f))
            for f in files
            if f.endswith(".yaml")
            and f not in ["repositories.yaml", "helms.yaml"]
            and (calico or not f.endswith("-IPPool.yaml"))
        ]
    return ret


def update_kubectl(folder, apply):
    try:
        exec(f"kubectl diff -f {folder} --warnings-as-errors")
        return
    except subprocess.CalledProcessError:
        # At least one file in this folder had a diff, so lets find that
        pass
    files = all_files(folder)
    changes = False
    for file in files:
        default_args = f"-f {file}"
        try:
            exec(f"kubectl diff {default_args} --warnings-as-errors")
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                print(e.output.decode("utf-8"))
                exec(f"kubectl apply {default_args} --dry-run=client")
                if apply:
                    exec(f"kubectl apply {default_args}")
                changes = True
            else:
                raise

    return changes


parser = argparse.ArgumentParser()
parser.add_argument("--apply", type=int, default=0)
parser.add_argument("--env", type=str, required=True)
args = parser.parse_args()

groups = [
    ["rbac", "external/namespaces", "external/crds"],
    ["external/calico"],
    None,
    ["external/coredns"],
    ["external/longhorn"],
    [
        "external/rabbitmq",
        "external/cockroachdb",
        "external/prometheus",
        "external/nginx",
    ],
    ["repo", "portal", "app"],
]
apply = args.apply
kustomize = pathlib.Path(__file__).parent.parent.joinpath("kustomize")
for group in groups:
    changes = False

    if group is None:
        count = 0
        for conf in all_files("external/calico-config", calico=True):
            exec(f"./calicoctl apply -f {conf}")
            count += 1
        assert count > 0
    else:
        for folder in group:
            root = pathlib.Path(folder)
            overlays_path = root.joinpath("overlays")
            if overlays_path.exists():
                generate_path = root.joinpath("generated")
                if not generate_path.exists():
                    generate_path.mkdir()
                data = subprocess.check_output(
                    [kustomize, "build", overlays_path.joinpath(args.env).absolute()]
                )
                count = split_list(data, generate_path, None)
                assert count > 0
                changes = update_kubectl(generate_path, apply > 0) or changes
            else:
                changes = update_kubectl(folder, apply > 0) or changes

    if changes:
        if apply == 0:
            break
        apply -= 1
