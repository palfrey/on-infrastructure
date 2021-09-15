provider "aws" {
  region = "eu-west-2"
}

resource "aws_route53_zone" "infra" {
  name = "infra.net"
}

resource "aws_route53_zone" "infra-zone" {
  name = "${var.env_name}.infra.net"
}

resource "aws_route53_record" "infra-ns" {
  zone_id = aws_route53_zone.infra.zone_id
  name    = "${var.env_name}.infra.net"
  type    = "NS"
  ttl     = "30"
  records = [for s in aws_route53_zone.infra-zone.name_servers : "${s}."]
}
