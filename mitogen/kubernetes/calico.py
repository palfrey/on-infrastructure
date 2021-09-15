from utils import (
    configs,
    download_executable,
    make_directory,
    set_file_contents,
    set_file_contents_from_template,
    systemd_set,
)


def main():
    download_executable(
        "https://github.com/projectcalico/cni-plugin/releases/download/v3.14.0/calico-amd64",
        "412a3a94742fb4a72698bb561a0d0f31af03588a41e7c6acd74ce081b3859189",
        path="/opt/cni/bin/calico",
    )
    download_executable(
        "https://github.com/projectcalico/cni-plugin/releases/download/v3.14.0/calico-ipam-amd64",
        "73ac406687062b67ab27084577f05fb2212e77819d624dc26e1cc782c60cbba1",
        path="/opt/cni/bin/calico-ipam",
    )
    download_executable(
        "https://github.com/projectcalico/calicoctl/releases/download/v3.14.0/calicoctl",
        "4e38c7e81653faf3659b0afddabde4dff736bb1b4cc59ebe238907a9641816a7",
        "calicoctl",
    )
    changes = make_directory("/etc/cni/net.d/")

    changes = (
        set_file_contents(
            "/etc/cni/net.d/calico-kubeconfig", configs("kubeconfig/cni.kubeconfig")
        )
        or changes
    )
    changes = (
        set_file_contents_from_template(
            "/etc/cni/net.d/10-calico.conflist", "calico.conflist.j2"
        )
        or changes
    )

    if changes:
        systemd_set("kubelet", restart=True)
