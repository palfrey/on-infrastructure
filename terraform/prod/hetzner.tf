locals {
  locations  = ["nbg1", "fsn1", "hel1"]
  node_count = 1
}

provider "hcloud" {}

resource "tls_private_key" "hcloud" {
  count       = local.node_count
  algorithm   = "ECDSA"
  ecdsa_curve = "P521"
}

resource "random_uuid" "hetzner-node-id" {
  count = local.node_count
}

resource "hcloud_ssh_key" "default" {
  count      = local.node_count
  name       = "SSH key for node-${random_uuid.hetzner-node-id[count.index].result}"
  public_key = tls_private_key.hcloud[count.index].public_key_openssh
}

resource "hcloud_server" "node" {
  count = local.node_count

  name        = "node-${random_uuid.hetzner-node-id[count.index].result}"
  image       = "debian-10"
  server_type = "cpx21"
  location    = local.locations[count.index]
  ssh_keys    = [hcloud_ssh_key.default[count.index].id]
}

resource "local_file" "hetzner-keys" {
  count           = local.node_count
  content         = tls_private_key.hcloud[count.index].private_key_pem
  filename        = "../../mitogen/prod/configs/ssh-private-${hcloud_server.node[count.index].name}.key"
  file_permission = "0600"
}
