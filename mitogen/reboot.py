from utils import main, run, run_command, set_config

from mitogen.parent import Router


def do(data):
    run_command("reboot")


def core(router):
    # type:(Router) -> None

    for _ in main(router, do):
        pass


if __name__ == "__main__":
    import sys

    set_config(sys.argv[1])
    run(core)
