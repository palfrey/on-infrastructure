# Done as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/04-certificate-authority.md

import json
import pathlib

from network import external_ips, in_vagrant, ips, wireguard_ips
from utils import build_with_command, make_directory

ssl_folder = None

ssl_configs_folder = pathlib.Path("ssl")


def make_key():
    ca_key = ssl_folder.joinpath("ca.pem")
    build_with_command(
        ca_key,
        f"./cfssl gencert -initca {ssl_configs_folder.joinpath('ca-csr.json')} \
             | ./cfssljson -bare {ssl_folder.joinpath('ca')}",
    )

    KUBERNETES_HOSTNAMES = [
        "kubernetes",
        "kubernetes.default",
        "kubernetes.default.svc",
        "kubernetes.default.svc.cluster",
        "kubernetes.svc.cluster.local",
    ]

    names = [
        "admin",
        "kubernetes",
        "kube-controller-manager",
        "kube-proxy",
        "kube-scheduler",
        "service-account",
        "etcd",
        "cni",
    ]
    hostnames = (
        list(wireguard_ips().values())
        + ["10.32.0.1"]
        + list(external_ips().values())
        + KUBERNETES_HOSTNAMES
    )
    if in_vagrant():
        names += ["vagrant"]
        hostnames.append("127.0.0.1")
    else:
        names += ["external"]

    for name in names:
        pem = ssl_folder.joinpath(f"{name}.pem")
        # The Kubernetes API server is automatically assigned the kubernetes internal dns name,
        # which will be linked to the first IP address (10.32.0.1) from the address range (10.32.0.0/24)
        # reserved for internal cluster services during the control plane bootstrapping lab.
        # See https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/04-certificate-authority.md#the-kubernetes-api-server-certificate
        build_with_command(
            pem,
            f"""
            ./cfssl gencert -ca={str(ca_key)} \
            -ca-key={ssl_folder.joinpath('ca-key.pem')} \
            -config={ssl_configs_folder.joinpath('ca-config.json')} \
            -hostname={','.join(sorted(hostnames))} \
            -profile=kubernetes {ssl_configs_folder.joinpath(f'{name}-csr.json')} | \
            ./cfssljson -bare {ssl_folder.joinpath(name)}""",
        )


def make_node_key(host):
    csr = {
        "CN": f"system:node:{host['name']}",
        "key": {"algo": "rsa", "size": 2048},
        "names": [
            {
                "C": "UK",
                "L": "London",
                "O": "system:nodes",
            }
        ],
    }
    csr_file = ssl_folder.joinpath(f"generated-csr-{host['name']}.json")
    with csr_file.open("w") as f:
        json.dump(csr, f, indent=2)

    names = ips(host) + [host["name"]]
    if in_vagrant():
        names.append("127.0.0.1")
    node_key = ssl_folder.joinpath(f"keys-{host['name']}.pem")
    build_with_command(
        node_key,
        f"""
        ./cfssl gencert \
        -ca={ssl_folder.joinpath('ca.pem')} \
        -ca-key={ssl_folder.joinpath('ca-key.pem')} \
        -config={ssl_configs_folder.joinpath('ca-config.json')} \
        -hostname={','.join(names)} \
        -profile=kubernetes \
        {csr_file} | ./cfssljson -bare {ssl_folder.joinpath(f'keys-{host["name"]}')}""",
    )


def main(config):
    global ssl_folder
    ssl_folder = pathlib.Path(config["data_path"]).joinpath("ssl")
    if not ssl_folder.exists():
        make_directory(ssl_folder)
    make_key()
    for server in config["servers"]:
        make_node_key(server)
