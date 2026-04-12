# Paths
$dnlibPath = "C:\Users\dd200\Downloads\dnSpy-net-win64\bin\dnlib.dll"
$dllPath    = "C:\Users\dd200\AppData\Local\Programs\QuickLook\QuickLook.Plugin\QuickLook.Plugin.MarkdownViewer\QuickLook.Plugin.MarkdownViewer.dll"
$jsPath     = "C:\Users\dd200\Desktop\mermaid.min.js"
$resName    = "QuickLook.Plugin.MarkdownViewer.Resources.js\mermaid.min.js"

Add-Type -Path $dnlibPath

$module   = [dnlib.DotNet.ModuleDefMD]::Load($dllPath)
$jsBytes  = [System.IO.File]::ReadAllBytes($jsPath)

# Remove existing entry if present
$existing = $module.Resources | Where-Object { $_.Name -eq $resName }
if ($existing) { $module.Resources.Remove($existing) | Out-Null }

# Add embedded resource
$res = [dnlib.DotNet.EmbeddedResource]::new($resName, $jsBytes, [dnlib.DotNet.ManifestResourceAttributes]::Public)
$module.Resources.Add($res)

$tmpPath = $dllPath + ".tmp"
$module.Write($tmpPath)
Move-Item -Force $tmpPath $dllPath
Write-Host "Done."