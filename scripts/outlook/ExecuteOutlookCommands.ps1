param(
    [Parameter(Mandatory=$true)]
    [string]$CommandsFile,

    [string]$ScriptsDir = $PSScriptRoot
)

if (-not (Test-Path $CommandsFile)) {
    Write-Host "No commands file found at $CommandsFile — nothing to do."
    exit 0
}

# Load powershell-yaml if available; otherwise parse manually via ConvertFrom-Json workaround.
# We keep it dependency-free by using a lightweight YAML reader for our known schema.
function Read-CommandsYaml($path) {
    # Use a simple line-by-line parser for the known flat list structure.
    # Relies on the fixed indentation produced by Python's yaml.dump.
    $content = Get-Content $path -Raw -Encoding UTF8
    # Convert to JSON via PowerShell's pipeline — requires powershell-yaml module OR
    # we parse the known structure ourselves.
    # Attempt module-based load first; fall back to manual parse.
    if (Get-Module -ListAvailable -Name powershell-yaml -ErrorAction SilentlyContinue) {
        Import-Module powershell-yaml -ErrorAction Stop
        $data = ConvertFrom-Yaml $content
        return $data.commands
    }

    # Manual fallback: parse "- key: value" blocks separated by "  - action:"
    $commands = @()
    $current  = $null
    foreach ($line in ($content -split "`n")) {
        if ($line -match '^\s*-\s+action:\s*"?([^"]+)"?\s*$') {
            if ($current) { $commands += $current }
            $current = @{ action = $matches[1].Trim() }
        } elseif ($current -and $line -match '^\s+(\w+):\s*"?(.+?)"?\s*$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim()
            $current[$key] = $value
        }
    }
    if ($current) { $commands += $current }
    return $commands
}

$manipulateScript = Join-Path $ScriptsDir "ManipulateOutlook.ps1"
$draftScript      = Join-Path $ScriptsDir "DraftOutlook.ps1"

foreach ($s in @($manipulateScript, $draftScript)) {
    if (-not (Test-Path $s)) {
        throw "Required script not found: $s"
    }
}

$commands = Read-CommandsYaml $CommandsFile
if (-not $commands -or $commands.Count -eq 0) {
    Write-Host "Commands file is empty — nothing to do."
    Remove-Item $CommandsFile -Force
    exit 0
}

Write-Host "Executing $($commands.Count) Outlook command(s)..."
$errors = 0

foreach ($cmd in $commands) {
    $action = $cmd.action
    Write-Host "  [$action] $(if ($cmd.subject) { $cmd.subject } elseif ($cmd.entry_id) { $cmd.entry_id } else { '' })"

    try {
        switch ($action) {
            { $_ -in @("move", "flag", "unflag", "read", "unread") } {
                $args = @(
                    "-Action", $action,
                    "-EntryId", $cmd.entry_id,
                    "-StoreId", $cmd.store_id
                )
                if ($action -eq "move") {
                    $args += @("-DestinationFolder", $cmd.destination_folder)
                }
                & $manipulateScript @args
            }

            "draft" {
                & $draftScript `
                    -MailboxName $cmd.mailbox `
                    -To          $cmd.to `
                    -Subject     $cmd.subject `
                    -Body        $cmd.body
            }

            default {
                Write-Warning "Unknown action '$action' — skipped."
                $errors++
            }
        }
    } catch {
        Write-Warning "Error executing [$action]: $_"
        $errors++
    }
}

# Archive or delete the commands file after execution
$archiveDir = Join-Path (Split-Path $CommandsFile) "processed"
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
}
$timestamp   = Get-Date -Format "yyyyMMddTHHmmss"
$archiveName = "commands_$timestamp.yaml"
Move-Item $CommandsFile (Join-Path $archiveDir $archiveName) -Force

Write-Host "Done. Archived to $archiveName. Errors: $errors"
if ($errors -gt 0) { exit 1 }
