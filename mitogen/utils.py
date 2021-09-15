import contextlib
import logging
import os
import re
import stat
import subprocess
from difflib import unified_diff

import jinja2

import mitogen.utils
from mitogen.core import StreamError
from mitogen.parent import Router

env = None
data = None


def host():
    return data["host"]


def config():
    return data["config"]


def configs(fname):
    try:
        return data["configs"][fname]
    except KeyError:
        print(sorted(data["configs"].keys()))
        raise


def set_data(new_data):
    loader = jinja2.DictLoader(new_data["templates"])
    global env, data
    env = jinja2.Environment(loader=loader, undefined=jinja2.StrictUndefined)
    data = new_data


def set_file_contents(fname, contents, ignore_changes=False):
    # type:(str, str, bool) -> bool
    needs_update = False
    if not os.path.exists(fname):
        needs_update = True
        logging.info("File %s was missing" % fname)
    elif not ignore_changes:
        data = open(fname).readlines()
        diff = list(unified_diff(data, contents.splitlines(True)))
        if len(diff) > 0:
            diff = "".join(diff)
            logging.info("File %s was different. Diff is: \n%s" % (fname, diff))
            needs_update = True

    if needs_update:
        open(fname, "w").write(contents)

    return needs_update


def set_file_contents_from_template(fname, template, ignore_changes=False, **kwargs):
    return set_file_contents(
        fname,
        env.get_template(template).render(**kwargs),
        ignore_changes=ignore_changes,
    )


@contextlib.contextmanager
def cd(path):
    CWD = os.getcwd()

    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(CWD)


def run_command(cmd, directory=None):
    # type: (str, str) -> str
    display = cmd.strip()
    while display.find("  ") != -1:
        display = display.replace("  ", " ")
    try:
        if directory is not None:
            logging.info("Run in %s: %s" % (directory, display))
            with cd(directory):
                return subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, shell=True
                )
        else:
            logging.info("Run: %s" % display)
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise


def apt_install(packages):
    # type: (list[str]) -> None
    run_command("apt-get install %s --no-install-recommends --yes" % " ".join(packages))


def set_mode(path, mode):
    raw_mode = int(mode, 8)
    existing = stat.S_IMODE(os.stat(path).st_mode)
    if existing != raw_mode:
        logging.info("chmod %s %s" % (path, mode))
        os.chmod(path, raw_mode)
        return True
    else:
        return False


def make_directory(path, mode=None):
    ret = False
    if not os.path.exists(path):
        logging.info("Make directory %s" % path)
        os.makedirs(path)
        ret = True
    if mode is not None:
        ret = set_mode(path, mode) or ret
    return ret


def decode(info):
    for k in list(info.keys()):
        if type(k) == bytes:
            info[k.decode()] = info[k].decode()
            del info[k]


def run(func):
    mitogen.utils.log_to_file()
    mitogen.utils.run_with_router(func)


def add_folder_to_config(configs, folder, shortname=None, filter=None):
    if not os.path.exists(folder):
        print("Skipping %s from config as doesn't exist" % folder)
        return
    for f in os.listdir(folder):
        if filter is not None:
            if not filter(f):
                continue
        if shortname is not None:
            key = os.path.join(shortname, f)
            full = os.path.join(folder, f)
        else:
            full = key = os.path.join(folder, f)
        configs[key] = open(full).read()


def create_data(server=None):
    config = get_config()
    templates = {}
    for root, dirs, files in os.walk("templates"):
        for f in files:
            templates[f] = open(os.path.join(root, f)).read()
    configs = {}
    add_folder_to_config(
        configs,
        config_path(),
        shortname="configs",
        filter=lambda f: f.startswith("wireguard-public")
        or f.startswith("networks-")
        or f.startswith("other-"),
    )
    add_folder_to_config(
        configs,
        config["data_path"] + "/ssl",
        shortname="ssl",
        filter=lambda f: f.endswith(".pem"),
    )
    add_folder_to_config(
        configs, config["data_path"] + "/kubeconfig", shortname="kubeconfig"
    )
    if os.path.exists("kubernetes/encryption-config.yaml"):
        configs["encryption-config.yaml"] = open(
            "kubernetes/encryption-config.yaml"
        ).read()
    return {
        "templates": templates,
        "host": server,
        "config": config,
        "configs": configs,
    }


def main(router, func):
    # type:(Router, callable) -> None
    config = get_config()
    calls = []
    for server in config["servers"]:
        try:
            connect = router.ssh(
                hostname=server["ssh_hostname"],
                port=server["ssh_port"],
                username=server["ssh_user"],
                identity_file=server["ssh_key"],
                check_host_keys="accept",
            )
        except StreamError:
            print(
                "Exception while trying to login to %s@%s:%s"
                % (server["ssh_user"], server["ssh_hostname"], server["ssh_port"])
            )
            raise

        sudo = router.sudo(via=connect)
        calls.append(
            sudo.call_async(
                func,
                create_data(server=server),
            )
        )

    infos = []
    errors = []
    for call in calls:
        try:
            info = call.get().unpickle()
            if info is not None:
                decode(info)
            infos.append(info)
        except mitogen.core.Error as e:
            print("Got error", e)
            errors.append(e)

    if len(errors) > 0:
        raise Exception(errors)

    return infos


