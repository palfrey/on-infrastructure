# Mostly as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/08-bootstrapping-kubernetes-controllers.md

from network import wireguard_ip, wireguard_ips
from utils import (
    configs,
    download_executable,
    host,
    make_directory,
    run_command,
    set_file_contents,
    set_file_contents_from_template,
    systemd_set,
)

from .worker_node import POD_CIDR


def kube_server(name, hash, has_kubeconfig=True, **kwargs):
    download_executable(
        "https://dl.k8s.io/v1.20.1/bin/linux/amd64/kube-%s" % name,
        hash,
    )

    if has_kubeconfig:
        changed = set_file_contents(
            "/var/lib/kubernetes/kube-%s.kubeconfig" % name,
            configs("kubeconfig/kube-%s.kubeconfig" % name),
        )
    else:
        changed = False

    service_file = set_file_contents_from_template(
        "/etc/systemd/system/kube-%s.service" % name,
        "kube-%s.service.j2" % name,
        **kwargs
    )

    if service_file:
        run_command("systemctl daemon-reload")

    systemd_set(
        "kube-%s" % name, enabled=True, running=True, restart=service_file or changed
    )


def main():
    make_directory("/etc/kubernetes/config")
    make_directory("/var/lib/kubernetes/")
    for pem in [
        "ca.pem",
        "ca-key.pem",
        "kubernetes-key.pem",
        "kubernetes.pem",
        "service-account-key.pem",
        "service-account.pem",
        "etcd.pem",
        "etcd-key.pem",
    ]:
        set_file_contents("/var/lib/kubernetes/%s" % pem, configs("ssl/%s" % pem))

    set_file_contents(
        "/var/lib/kubernetes/encryption-config.yaml", configs("encryption-config.yaml")
    )

    etcd_servers = ",".join(["https://%s:2379" % v for v in wireguard_ips().values()])
    kube_server(
        "apiserver",
        "2d743bcf1c56f9f8445eca9b4f1dc8b7a5a55910691f11b42ba34794739a724b",
        has_kubeconfig=False,
        INTERNAL_IP=wireguard_ip(host()),
        ETCD_SERVERS=etcd_servers,
    )

    kube_server(
        "controller-manager",
        "c309f89a864e54fb318186a2cbe6981915f7a97f137b638e35fa1999d1411782",
        WIREGUARD_IP=wireguard_ip(host()),
        POD_CIDR=POD_CIDR,
    )
    kube_server(
        "scheduler", "ce82a1e9704baff186d18d6e7f030a4c5329cb378d4fc5adac51e8e819b96621"
    )
    changed = set_file_contents_from_template(
        "/etc/kubernetes/config/kube-scheduler.yaml", "kube-scheduler.yaml.j2"
    )
    systemd_set("kube-scheduler", restart=changed)
