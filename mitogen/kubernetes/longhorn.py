from utils import apt_install, systemd_set


def main():
    # As per https://longhorn.io/docs/1.1.0/deploy/install/#installation-requirements
    apt_install(["open-iscsi", "nfs-common"])

    systemd_set("iscsid", enabled=True, running=True)
