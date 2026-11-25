output "vpc_id" {
  description = "ID de la VPC."
  value       = aws_vpc.esta.id
}

output "public_subnet_ids" {
  description = "IDs de las 2 subredes públicas (una por zona)."
  value       = [for s in aws_subnet.publica : s.id]
}

output "private_subnet_ids" {
  description = "IDs de las 2 subredes privadas (una por zona, sin salida a internet)."
  value       = [for s in aws_subnet.privada : s.id]
}
