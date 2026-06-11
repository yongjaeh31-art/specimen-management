$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$hostName = Read-Host "PostgreSQL host (default: localhost)"
if ([string]::IsNullOrWhiteSpace($hostName)) { $hostName = "localhost" }

$port = Read-Host "PostgreSQL port (default: 5432)"
if ([string]::IsNullOrWhiteSpace($port)) { $port = "5432" }

$dbName = Read-Host "Database name (default: specimen_routing)"
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "specimen_routing" }

$user = Read-Host "PostgreSQL user (default: postgres)"
if ([string]::IsNullOrWhiteSpace($user)) { $user = "postgres" }

$password = Read-Host "PostgreSQL password"
$adminPassword = Read-Host "App admin password (default: admin1234)"
if ([string]::IsNullOrWhiteSpace($adminPassword)) { $adminPassword = "admin1234" }

$check = Test-NetConnection -ComputerName $hostName -Port ([int]$port)
if (-not $check.TcpTestSucceeded) {
    Write-Host ""
    Write-Host "PostgreSQL is not reachable at ${hostName}:${port}."
    Write-Host "Install/start PostgreSQL first, then run this script again."
    Read-Host "Press Enter to close"
    exit 1
}

$envText = @"
DATABASE_URL=postgresql+psycopg2://${user}:${password}@${hostName}:${port}/${dbName}
ADMIN_PASSWORD=${adminPassword}
"@

Set-Content -Path ".env" -Value $envText -Encoding UTF8
Write-Host ""
Write-Host ".env has been updated for PostgreSQL."
Write-Host "Restart start_app.bat to use PostgreSQL."
Read-Host "Press Enter to close"
