# Check the Windows host for the DE4SDV AAOS SDV reference proof.
# Run from PowerShell. This script does not change the machine.

$ErrorActionPreference = "Continue"

function Check($label, $command) {
    Write-Host "`n[$label]" -ForegroundColor Cyan
    try { Invoke-Expression $command } catch { Write-Host $_ -ForegroundColor Yellow }
}

Write-Host "DE4SDV AAOS SDV reference-host preflight" -ForegroundColor Green
Write-Host "Read-only checks; no credentials or configuration changes are performed."

Check "Windows version" "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber"
Check "CPU and memory" "Get-CimInstance Win32_ComputerSystem | Select-Object NumberOfLogicalProcessors, @{N='RAM_GiB';E={[math]::Round(`$_.TotalPhysicalMemory/1GB,1)}}"
Check "Virtualization" "Get-CimInstance Win32_Processor | Select-Object Name, VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions"
Check "System disk" "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Free_GiB';E={[math]::Round(`$_.Free/1GB,1)}}, @{N='Used_GiB';E={[math]::Round(`$_.Used/1GB,1)}}"
Check "WSL" "wsl.exe --status; wsl.exe --list --verbose"
Check "Docker" "docker version; docker info --format 'server={{.ServerVersion}} arch={{.Architecture}}'"
Check "ADB" "adb.exe version"
Check "Fastboot" "fastboot.exe --version"

Write-Host "`nMinimum recommendation:" -ForegroundColor Yellow
Write-Host "  x86_64 CPU, 64+ GiB RAM, 400+ GiB free Linux-backed storage"
Write-Host "  WSL2 Ubuntu 22.04, source under the WSL ext4 filesystem (not /mnt/c)"
Write-Host "  Android SDK/platform tools with adb, if a device/emulator will be used"
