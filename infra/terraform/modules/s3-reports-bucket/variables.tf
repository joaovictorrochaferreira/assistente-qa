variable "bucket_name" {
  description = "Nome globalmente único do bucket de relatórios."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name)) && !strcontains(var.bucket_name, "..")
    error_message = "Use de 3 a 63 caracteres: minúsculas, números, pontos e hífens, começando e terminando com letra ou número."
  }
}

variable "reports_prefix" {
  description = "Prefixo (pasta) onde o CI grava os relatórios."
  type        = string
  default     = "relatorios/"
}

variable "report_retention_days" {
  description = "Dias até um relatório ser apagado automaticamente."
  type        = number
  default     = 90

  validation {
    condition     = var.report_retention_days >= 1
    error_message = "A retenção deve ser de pelo menos 1 dia."
  }
}

variable "noncurrent_version_retention_days" {
  description = "Dias até versões antigas (sobrescritas) serem apagadas."
  type        = number
  default     = 30

  validation {
    condition     = var.noncurrent_version_retention_days >= 1
    error_message = "A retenção de versões antigas deve ser de pelo menos 1 dia."
  }
}

variable "force_destroy" {
  description = "Permite destruir o bucket mesmo com objetos dentro. Mantenha false fora de testes."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags extras aplicadas ao bucket."
  type        = map(string)
  default     = {}
}
