import json
import socket

from utils import config_path, configs, main, run, run_command, set_data
from wireguard_bootstrap import main as wg_bootstrap
from wireguard_bootstrap import public_key_path

from mitogen.parent import Router


def network_config_file(name, shortname=False):
    return config_path(shortname) + "/networks-{name}".format(name=name)


def network_config(name):
    return json.loads(configs(network_config_file(name, shortname=True)))


def other_config_file(name, shortname=False):
    return config_path(shortname) + "/other-{name}".format(name=name)


def other_config(name):
    return json.loads(configs(other_config_file(name, shortname=True)))


def do(data):
    set_data(data)
    data = {
        "hostname": socket.gethostname(),
        "network_devices": run_command("ip -j address"),
        "external_ip": run_command("curl --silent https://api.ipify.org?format=json"),
    }
    data.update(wg_bootstrap())
    return data


def core(router):
    # type:(Router) -> None

    for info in main(router, do):
        open(public_key_path(info["hostname"]), "w").write(info["wg_publickey"])
        networks = json.loads(info["network_devices"])
        json.dump(networks, open(network_config_file(info["hostname"]), "w"), indent=2)

        other = {"external_ip": json.loads(info["external_ip"])["ip"]}
        json.dump(other, open(other_config_file(info["hostname"]), "w"), indent=2)


if __name__ == "__main__":
    run(core)
