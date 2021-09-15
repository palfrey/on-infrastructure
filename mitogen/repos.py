from utils import run_command, set_file_contents, set_file_contents_from_template


def debian_repo(name):
    fname = "/etc/apt/sources.list.d/%s.list" % name
    contents = "deb http://deb.debian.org/debian %s main" % name

    changed = set_file_contents(fname, contents)
    if changed:
        run_command("apt update")

    pinning()


def pinning():
    set_file_contents_from_template("/etc/apt/preferences.d/pinning", "pinning.j2")
