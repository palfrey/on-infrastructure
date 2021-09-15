import os

from utils import (
    download_and_unpack,
    has_sha,
    insert_line,
    replace_line,
    run_command,
    set_file_contents_from_template,
    systemd_set,
)


def do():
    if not has_sha(
        "/usr/sbin/ferm",
        "356c3675c1d7a32a585f6aa17d06ab0a314c3cf659ee808e46689136fa31b0a5",
    ):
        res = download_and_unpack(
            "https://github.com/MaxKellermann/ferm/archive/refs/tags/v2.6.tar.gz",
            "235fe3f91e010671fd03b1178808a90ab923ed170ad30c5b7459511d9a3154f4",
            name="ferm-2.6.tar.gz",
        )

        run_command("make install", directory="%s/ferm-2.6" % res["dir_name"])
        run_command("systemctl daemon-reload")

    ferm_version = run_command("ferm --version").splitlines()[0].strip()
    assert ferm_version == "ferm 2.6", ferm_version

    # This makes sure the nftables is not used, as it doesn't co-operate nicely with k8s
    for name in ["iptables", "ip6tables"]:
        linkto = "/usr/sbin/%s-legacy" % name
        if not os.path.samefile("/etc/alternatives/%s" % name, linkto):
            run_command("update-alternatives --set %s %s" % (name, linkto))

    sysctl_change = replace_line(
        "/etc/sysctl.conf",
        r"#net.ipv4.ip_forward=1",
        "net.ipv4.ip_forward=1",
    )

    if sysctl_change:
        run_command("sysctl -w net.ipv4.ip_forward=1")

    for iface in ["all", "default", "lo"]:
        sysctl_change = insert_line(
            "/etc/sysctl.conf",
            "net.ipv6.conf.%s.disable_ipv6 = 1" % iface,
        )

        if sysctl_change:
            run_command("sysctl -w net.ipv6.conf.%s.disable_ipv6=1" % iface)

    ferm_conf = set_file_contents_from_template("/etc/ferm.conf", "ferm.conf.j2")
    systemd_set("ferm", enabled=True, restart=ferm_conf)
