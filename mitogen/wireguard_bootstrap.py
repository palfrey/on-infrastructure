import os
import sys
from distutils.version import LooseVersion

from repos import debian_repo
from utils import apt_install, config_path, make_directory, run_command

wg_config = "/etc/wireguard"
private_key_file = "{wg_config}/privatekey".format(wg_config=wg_config)
public_key_file = "{wg_config}/publickey".format(wg_config=wg_config)


def public_key_path(name):
    return config_path() + "/wireguard-public-{name}.key".format(name=name)


def get_output(host, command):
    status, stdout, stderr = host.run_shell_command(command=command)
    stdout = "".join(stdout)
    assert status is True, (stdout, stderr)
    return stdout


def get_all_kernel_versions():
    raw = run_command(
        r"dpkg-query --showformat=$\{Package\},$\{Status\},$\{Version\}\\t --show linux-image-*",
    )
    versions = {}
    for line in raw.split("\t"):
        if line.strip() == "":
            continue
        try:
            (name, status, version) = line.split(",")
        except ValueError:
            raise Exception("'%s'" % line)
        if status == "install ok installed":
            versions[name] = version
    return versions


def main():
    debian_repo("buster-backports")

    apt_install(["linux-image-amd64"])
    versions = get_all_kernel_versions()
    ordered = sorted(
        [
            x.replace("linux-image-", "")
            for x in versions.keys()
            if x not in ["linux-image-amd64", "linux-image-cloud-amd64"]
        ],
        key=LooseVersion,
        reverse=True,
    )
    highest = ordered[0]
    current = run_command("uname -r").strip()
    if current != highest:
        print(ordered)
        print("'%s' != '%s'" % (current, highest))
        run_command("reboot")
        sys.exit(0)

    apt_install(["wireguard", "linux-headers-amd64"])
    modules = sorted([line.split(" ")[0] for line in run_command("lsmod").splitlines()])
    if "wireguard" not in modules:
        print("modules", modules)
        run_command("modprobe wireguard")

    make_directory(wg_config)
    if not os.path.exists(private_key_file):
        run_command("wg genkey > %s" % private_key_file)
    if not os.path.exists(public_key_file):
        run_command("cat %s | wg pubkey > %s" % (private_key_file, public_key_file))

    return {"wg_publickey": open(public_key_file).read().strip()}


if __name__ == "builtins":
    main()
