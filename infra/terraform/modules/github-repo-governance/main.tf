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

# Ambientes usados pelo pipeline de CD. Só a main pode implantar neles.
resource "github_repository_environment" "this" {
  for_each = var.environments

  repository          = var.repository_name
  environment         = each.key
  wait_timer          = each.value.wait_timer
  prevent_self_review = false

  dynamic "reviewers" {
    for_each = length(each.value.reviewer_ids) > 0 ? [1] : []
    content {
      users = each.value.reviewer_ids
    }
  }

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}
