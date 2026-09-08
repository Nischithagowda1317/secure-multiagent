param([string]$HostAddress = "127.0.0.1", [int]$Port = 8000)
& "$PSScriptRoot\run_dashboard.ps1" -HostAddress $HostAddress -Port $Port -NoReload
