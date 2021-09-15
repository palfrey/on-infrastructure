from os import system

from utils import get_config, set_config

if __name__ == "__main__":
    import sys

    set_config(sys.argv[1])
    server = int(sys.argv[2])

    server = get_config()["servers"][server]
    command = f"ssh -v {server['ssh_user']}@{server['ssh_hostname']} -i {server['ssh_key']} -p {server['ssh_port']}"
    print(command)
    system(command)
