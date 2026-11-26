<#
.SYNOPSIS
    Deploy da API do qa-toolkit com Docker Compose (versão para Windows/PowerShell).

.DESCRIPTION
    Mesmas etapas do scripts/deploy.sh:
      1. obtém a imagem (pull do registro, ou build se for a imagem local)
      2. sobe API, Prometheus e Grafana e espera a API ficar saudável
      3. roda o teste de fumaça de dentro do container da API
      4. se o teste falhar, volta para a última imagem aprovada (rollback)

.EXAMPLE
    .\scripts\deploy.ps1 -Ambiente local
.EXAMPLE
    .\scripts\deploy.ps1 -Ambiente homologacao -Imagem ghcr.io/joaovictorrochaferreira/assistente-qa:latest
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("homologacao", "producao", "local")]
    [string]$Ambiente,

    [string]$Imagem = "qa-toolkit:local"
)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

$Projeto = "qa-$Ambiente"
$EnvFile = "deploy/$Ambiente.env"
$Estado = ".deploy/$Ambiente.imagem"

function Write-Log([string]$Mensagem) {
    $hora = (Get-Date).ToUniversalTime().ToString("HH:mm:ss")
    Write-Host "[deploy $Ambiente $hora] $Mensagem"
}

function Invoke-Compose([string]$ImagemAlvo, [string[]]$Argumentos) {
    $env:QA_TOOLKIT_IMAGE = $ImagemAlvo
    $base = @("compose", "-p", $Projeto)
    if (Test-Path $EnvFile) { $base += @("--env-file", $EnvFile) }
    # Out-Host: a saída do docker vai para a tela e não vira parte do valor de retorno.
    & docker @($base + $Argumentos) | Out-Host
    return $LASTEXITCODE -eq 0
}

function Test-Deploy([string]$ImagemAlvo) {
    $subiu = Invoke-Compose $ImagemAlvo @("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
    if (-not $subiu) { return $false }
    return Invoke-Compose $ImagemAlvo @(
        "exec", "-T", "api", "qa-toolkit", "smoke-test",
        "--url", "http://localhost:8000", "--prometheus-url", "http://prometheus:9090"
    )
}

$Anterior = if (Test-Path $Estado) { (Get-Content $Estado -Raw).Trim() } else { "" }

if ($Imagem.EndsWith(":local")) {
    Write-Log "construindo a imagem $Imagem"
    docker build -t $Imagem . | Out-Host
} else {
    docker image inspect $Imagem 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Log "usando a imagem $Imagem já presente na máquina"
    } else {
        Write-Log "baixando a imagem $Imagem"
        docker pull $Imagem | Out-Host
    }
}
if ($LASTEXITCODE -ne 0) { throw "não foi possível obter a imagem $Imagem" }

Write-Log "subindo os containers"
if (Test-Deploy $Imagem) {
    New-Item -ItemType Directory -Force .deploy | Out-Null
    # Grava sem BOM, para o arquivo ser lido igual pelo deploy.sh.
    [System.IO.File]::WriteAllText((Join-Path $Raiz $Estado), $Imagem)
    Write-Log "deploy concluído: $Imagem"
    exit 0
}

Write-Log "FALHA no deploy de $Imagem. Últimos logs da API:"
Invoke-Compose $Imagem @("logs", "--no-color", "--tail", "50", "api") | Out-Null

if ($Anterior -and $Anterior -ne $Imagem) {
    Write-Log "rollback para a última imagem aprovada: $Anterior"
    if (Test-Deploy $Anterior) {
        Write-Log "rollback concluído"
    } else {
        Write-Log "ROLLBACK FALHOU: o ambiente precisa de intervenção manual"
    }
} else {
    Write-Log "não há imagem anterior aprovada para rollback"
}
exit 1
