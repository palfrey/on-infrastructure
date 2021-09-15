import re

import utils
from bootstrap import network_config, other_config


def networks_by_interface(h):
    return dict([(intf["ifname"], intf) for intf in network_config(h["name"])])


def get_ipv4(network):
    addrs = network["addr_info"]
    for addr in addrs:
        if addr["family"] == "inet" and "local" != "":
            return addr["local"]
    return None


def external_ip(h):
    return other_config(h["name"])["external_ip"]


def external_ips():
    return dict([(h["name"], external_ip(h)) for h in utils.config()["servers"]])


def wireguard_ips():
    return dict([(h["name"], wireguard_ip(h)) for h in utils.config()["servers"]])


def in_vagrant():
    ext_ip = list(external_ips().values())[0]
    return ext_ip.startswith("172.28")


def ips(h):
    network = networks_by_interface(h)
    return [
        x
        for x in [
            get_ipv4(intf)
            for (name, intf) in network.items()
            if name not in ["vxlan.calico"]
        ]
        if x is not None
    ]


def wireguard_ip(h):
    return "192.168.2.%d" % (h["count"] + 1)


def do():
    for server in utils.config()["servers"]:
        name = server["name"]
        if name == utils.host()["name"]:
            continue
        utils.insert_or_replace(
            "/etc/hosts",
            re.compile(r"\d+\.\d+\.\d+\.\d+ %s" % name),
            "%s %s" % (wireguard_ip(server), name),
        )

        if not in_vagrant():
            utils.insert_or_replace(
                "/etc/resolv.conf", re.compile(r"nameserver .+"), "nameserver 8.8.8.8"
            )
