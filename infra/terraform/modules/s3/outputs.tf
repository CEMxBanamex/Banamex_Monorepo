output "bucket" {
  description = "Nombre del bucket."
  value       = aws_s3_bucket.este.bucket
}

output "arn" {
  description = "ARN del bucket."
  value       = aws_s3_bucket.este.arn
}
