import base64
import os

from utils import (
    cd,
    create_data,
    get_config,
    main,
    run,
    set_data,
    set_file_contents_from_template,
)

from mitogen.parent import Router


def do_each(data):
    from . import calico, control_plane, etcd, longhorn, worker_node

    set_data(data)
    etcd.main()
    longhorn.main()
    control_plane.main()
    worker_node.main()
    calico.main()


def core(router):
    # type:(Router) -> None

    for _ in main(router, do_each):
        pass


def do():
    from . import certs, kubeconfig, typha

    config = get_config()
    set_data(create_data())
    with cd(os.path.dirname(__file__)):
        certs.main(config)
        kubeconfig.main(config)
        set_file_contents_from_template(
            "encryption-config.yaml",
            "encryption-config.yaml.j2",
            ignore_changes=True,
            ENCRYPTION_KEY=base64.b64encode(os.urandom(32)).decode("utf-8"),
        )
        typha.main()

    run(core)
