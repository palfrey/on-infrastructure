provider "aws" {
  region = "eu-west-2"
}

locals {
  servers = concat(
    [for node in scaleway_instance_server.node.* : { name : node.name, public_ipv4address : node.public_ip }],
    [for node in hcloud_server.node.* : { name : node.name, public_ipv4address : node.ipv4_address }]
  )
}

resource "local_file" "inventory" {
  content  = templatefile("inventory.yaml.tpl", { servers = local.servers })
  filename = "../../mitogen/prod/inventory.yaml"
}

module "dns" {
  source   = "../modules/dns"
  env_name = "prod"
}

resource "aws_route53_record" "infra-a-star" {
  zone_id = module.dns.zone_id
  name    = "*.prod.infra.net"
  type    = "A"
  ttl     = "300"
  records = local.servers[*].public_ipv4address
}
