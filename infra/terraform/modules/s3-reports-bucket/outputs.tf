output "bucket_name" {
  description = "Nome do bucket criado."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN do bucket, para usar em políticas de IAM."
  value       = aws_s3_bucket.this.arn
}

output "reports_prefix" {
  description = "Prefixo onde os relatórios devem ser gravados."
  value       = var.reports_prefix
}
