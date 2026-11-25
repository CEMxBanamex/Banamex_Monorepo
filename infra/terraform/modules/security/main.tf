locals {
  # Una entrada por (ambiente, CIDR) con clave estable, p. ej. "dev-10.0.0.0/8".
  ec2_https = merge([
    for env, cfg in var.ambientes : {
      for cidr in cfg.allowed_cidrs : "${env}-${cidr}" => { env = env, cidr = cidr }
    }
  ]...)
}

# --- EC2: un security group por ambiente ---

resource "aws_security_group" "ec2" {
  for_each = var.ambientes

  name        = "${var.nombre}-ec2-${each.key}"
  description = "EC2 de la API (${each.key})"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.nombre}-ec2-${each.key}" }
}

# 80 abierto a todos solo para el reto HTTP-01 de Let's Encrypt y la
# redirección a HTTPS que hace Caddy; la API se sirve por 443.
resource "aws_vpc_security_group_ingress_rule" "ec2_http" {
  for_each = aws_security_group.ec2

  security_group_id = each.value.id
  description       = "HTTP-01 de Lets Encrypt y redireccion a HTTPS" # sin apostrofo: AWS no lo admite en descripciones
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "ec2_https" {
  for_each = local.ec2_https

  security_group_id = aws_security_group.ec2[each.value.env].id
  description       = "HTTPS de la API"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = each.value.cidr
}

resource "aws_vpc_security_group_egress_rule" "ec2_todo" {
  for_each = aws_security_group.ec2

  security_group_id = each.value.id
  description       = "Salida libre"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# --- RDS ---

# Sin reglas de salida: los SG son con estado (las respuestas salen solas) y
# RDS no necesita iniciar conexiones. Terraform quita la regla de salida por
# defecto que AWS agrega al crear el SG.
resource "aws_security_group" "rds" {
  name        = "${var.nombre}-rds"
  description = "PostgreSQL de RDS"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.nombre}-rds" }
}

resource "aws_vpc_security_group_ingress_rule" "rds_desde_ec2" {
  for_each = aws_security_group.ec2

  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL desde la EC2 de ${each.key}"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = each.value.id
}

# Lista vacía = base cerrada a todo lo que no sea las EC2.
resource "aws_vpc_security_group_ingress_rule" "rds_cidr" {
  for_each = toset(var.db_allowed_cidrs)

  security_group_id = aws_security_group.rds.id
  description       = "PostgreSQL desde ${each.value}"
  ip_protocol       = "tcp"
  from_port         = 5432
  to_port           = 5432
  cidr_ipv4         = each.value
}
