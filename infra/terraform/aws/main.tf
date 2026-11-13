data "aws_caller_identity" "current" {}

locals {
  # O ID da conta no nome evita colisão, já que nomes de bucket são globais.
  bucket_name = var.bucket_name != "" ? var.bucket_name : "assistente-qa-relatorios-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

module "reports_bucket" {
  source = "../modules/s3-reports-bucket"

  bucket_name           = local.bucket_name
  report_retention_days = var.report_retention_days
}
