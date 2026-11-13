output "protected_branch" {
  description = "Branch protegida pelo módulo."
  value       = github_branch_protection.this.pattern
}

output "required_status_checks" {
  description = "Jobs do CI exigidos antes do merge."
  value       = var.required_status_checks
}

output "labels" {
  description = "Labels gerenciadas pelo Terraform."
  value       = sort(keys(github_issue_label.this))
}

output "topics" {
  description = "Tópicos aplicados ao repositório."
  value       = sort(var.topics)
}
