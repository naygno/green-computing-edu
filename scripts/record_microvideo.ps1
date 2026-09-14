<#
.SYNOPSIS
  Grava microvídeos verticais de 15 a 20 segundos diretamente do Android Studio AVD.
.EXAMPLE
  .\scripts\record_microvideo.ps1 -Passo "passo1_dns_privado" -Segundos 15
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$Passo,
    [int]$Segundos = 18
)

$OutputDir = "assets/videos"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$DevicePath = "/sdcard/temp_microvideo.mp4"
$LocalPath = "$OutputDir/$Passo.mp4"

Write-Host "🎥 Iniciando gravação do $Passo ($Segundos segundos)..." -ForegroundColor Cyan
Write-Host "👉 Execute os toques no Emulador AGORA!" -ForegroundColor Yellow

# Dispara a captura direta no framebuffer do emulador (9:16 nativo a 8Mbps)
adb shell screenrecord --size 1080x1920 --bit-rate 8000000 --time-limit $Segundos $DevicePath

Write-Host "⏳ Transferindo vídeo para o repositório..." -ForegroundColor Green
adb pull $DevicePath $LocalPath
adb shell rm $DevicePath

Write-Host "✅ Microvídeo salvo com sucesso em: $LocalPath" -ForegroundColor Green