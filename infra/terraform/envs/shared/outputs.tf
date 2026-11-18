output "vpc_id" {
  description = "ID de la VPC."
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Subredes públicas (las usan las EC2 de dev y prod)."
  value       = module.network.public_subnet_ids
}

output "ec2_sg_ids" {
  description = "Mapa ambiente => security group de su EC2."
  value       = module.security.ec2_sg_ids
}

output "rds_endpoint" {
  description = "host:puerto de RDS."
  value       = module.rds.endpoint
}

output "rds_address" {
  description = "Host de RDS."
  value       = module.rds.address
}

output "rds_port" {
  description = "Puerto de RDS."
  value       = module.rds.port
}

output "rds_master_secret_arn" {
  description = "ARN del secreto con la contraseña maestra (lo administra RDS). Solo lo lee quien administra la base."
  value       = module.rds.master_user_secret_arn
}

output "cognito_user_pool_id" {
  description = "ID del user pool, o null si enable_cognito = false."
  value       = one(module.cognito[*].user_pool_id)
}

output "cognito_client_id" {
  description = "ID del cliente del frontend, o null si enable_cognito = false."
  value       = one(module.cognito[*].client_id)
}

output "cognito_dominio_login" {
  description = "Dominio de login alojado por Cognito, o null."
  value       = one(module.cognito[*].dominio_login)
}
