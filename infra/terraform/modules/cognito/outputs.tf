output "user_pool_id" {
  description = "ID del user pool."
  value       = aws_cognito_user_pool.este.id
}

output "client_id" {
  description = "ID del cliente (sin secreto) que usa el frontend."
  value       = aws_cognito_user_pool_client.frontend.id
}

output "dominio_login" {
  description = "Dominio de la interfaz de login alojada, o null si no se creó."
  value       = one(aws_cognito_user_pool_domain.este[*].domain)
}
