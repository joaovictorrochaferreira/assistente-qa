variable "repository_name" {
  description = "Nome do repositório (sem o dono), por exemplo assistente-qa."
  type        = string
}

variable "branch" {
  description = "Branch protegida."
  type        = string
  default     = "main"
}

variable "required_status_checks" {
  description = "Nomes dos jobs do GitHub Actions que precisam passar antes do merge."
  type        = list(string)

  validation {
    condition     = length(var.required_status_checks) > 0
    error_message = "Informe ao menos um status check obrigatório."
  }
}

variable "strict_status_checks" {
  description = "Exige que a branch do PR esteja atualizada com a main antes do merge."
  type        = bool
  default     = true
}

variable "enforce_admins" {
  description = "Aplica as regras também aos administradores. Em repositório pessoal, false deixa o dono corrigir a main em emergências."
  type        = bool
  default     = false
}

variable "require_linear_history" {
  description = "Proíbe merge commits na branch protegida."
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels de issues e PRs, no formato nome => { color, description }."
  type = map(object({
    color       = string
    description = string
  }))
  default = {}

  validation {
    condition     = alltrue([for label in values(var.labels) : can(regex("^[0-9a-fA-F]{6}$", label.color))])
    error_message = "A cor de cada label deve ter 6 dígitos hexadecimais, sem #."
  }
}

variable "topics" {
  description = "Tópicos do repositório exibidos no GitHub."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for topic in var.topics : can(regex("^[a-z0-9][a-z0-9-]{0,49}$", topic))])
    error_message = "Tópicos devem ter até 50 caracteres, só minúsculas, números e hífens."
  }
}
