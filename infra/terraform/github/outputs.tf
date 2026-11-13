output "protected_branch" {
  description = "Branch protegida."
  value       = module.governance.protected_branch
}

output "required_status_checks" {
  description = "Jobs exigidos antes do merge."
  value       = module.governance.required_status_checks
}

output "labels" {
  description = "Labels criadas no repositório."
  value       = module.governance.labels
}

output "topics" {
  description = "Tópicos do repositório."
  value       = module.governance.topics
}
