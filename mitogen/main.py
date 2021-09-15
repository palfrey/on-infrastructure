import bootstrap
import firewall
import kubernetes
import network
import wireguard
from utils import (
    apt_install,
    main,
    run,
    run_command,
    set_config,
    set_data,
    set_file_contents_from_template,
    systemd_set,
)

from mitogen.parent import Router


def do(data):
    set_data(data)
    apt_install(["ntp", "curl", "htop", "psmisc", "net-tools", "logrotate"])

    logrotate_changed = set_file_contents_from_template(
        "/etc/logrotate.conf", "logrotate.conf.j2"
    )
    logrotate_changed = (
        set_file_contents_from_template(
            "/etc/logrotate.d/rsyslog", "logrotate-rsyslog.j2"
        )
        or logrotate_changed
    )
    if logrotate_changed:
        run_command("logrotate /etc/logrotate.conf")

    systemd_set("ntp", enabled=True, running=True)

    wireguard.do()
    firewall.do()
    network.do()


def core(router):
    # type:(Router) -> None

    for info in main(router, do):
        pass


if __name__ == "__main__":
    import sys

    set_config(sys.argv[1])

    run(bootstrap.core)
    run(core)
    kubernetes.do()
