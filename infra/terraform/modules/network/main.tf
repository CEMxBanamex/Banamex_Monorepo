data "aws_availability_zones" "disponibles" {
  state = "available"
}

# Resuelve "com.amazonaws.<region>.s3" sin leer aws_region.name/id (deprecados en
# v6) ni aws_region.region (no existe en v5); funciona con ambas versiones.
data "aws_vpc_endpoint_service" "s3" {
  service      = "s3"
  service_type = "Gateway"
}

locals {
  # Las dos primeras zonas; el índice fija el CIDR de cada subred.
  zonas = { for i, az in slice(data.aws_availability_zones.disponibles.names, 0, 2) : az => i }
}

resource "aws_vpc" "esta" {
  cidr_block = var.cidr_vpc
  # RDS con acceso público necesita DNS y hostnames activos en la VPC.
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.nombre}-vpc" }
}

resource "aws_internet_gateway" "este" {
  vpc_id = aws_vpc.esta.id

  tags = { Name = "${var.nombre}-igw" }
}

# Claves por zona: el orden de los outputs es estable (orden lexicográfico de la zona).
resource "aws_subnet" "publica" {
  for_each = local.zonas

  vpc_id                  = aws_vpc.esta.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.cidr_vpc, 8, each.value) # x.x.0.0/24, x.x.1.0/24
  map_public_ip_on_launch = true

  tags = { Name = "${var.nombre}-publica-${each.key}" }
}

resource "aws_subnet" "privada" {
  for_each = local.zonas

  vpc_id            = aws_vpc.esta.id
  availability_zone = each.key
  # Desplazadas +10 para dejar espacio a más subredes públicas.
  cidr_block = cidrsubnet(var.cidr_vpc, 8, each.value + 10)

  tags = { Name = "${var.nombre}-privada-${each.key}" }
}

resource "aws_route_table" "publica" {
  vpc_id = aws_vpc.esta.id

  tags = { Name = "${var.nombre}-rt-publica" }
}

resource "aws_route" "publica_internet" {
  route_table_id         = aws_route_table.publica.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.este.id
}

resource "aws_route_table_association" "publica" {
  for_each = aws_subnet.publica

  subnet_id      = each.value.id
  route_table_id = aws_route_table.publica.id
}

# Sin ruta a internet: no hay NAT Gateway (costo). Solo tráfico local y S3 vía endpoint.
resource "aws_route_table" "privada" {
  vpc_id = aws_vpc.esta.id

  tags = { Name = "${var.nombre}-rt-privada" }
}

resource "aws_route_table_association" "privada" {
  for_each = aws_subnet.privada

  subnet_id      = each.value.id
  route_table_id = aws_route_table.privada.id
}

# Endpoint de tipo Gateway: gratuito y da acceso a S3 sin pasar por internet.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.esta.id
  service_name      = data.aws_vpc_endpoint_service.s3.service_name
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.publica.id, aws_route_table.privada.id]

  tags = { Name = "${var.nombre}-s3-endpoint" }
}
