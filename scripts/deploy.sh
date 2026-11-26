#!/usr/bin/env bash
# Deploy da API do qa-toolkit com Docker Compose.
#
# Uso:
#   scripts/deploy.sh <homologacao|producao|local> [imagem]
#
# Exemplos:
#   scripts/deploy.sh local                                         # constrói e sobe a imagem local
#   scripts/deploy.sh homologacao ghcr.io/<usuario>/assistente-qa:sha-abc1234
#
# Etapas:
#   1. obtém a imagem (pull do registro, ou build se for a imagem local)
#   2. sobe API, Prometheus e Grafana e espera a API ficar saudável
#   3. roda o teste de fumaça de dentro do container da API
#   4. se o teste falhar, volta para a última imagem aprovada (rollback) e sai com erro
set -euo pipefail

AMBIENTE="${1:?uso: scripts/deploy.sh <homologacao|producao|local> [imagem]}"
IMAGEM="${2:-qa-toolkit:local}"

case "$AMBIENTE" in
  homologacao | producao | local) ;;
  *) echo "ambiente inválido: $AMBIENTE (use homologacao, producao ou local)" >&2; exit 2 ;;
esac

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PROJETO="qa-${AMBIENTE}"
ENV_FILE="deploy/${AMBIENTE}.env"
ESTADO=".deploy/${AMBIENTE}.imagem"

log() { echo "[deploy ${AMBIENTE} $(date -u +%H:%M:%S)] $*"; }

compose() {
  local imagem="$1"
  shift
  local args=(-p "$PROJETO")
  [[ -f "$ENV_FILE" ]] && args+=(--env-file "$ENV_FILE")
  QA_TOOLKIT_IMAGE="$imagem" docker compose "${args[@]}" "$@"
}

subir() {
  compose "$1" up -d --no-build --wait --wait-timeout 120
}

smoke() {
  compose "$1" exec -T api qa-toolkit smoke-test \
    --url http://localhost:8000 \
    --prometheus-url http://prometheus:9090
}

# Remove BOM e espaços que um editor (ou o PowerShell) possa ter colocado no arquivo.
ANTERIOR="$(LC_ALL=C tr -d '\357\273\277\r\n ' <"$ESTADO" 2>/dev/null || true)"

if [[ "$IMAGEM" == *":local" ]]; then
  log "construindo a imagem $IMAGEM"
  docker build -t "$IMAGEM" .
elif docker image inspect "$IMAGEM" >/dev/null 2>&1; then
  log "usando a imagem $IMAGEM já presente na máquina"
else
  log "baixando a imagem $IMAGEM"
  docker pull "$IMAGEM"
fi

log "subindo os containers"
if subir "$IMAGEM" && smoke "$IMAGEM"; then
  mkdir -p .deploy
  echo "$IMAGEM" >"$ESTADO"
  log "deploy concluído: $IMAGEM"
  exit 0
fi

log "FALHA no deploy de $IMAGEM. Últimos logs da API:"
compose "$IMAGEM" logs --no-color --tail 50 api || true

if [[ -n "$ANTERIOR" && "$ANTERIOR" != "$IMAGEM" ]]; then
  log "rollback para a última imagem aprovada: $ANTERIOR"
  if subir "$ANTERIOR" && smoke "$ANTERIOR"; then
    log "rollback concluído"
  else
    log "ROLLBACK FALHOU: o ambiente precisa de intervenção manual"
  fi
else
  log "não há imagem anterior aprovada para rollback"
fi
exit 1
