output "elastic_ip" {
  description = "IP fija de la EC2."
  value       = module.ec2.elastic_ip
}

output "registro_dns" {
  description = "Registro que hay que crear a mano en el registrador del dominio."
  value       = "Tipo A   ${local.api_host}   ->   ${module.ec2.elastic_ip}"
}

output "instance_id" {
  description = "ID de la EC2 (para Session Manager)."
  value       = module.ec2.instance_id
}

output "s3_bucket" {
  description = "Bucket de archivos del ambiente."
  value       = module.s3.bucket
}

output "parametros_ssm" {
  description = "Parámetros creados en SSM. Los que valen CAMBIAR se llenan con aws ssm put-parameter --overwrite."
  value       = module.ssm.nombres
}
