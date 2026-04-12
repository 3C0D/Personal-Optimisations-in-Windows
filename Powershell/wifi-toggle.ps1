# Script de gestion automatique Wi-Fi/Ethernet
# Désactive le Wi-Fi quand l'Ethernet est connecté

# Détecter les adaptateurs
$ethernet = Get-NetAdapter | Where-Object { 
    $_.Status -eq "Up" -and 
    ($_.InterfaceDescription -like "*Ethernet*" -or $_.Name -like "*Ethernet*")
}

$wifi = Get-NetAdapter | Where-Object { 
    $_.InterfaceDescription -like "*Wi-Fi*" -or $_.InterfaceDescription -like "*Wireless*" 
}

if ($ethernet) {
    Write-Host "Ethernet actif détecté - Désactivation du Wi-Fi..." -ForegroundColor Green
    
    # Déconnecter et désactiver complètement le Wi-Fi
    netsh wlan disconnect | Out-Null
    netsh interface set interface name="$($wifi.Name)" admin=disable
    
    Write-Host "Wi-Fi complètement désactivé." -ForegroundColor Yellow
}

# Afficher l'état final
# Write-Host "`nÉtat des interfaces :" -ForegroundColor White
# netsh interface show interface

# Read-Host -Prompt "`nAppuyez sur Entrée pour fermer"
