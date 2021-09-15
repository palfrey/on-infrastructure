# Mostly as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/07-bootstrapping-etcd.md

from network import wireguard_ip, wireguard_ips
from utils import (
    configs,
    download_and_unpack,
    host,
    link,
    make_directory,
    run_command,
    set_file_contents,
    set_file_contents_from_template,
    systemd_set,
)


def main():
    make_directory("/opt/etcd")
    res = download_and_unpack(
        "https://github.com/etcd-io/etcd/releases/download/v3.4.15/etcd-v3.4.15-linux-amd64.tar.gz",
        "3bd00836ea328db89ecba3ed2155293934c0d09e64b53d6c9dfc0a256e724b81",
    )
    changed = res["changed"]

    changed = (
        link(
            "/usr/local/bin/etcd", "%s/etcd-v3.4.15-linux-amd64/etcd" % res["dir_name"]
        )
        or changed
    )
    changed = (
        link(
            "/usr/local/bin/etcdctl",
            "%s/etcd-v3.4.15-linux-amd64/etcdctl" % res["dir_name"],
        )
        or changed
    )

    make_directory("/etc/etcd")
    make_directory("/var/lib/etcd", mode="700")
    for pem in ["ca", "etcd-key", "etcd"]:
        changed = (
            set_file_contents("/etc/etcd/%s.pem" % pem, configs("ssl/%s.pem" % pem))
            or changed
        )

    cluster = ",".join(
        ["%s=https://%s:2380" % (k, v) for (k, v) in wireguard_ips().items()]
    )
    service_file = set_file_contents_from_template(
        "/etc/systemd/system/etcd.service",
        "etcd.service.j2",
        ETCD_NAME=host()["name"],
        INTERNAL_IP=wireguard_ip(host()),
        CLUSTER=cluster,
    )

    if service_file:
        run_command("systemctl daemon-reload")

    systemd_set("etcd", enabled=True, running=True, restart=service_file or changed)
