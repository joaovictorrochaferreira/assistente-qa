output "reports_bucket_name" {
  description = "Nome do bucket de relatórios."
  value       = module.reports_bucket.bucket_name
}

output "reports_bucket_arn" {
  description = "ARN do bucket de relatórios."
  value       = module.reports_bucket.bucket_arn
}
