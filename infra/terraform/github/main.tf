locals {
  labels = {
    "tipo: bug"          = { color = "d73a4a", description = "Algo não funciona como deveria" }
    "tipo: melhoria"     = { color = "a2eeef", description = "Nova funcionalidade ou melhoria" }
    "area: skill"        = { color = "5319e7", description = "Mudanças na skill cenarios-de-teste" }
    "area: ci"           = { color = "0e8a16", description = "Pipeline do GitHub Actions" }
    "area: infra"        = { color = "fbca04", description = "Scripts Terraform" }
    "area: testes"       = { color = "1d76db", description = "Testes automatizados e fixtures" }
    "area: documentacao" = { color = "0075ca", description = "README e documentação do projeto" }
  }

  topics = [
    "devops",
    "github-actions",
    "terraform",
    "qa",
    "gherkin",
    "test-automation",
    "python",
    "claude-skill",
  ]
}

module "governance" {
  source = "../modules/github-repo-governance"

  repository_name        = var.repository_name
  branch                 = "main"
  required_status_checks = var.required_status_checks
  labels                 = local.labels
  topics                 = local.topics
}
