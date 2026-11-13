# Governança do repositório: a main só recebe código que passou pelo CI.

resource "github_branch_protection" "this" {
  repository_id = var.repository_name
  pattern       = var.branch

  enforce_admins                  = var.enforce_admins
  required_linear_history         = var.require_linear_history
  require_conversation_resolution = true
  allows_deletions                = false
  allows_force_pushes             = false

  required_status_checks {
    strict   = var.strict_status_checks
    contexts = var.required_status_checks
  }
}

resource "github_issue_label" "this" {
  for_each = var.labels

  repository  = var.repository_name
  name        = each.key
  color       = lower(each.value.color)
  description = each.value.description
}

resource "github_repository_topics" "this" {
  count = length(var.topics) > 0 ? 1 : 0

  repository = var.repository_name
  topics     = sort(var.topics)
}
