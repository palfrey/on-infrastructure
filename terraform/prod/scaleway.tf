provider "scaleway" {
  project_id = "bf02f5f2-5232-4476-a99f-a68f1f28e2fd"
}

resource "tls_private_key" "scaleway" {
  algorithm   = "ECDSA"
  ecdsa_curve = "P521"
}

resource "random_uuid" "scaleway-node-id" {
  count = 3
}

locals {
  scaleway_zones = ["fr-par-1", "fr-par-2", "nl-ams-1", "pl-waw-1"]
}

resource "scaleway_account_ssh_key" "default" {
  name       = "SSH key for prod infra"
  public_key = tls_private_key.scaleway.public_key_openssh
}

resource "scaleway_instance_ip" "node_ip" {
  count = 3
  zone  = local.scaleway_zones[count.index]
}

resource "scaleway_instance_server" "node" {
  count = 3
  type  = "DEV1-M"
  name  = "node-${random_uuid.scaleway-node-id[count.index].result}"
  image = "debian_buster"
  zone  = local.scaleway_zones[count.index]
  ip_id = scaleway_instance_ip.node_ip[count.index].id
}

resource "local_file" "scaleway-keys" {
  count           = length(scaleway_instance_server.node)
  content         = tls_private_key.scaleway.private_key_pem
  filename        = "../../mitogen/prod/configs/ssh-private-${scaleway_instance_server.node[count.index].name}.key"
  file_permission = "0600"
}
