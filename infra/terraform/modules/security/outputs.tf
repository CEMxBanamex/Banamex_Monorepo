output "ec2_sg_ids" {
  description = "Mapa ambiente => ID del security group de su EC2."
  value       = { for env, sg in aws_security_group.ec2 : env => sg.id }
}

output "rds_sg_id" {
  description = "ID del security group de RDS."
  value       = aws_security_group.rds.id
}
