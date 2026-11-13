variable "github_owner" {
  description = "Usuário ou organização dono do repositório."
  type        = string
}

variable "repository_name" {
  description = "Nome do repositório a ser governado."
  type        = string
  default     = "assistente-qa"
}

variable "required_status_checks" {
  description = "Jobs do workflow CI exigidos antes do merge na main. Precisam bater com os nomes dos jobs em .github/workflows/ci.yml."
  type        = list(string)
  default = [
    "lint",
    "test",
    "validate",
    "build",
    "terraform (github)",
    "terraform (aws)",
  ]
}
