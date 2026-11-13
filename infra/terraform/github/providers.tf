# O token NÃO fica em arquivo: o provider lê a variável de ambiente GITHUB_TOKEN.
provider "github" {
  owner = var.github_owner
}
