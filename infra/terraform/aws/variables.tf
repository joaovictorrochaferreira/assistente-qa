variable "aws_region" {
  description = "Região da AWS onde o bucket seria criado."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Nome do ambiente, usado nas tags e no nome do bucket."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "hml", "prd"], var.environment)
    error_message = "O ambiente deve ser dev, hml ou prd."
  }
}

variable "bucket_name" {
  description = "Nome do bucket. Se vazio, usa assistente-qa-relatorios-<ambiente>-<id da conta>."
  type        = string
  default     = ""
}

variable "report_retention_days" {
  description = "Dias de retenção dos relatórios."
  type        = number
  default     = 90
}
