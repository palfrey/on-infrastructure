terraform {
  required_providers {
    vagrant = {
      source  = "bmatcuk/vagrant"
      version = "4.0.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"
}

resource "vagrant_vm" "server" {
  vagrantfile_dir = "."
  count           = 2
  get_ports       = true
  env = {
    SERVER_NAME      = "server-${count.index}"
    SERVER_INDEX     = count.index
    VAGRANTFILE_HASH = md5(file("Vagrantfile"))
  }
}

resource "local_file" "inventory" {
  content  = templatefile("inventory.yaml.tpl", { servers = vagrant_vm.server.* })
  filename = "../../mitogen/local/inventory.yaml"
}

resource "local_file" "keys" {
  count           = length(vagrant_vm.server)
  content         = vagrant_vm.server[count.index].ssh_config[0].private_key
  filename        = "../../mitogen/local/configs/ssh-private-${vagrant_vm.server[count.index].machine_names[0]}.key"
  file_permission = "0600"
}

module "dns" {
  source = "../modules/dns"

  env_name = "local"
}

resource "aws_route53_record" "app-a-star" {
  zone_id = module.dns.zone_id
  name    = "*.local.infra.net"
  type    = "A"
  ttl     = "300"
  records = ["127.0.0.1"]
}
