import json
import pathlib

from utils import build_with_command, get_config, set_file_contents

root = pathlib.Path(__file__).parents[2]
kubectl = root.joinpath("kubectl")
calico_k8s = root.joinpath("k8s", "external", "calico")
ssl_configs_folder = pathlib.Path("ssl")


def kubectl_build(name, cmd, deps=[]):
    fname = calico_k8s.joinpath(f"{name}.yaml")
    build_with_command(
        fname, f"{cmd} --output=yaml --dry-run=client > {fname}", deps=deps
    )


def main():
    config = get_config()
    ssl_folder = pathlib.Path(config["data_path"]).joinpath("ssl")
    ca_pem = ssl_folder.joinpath("typha-ca.pem")
    ca_pem_key = ssl_folder.joinpath("typha-ca-key.pem")
    build_with_command(
        ca_pem,
        f"./cfssl gencert -initca {ssl_configs_folder.joinpath('ca-csr.json')} \
             | ./cfssljson -bare {ssl_folder.joinpath('typha-ca')}",
    )

    kubectl_build(
        "calico-typha-ca-ConfigMap",
        f"{kubectl} create configmap -n kube-system calico-typha-ca --from-file={ca_pem}",
        deps=[ca_pem],
    )

    csr = {
        "CN": "calico-typha",
        "key": {"algo": "rsa", "size": 2048},
        "names": [
            {
                "C": "UK",
                "L": "London",
                "O": "App",
            }
        ],
    }
    csr_file = ssl_folder.joinpath("typha-csr.json")
    set_file_contents(csr_file, json.dumps(csr, indent=2))

    typha_pem = ssl_folder.joinpath("typha.pem")
    typha_key_pem = ssl_folder.joinpath("typha-key.pem")
    ca_config = ssl_configs_folder.joinpath("ca-config.json")
    build_with_command(
        typha_pem,
        f"""
        ./cfssl gencert \
        -ca={ca_pem} \
        -ca-key={ca_pem_key} \
        -config={ca_config} \
        -profile=kubernetes \
        {csr_file} | ./cfssljson -bare {ssl_folder.joinpath('typha')}""",
        deps=[ca_config, ca_pem, ca_pem_key, csr_file],
    )

    kubectl_build(
        "calico-typha-certs-Secret",
        f"{kubectl} create secret generic -n kube-system calico-typha-certs --from-file={typha_pem} --from-file={typha_key_pem}",
        deps=[typha_pem, typha_key_pem],
    )

    csr = {
        "CN": "calico-node",
        "key": {"algo": "rsa", "size": 2048},
        "names": [
            {
                "C": "UK",
                "L": "London",
                "O": "system:nodes",
            }
        ],
    }
    csr_file = ssl_folder.joinpath("calico-node-csr.json")
    set_file_contents(csr_file, json.dumps(csr, indent=2))

    node_pem = ssl_folder.joinpath("calico-node.pem")
    node_key_pem = ssl_folder.joinpath("calico-node-key.pem")
    build_with_command(
        node_pem,
        f"""
        ./cfssl gencert \
        -ca={ca_pem} \
        -ca-key={ca_pem_key} \
        -config={ca_config} \
        -profile=kubernetes \
        {csr_file} | ./cfssljson -bare {ssl_folder.joinpath('calico-node')}""",
        deps=[ca_config, ca_pem, csr_file],
    )

    kubectl_build(
        "calico-node-certs-Secret",
        f"{kubectl} create secret generic -n kube-system calico-node-certs --from-file={node_pem} --from-file={node_key_pem}",
        deps=[node_pem, node_key_pem],
    )

    kubectl_build(
        "calico-typha-ServiceAccount",
        f"{kubectl} create serviceaccount -n kube-system calico-typha",
    )

    kubectl_build(
        "calico-node-ServiceAccount",
        f"{kubectl} create serviceaccount -n kube-system calico-node",
    )

    kubectl_build(
        "calico-typha-ClusterRoleBinding",
        f"{kubectl} create clusterrolebinding calico-typha --clusterrole=calico-typha --serviceaccount=kube-system:calico-typha",
    )

    kubectl_build(
        "calico-node-ClusterRoleBinding",
        f"{kubectl} create clusterrolebinding calico-node --clusterrole=calico-node --serviceaccount=kube-system:calico-node",
    )
