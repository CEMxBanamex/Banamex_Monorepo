output "identifier" {
  description = "Identificador de la instancia."
  value       = aws_db_instance.esta.identifier
}

output "address" {
  description = "Host de la base."
  value       = aws_db_instance.esta.address
}

output "port" {
  description = "Puerto de la base."
  value       = aws_db_instance.esta.port
}

output "endpoint" {
  description = "host:puerto de la base."
  value       = aws_db_instance.esta.endpoint
}

output "master_user_secret_arn" {
  description = "ARN del secreto de Secrets Manager con la contraseña maestra (lo administra RDS)."
  value       = aws_db_instance.esta.master_user_secret[0].secret_arn
}
