output "instance_id" {
  description = "ID de la instancia."
  value       = aws_instance.esta.id
}

output "elastic_ip" {
  description = "IP elástica (fija) de la instancia. Va en el registro A del subdominio de la API."
  value       = aws_eip.esta.public_ip
}

output "private_ip" {
  description = "IP privada de la instancia."
  value       = aws_instance.esta.private_ip
}