inventory = None


def set_config(inventory_path):
    import yaml

    global inventory
    inventory = yaml.safe_load(open(inventory_path))


def get_config():
    return inventory


def config_path(shortname=False):
    if inventory is None or shortname:
        return "configs"
    else:
        return inventory["data_path"] + "/configs"


def journal(name):
    res = run_command("journalctl -u %s" % name)
    print(res)


def systemd_set(name, enabled=None, running=None, restart=None, reloaded=None):
    raw = run_command("systemctl show %s --no-page" % name)
    status = dict([line.split("=", 1) for line in raw.splitlines()])
    if status.get("UnitFileState") == "masked":
        logging.info("Unmasking %s" % name)
        run_command("systemctl unmask %s" % name)
    if enabled is not None:
        if enabled:
            if status["UnitFileState"] != "enabled":
                logging.info("%s is currently %s" % (name, status["UnitFileState"]))
                run_command("systemctl enable %s" % name)
        else:
            raise Exception
    started = False
    if running is not None:
        if running:
            if status["SubState"] not in ["running", "auto-restart", "start"]:
                logging.info("running: %s %s" % (name, status["SubState"]))
                try:
                    run_command("systemctl start %s" % name)
                except subprocess.CalledProcessError:
                    journal(name)
                    raise
                started = True
        else:
            raise Exception
    if restart is True and not started:
        try:
            run_command("systemctl restart %s" % name)
        except subprocess.CalledProcessError:
            journal(name)
            raise

    if reloaded is not None:
        run_command("systemctl reload %s" % name)


def replace_line(fname, search, replace):
    existing = open(fname).read()
    if search in existing:
        set_file_contents(fname, existing.replace(search, replace))


def insert_line(fname, line):
    existing = open(fname).read()
    if line not in existing:
        set_file_contents(fname, existing + "\n" + line)


def insert_or_replace(fname, matcher, line):
    # type: (str, re.Pattern, str) -> None
    existing = open(fname).read()
    results = matcher.search(existing)
    if results is not None:
        set_file_contents(
            fname, existing[: results.start()] + line + existing[results.end() :]
        )
    else:
        set_file_contents(fname, existing + "\n" + line)


def sha_file(fname):
    existing_sha = run_command("sha256sum %s" % fname).strip()
    return existing_sha.split(" ")[0]


def has_sha(fname, sha):
    if os.path.exists(fname):
        existing_sha = sha_file(fname)
        if existing_sha == sha:
            return True

    return False


def download(url, fname, sha, mode=None):
    exists = has_sha(fname, sha)
    if not exists:
        run_command("curl -Lo %s %s" % (fname, url))
        existing_sha = sha_file(fname)
        assert existing_sha == sha, (existing_sha, sha)

    if mode is not None:
        set_mode(fname, mode)

    return not exists


def link(target, source):
    if os.path.lexists(target) and (
        not os.path.exists(target) or not os.path.samefile(source, target)
    ):
        logging.info("Unlink %s" % target)
        os.remove(target)
    if not os.path.lexists(target):
        logging.info("Link %s to %s" % (target, source))
        os.symlink(source, target)
        return True
    else:
        return False


def download_executable(url, hash, name=None, path=None):
    if name is None:
        name = url.split("/")[-1]
    if path is None:
        path = "/usr/local/bin/%s" % name
    download(
        url,
        path,
        hash,
        mode="755",
    )


def download_and_unpack(url, hash, name=None, dir_name=None):
    if name is None:
        name = url.split("/")[-1]
    tar_path = "/opt/%s" % name
    if dir_name is None:
        dir_name = "/opt/%s" % name.replace(".tar.gz", "").replace(".tgz", "")
    changed = download(
        url,
        tar_path,
        hash,
    )

    make_directory(dir_name)
    if os.listdir(dir_name) == []:
        run_command("tar --directory=%s -zxvf %s" % (dir_name, tar_path))
        changed = True

    return {"changed": changed, "dir_name": dir_name}


def last_modified(fname):
    try:
        return os.stat(fname).st_mtime
    except FileNotFoundError:
        return 0


def build_with_command(fname, command, deps=[]):
    display = command.strip()
    while display.find("  ") != -1:
        display = display.replace("  ", " ")
    changed = set_file_contents("%s.command" % fname, display)
    target_modified = last_modified(fname)
    for dep in deps:
        if last_modified(dep) > target_modified:
            changed = True
    if not os.path.exists(fname) or changed:
        run_command(command)
        return True
    else:
        return False


def delete(fname):
    if os.path.exists(fname):
        logging.info("Deleting %s", fname)
        os.remove(fname)
        return True
    else:
        return False
