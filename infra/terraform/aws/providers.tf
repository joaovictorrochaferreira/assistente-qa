# Este diretório é só validado no CI (fmt e validate) e nunca aplicado.
# Para aplicar, seria preciso uma conta AWS com credenciais no ambiente.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Projeto    = "assistente-qa"
      Ambiente   = var.environment
      Gerenciado = "terraform"
    }
  }
}
