output "nombres" {
  description = "Rutas completas de todos los parámetros creados."
  value       = sort(concat([for p in aws_ssm_parameter.manual : p.name], [for p in aws_ssm_parameter.gestionado : p.name]))
}
