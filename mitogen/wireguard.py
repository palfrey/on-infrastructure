import utils
from network import external_ip, wireguard_ip
from wireguard_bootstrap import private_key_file, public_key_path


def setup(name="wg0", ip="192.168.2.1", netmask=24, peers=[]):
    peers = {}
    for h in utils.config()["servers"]:
        if h["name"] == utils.host()["name"]:
            continue
        public_key = utils.configs(public_key_path(h["name"]))
        peers[h["name"]] = {
            "public_key": public_key,
            "endpoint": "%s:51820" % external_ip(h),
            "peer_addr": wireguard_ip(h),
        }

    conf_change = utils.set_file_contents_from_template(
        "/etc/wireguard/wg0.conf",
        "wg.conf.j2",
        PRIVATE_KEY=open(private_key_file).read().strip(),
        PEERS=peers,
        IP=ip,
        NETMASK=netmask,
    )

    utils.systemd_set("wg-quick@wg0", enabled=True, restart=conf_change)


def do():
    setup(ip=wireguard_ip(utils.host()))


# if __name__ == "builtins":
#     main()
