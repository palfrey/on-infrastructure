# Mostly as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/09-bootstrapping-kubernetes-workers.md

import os

from network import wireguard_ip
from utils import (
    apt_install,
    configs,
    download_and_unpack,
    download_executable,
    host,
    link,
    make_directory,
    run_command,
    set_file_contents,
    set_file_contents_from_template,
    systemd_set,
)

POD_CIDR = "10.244.0.0/16"


def systemd_with_config(config_path, template, name, changed=False, **kwargs):
    changed = (
        set_file_contents_from_template(config_path, template, **kwargs) or changed
    )
    service_file = set_file_contents_from_template(
        "/etc/systemd/system/%s.service" % name, "%s.service.j2" % name, **kwargs
    )

    if service_file:
        run_command("systemctl daemon-reload")

    systemd_set(name, enabled=True, running=True, restart=service_file or changed)


def main():
    apt_install(["socat", "conntrack", "ipset"])

    swap_status = run_command("swapon --show")
    if len(swap_status.splitlines()) > 1:
        # Need to disable swap for kubelet
        run_command("swapoff -a")

    download_executable(
        "https://dl.k8s.io/v1.20.1/bin/linux/amd64/kube-proxy",
        "bb1171b6cfb3b833310723de198b9608722db8507567812de8bacc06b2966e42",
    )
    download_executable(
        "https://dl.k8s.io/v1.20.1/bin/linux/amd64/kubectl",
        "3f4b52a8072013e4cd34c9ea07e3c0c4e0350b227e00507fb1ae44a9adbf6785",
    )
    download_executable(
        "https://dl.k8s.io/v1.20.1/bin/linux/amd64/kubelet",
        "2970974fa56ee90b76c7f3f8b0075f0719bb9d645aacfcef85238b68972aa9c3",
    )

    res = download_and_unpack(
        "https://github.com/kubernetes-sigs/cri-tools/releases/download/v1.20.0/crictl-v1.20.0-linux-amd64.tar.gz",
        "44d5f550ef3f41f9b53155906e0229ffdbee4b19452b4df540265e29572b899c",
    )
    link("/usr/local/bin/crictl", "%s/crictl" % res["dir_name"])

    download_executable(
        "https://github.com/opencontainers/runc/releases/download/v1.0.0-rc93/runc.amd64",
        "9feaa82be15cb190cf0ed76fcb6d22841abd18088d275a47e894cd1e3a0ee4b6",
        "runc",
    )
    res = download_and_unpack(
        "https://github.com/containernetworking/plugins/releases/download/v0.9.1/cni-plugins-linux-amd64-v0.9.1.tgz",
        "962100bbc4baeaaa5748cdbfce941f756b1531c2eadb290129401498bfac21e7",
    )
    make_directory("/opt/cni/bin/")
    for fname in os.listdir(res["dir_name"]):
        link("/opt/cni/bin/%s" % fname, "%s/%s" % (res["dir_name"], fname))
    res = download_and_unpack(
        "https://github.com/containerd/containerd/releases/download/v1.5.5/containerd-1.5.5-linux-amd64.tar.gz",
        "8efc527ffb772a82021800f0151374a3113ed2439922497ff08f2596a70f10f1",
    )
    bin_dir = "%s/bin" % res["dir_name"]
    for fname in os.listdir(bin_dir):
        link("/bin/%s" % fname, "%s/%s" % (bin_dir, fname))

    changed = make_directory("/etc/cni/net.d")
    changed = (
        set_file_contents_from_template(
            "/etc/cni/net.d/99-loopback.conf", "cni-loopback.conf.j2"
        )
    ) or changed
    make_directory("/etc/containerd")
    systemd_with_config(
        "/etc/containerd/config.toml",
        "containerd-config.toml.j2",
        "containerd",
        changed=changed,
    )

    changed = (
        set_file_contents("/var/lib/kubernetes/ca.pem", configs("ssl/ca.pem"))
        or changed
    )
    make_directory("/var/lib/kubelet/")
    hostname = host()["name"]
    changed = (
        set_file_contents(
            "/var/lib/kubelet/%s.pem" % hostname, configs("ssl/keys-%s.pem" % hostname)
        )
        or changed
    )
    changed = (
        set_file_contents(
            "/var/lib/kubelet/%s-key.pem" % hostname,
            configs("ssl/keys-%s-key.pem" % hostname),
        )
        or changed
    )
    changed = (
        set_file_contents(
            "/var/lib/kubelet/kubeconfig",
            configs("kubeconfig/%s.kubeconfig" % hostname),
        )
        or changed
    )
    systemd_with_config(
        "/var/lib/kubelet/kubelet-config.yaml",
        "kubelet-config.yaml.j2",
        "kubelet",
        changed=changed,
        POD_CIDR=POD_CIDR,
        HOSTNAME=hostname,
        WIREGUARD_IP=wireguard_ip(host()),
    )

    make_directory("/var/lib/kube-proxy")
    changed = set_file_contents(
        "/var/lib/kube-proxy/kubeconfig", configs("kubeconfig/kube-proxy.kubeconfig")
    )
    systemd_with_config(
        "/var/lib/kube-proxy/kube-proxy-config.yaml",
        "kube-proxy-config.yaml.j2",
        "kube-proxy",
        changed=changed,
    )
