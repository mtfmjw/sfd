$OutputEncoding = [System.Console]::OutputEncoding = [System.Console]::InputEncoding = [System.Text.Encoding]::UTF8
Set-Location "G:\マイドライブ\podman"
podman compose -f postgresql18_compose.yaml  up -d
