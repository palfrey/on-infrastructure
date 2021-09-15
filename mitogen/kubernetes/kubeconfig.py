# Done as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/05-kubernetes-configuration-files.md

import json
import pathlib

from network import external_ips, in_vagrant, wireguard_ips
from utils import run_command, set_file_contents

kc_folder = None
ssl_folder = None
ssl_config_folder = pathlib.Path("./ssl/")

ca_pem = None

kubectl = pathlib.Path(__file__).parents[2].joinpath("kubectl")


def make_configs(public_address):
    for name in [
        "admin",
        "kube-controller-manager",
        "kube-proxy",
        "kube-scheduler",
        "service-account",
        "cni",
    ]:
        make_config(name, public_address)


def make_config(name, public_address):
    kc = kc_folder.joinpath(f"{name}.kubeconfig")
    cert = ssl_folder.joinpath(f"{name}.pem")
    key = ssl_folder.joinpath(f"{name}-key.pem")
    newest_dep = sorted([x.stat().st_mtime for x in [ca_pem, cert, key]], reverse=True)[
        0
    ]
    if kc.exists() and newest_dep < kc.stat().st_mtime:
        return
    run_command(
        f"""
{kubectl} config set-cluster app \
    --certificate-authority={ca_pem} \
    --embed-certs=true \
    --server=https://{public_address}:6443 \
    --kubeconfig={kc}""",
    )

    run_command(
        f"""
    {kubectl} config set-credentials system:{name} \
        --client-certificate={cert} \
        --client-key={key} \
        --embed-certs=true \
        --kubeconfig={kc}""",
    )

    run_command(
        f"""
    {kubectl} config set-context default \
        --cluster=app \
        --user=system:{name} \
        --kubeconfig={kc}""",
    )

    run_command(f"""{kubectl} config use-context default --kubeconfig={kc}""")

    run_command(f"touch {kc}")


def make_node_config(host, public_address):
    kc = kc_folder.joinpath(f"{host['name']}.kubeconfig")
    kc_config = str(kc) + ".config"
    cert = ssl_folder.joinpath(f"keys-{host['name']}.pem")
    key = ssl_folder.joinpath(f"keys-{host['name']}-key.pem")

    newest_dep = sorted([x.stat().st_mtime for x in [ca_pem, cert, key]], reverse=True)[
        0
    ]
    changed = set_file_contents(kc_config, json.dumps({"address": public_address}))
    if (not changed) and kc.exists() and newest_dep < kc.stat().st_mtime:
        return

    run_command(
        f"""
  {kubectl} config set-cluster app \
    --certificate-authority={ca_pem} \
    --embed-certs=true \
    --server=https://{public_address}:6443 \
    --kubeconfig={kc}""",
    )

    run_command(
        f"""
  {kubectl} config set-credentials system:node:{host['name']} \
    --client-certificate={cert} \
    --client-key={key} \
    --embed-certs=true \
    --kubeconfig={kc}""",
    )

    run_command(
        f"""
    {kubectl} config set-context default \
        --cluster=app \
        --user=system:node:{host['name']} \
        --kubeconfig={kc}""",
    )

    run_command(
        f"""{kubectl} config use-context default --kubeconfig={kc}""",
    )

    run_command(f"touch {kc}")


def main(config):
    global ssl_folder, ca_pem, kc_folder
    ssl_folder = pathlib.Path(config["data_path"]).joinpath("ssl")
    ca_pem = ssl_folder.joinpath("ca.pem")
    kc_folder = pathlib.Path(config["data_path"]).joinpath("kubeconfig")

    wg = wireguard_ips()
    KUBERNETES_PUBLIC_ADDRESS = list(wg.values())[0]

    make_configs(KUBERNETES_PUBLIC_ADDRESS)
    if in_vagrant():
        make_config("vagrant", "127.0.0.1")
    else:
        ext_ip = list(external_ips().values())[0]
        make_config("external", ext_ip)
    for server in config["servers"]:
        make_node_config(server, KUBERNETES_PUBLIC_ADDRESS)
