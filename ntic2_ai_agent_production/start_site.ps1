# Script PowerShell pour démarrer le site
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEMARRAGE DU SITE ISTA NTIC" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Arrêter les processus existants qui utilisent les ports
Write-Host "[0/2] Arrêt des processus existants..." -ForegroundColor Yellow
try {
    # Arrêter les processus Node.js (frontend)
    $nodeProcesses = Get-Process -Name node -ErrorAction SilentlyContinue
    if ($nodeProcesses) {
        Write-Host "  Arrêt de $($nodeProcesses.Count) processus Node.js..." -ForegroundColor Gray
        Stop-Process -Name node -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
    
    # Arrêter les processus Python qui utilisent le port 5000 (backend)
    $backendProcesses = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($backendProcesses) {
        foreach ($pid in $backendProcesses) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            } catch {}
        }
        Write-Host "  Port 5000 libéré..." -ForegroundColor Gray
    }
    
    # Arrêter les processus qui utilisent le port 5173 (frontend)
    $frontendProcesses = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($frontendProcesses) {
        foreach ($pid in $frontendProcesses) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            } catch {}
        }
        Write-Host "  Port 5173 libéré..." -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds 2
} catch {
    Write-Host "  Aucun processus à arrêter..." -ForegroundColor Gray
}

Write-Host "[1/2] Démarrage du backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python -m app.main"
Start-Sleep -Seconds 3

Write-Host "[2/2] Démarrage du frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SITE DÉMARRÉ !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ouvrez http://localhost:5173 dans votre navigateur" -ForegroundColor Yellow
Write-Host ""
Write-Host "Appuyez sur une touche pour ouvrir le site dans le navigateur..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:5173"
