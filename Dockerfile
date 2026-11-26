# Imagem da API do qa-toolkit.
# Estágio 1 (build): gera o pacote wheel a partir do código.
# Estágio 2 (runtime): instala só o wheel, sem código-fonte nem ferramentas de build,
# e roda com um usuário sem privilégios.

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
WORKDIR /src
RUN pip install --no-cache-dir build==1.2.2
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m build --wheel --outdir /dist

FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="qa-toolkit" \
      org.opencontainers.image.description="API que valida a skill cenarios-de-teste e arquivos .feature" \
      org.opencontainers.image.source="https://github.com/joaovictorrochaferreira/assistente-qa"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    QA_TOOLKIT_AMBIENTE=local

# Aplica as correções de segurança já publicadas para os pacotes do sistema.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=build /dist/ /tmp/dist/
# Instala o wheel local; as versões das dependências têm limites mínimos no pyproject.toml.
# Melhoria futura: um arquivo de lock com versões exatas (veja a análise no README).
# O pip e o setuptools da imagem base podem ter falhas conhecidas: atualiza antes de instalar.
# hadolint ignore=DL3013
RUN pip install --upgrade "pip>=26.2" "setuptools>=78.1.1" \
 && pip install "$(ls /tmp/dist/qa_toolkit-*.whl)[api]" \
 && rm -rf /tmp/dist

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

CMD ["qa-toolkit", "serve", "--host", "0.0.0.0", "--port", "8000"]
