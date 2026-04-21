param(
    [Parameter(Mandatory=$true)]
    [string]$MailboxName,

    [Parameter(Mandatory=$true)]
    [string[]]$Folders,

    [Parameter(Mandatory=$true)]
    [string]$OutputDir,

    [string]$Since = "25h"
)

function Strip-Html($html) {
    if (-not $html) { return "" }
    # Remove entire <style>, <head>, and <script> blocks (content + tags)
    $text = $html -replace '(?is)<style[^>]*>.*?</style>', ''
    $text = $text  -replace '(?is)<head[^>]*>.*?</head>',  ''
    $text = $text  -replace '(?is)<script[^>]*>.*?</script>', ''
    # Block-level tags → newline so paragraph breaks are preserved
    $text = $text -replace '(?i)<(br\s*/?>|/p>|/div>|/tr>|/li>|/h[1-6]>)', "`n"
    # Remove all remaining tags
    $text = $text -replace '<[^>]+>', ' '
    # Decode common HTML entities
    $text = $text -replace '&nbsp;',  ' '
    $text = $text -replace '&amp;',   '&'
    $text = $text -replace '&lt;',    '<'
    $text = $text -replace '&gt;',    '>'
    $text = $text -replace '&quot;',  '"'
    $text = $text -replace '&#39;',   "'"
    # Collapse runs of spaces/tabs to a single space per line
    $text = ($text -split "`n" | ForEach-Object { $_ -replace '[ \t]+', ' ' } | ForEach-Object { $_.Trim() }) -join "`n"
    # Collapse runs of blank lines to a single newline
    $text = $text -replace '(\r?\n){3,}', "`n`n"
    return $text.Trim()
}

function Truncate-Body($text, [int]$max = 1000) {
    if ($text.Length -le $max) { return $text }
    return $text.Substring(0, $max) + "`n[truncated]"
}


function Parse-Since($since) {
    if ($since -match '^(\d+)([hd])$') {
        $value = [int]$matches[1]
        $unit  = $matches[2]

        switch ($unit) {
            'h' { return (Get-Date).AddHours(-$value) }
            'd' { return (Get-Date).AddDays(-$value) }
        }
    } else {
        throw "Invalid time format. Use e.g. 7h or 2d."
    }
}

$sinceTime = Parse-Since $Since

if ($sinceTime -lt (Get-Date).AddDays(-7)) {
    throw "Timestamp cannot be older than 7 days."
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace("MAPI")

$mailbox = $ns.Folders | Where-Object { $_.Name -eq $MailboxName }
if (-not $mailbox) {
    throw "Mailbox not found: $MailboxName"
}

$sessionTag = (Get-Date -Format "yyyyMMddTHHmmssZ")
$written = 0

foreach ($folderName in $Folders) {
    $folder = $mailbox.Folders | Where-Object { $_.Name -eq $folderName }
    if (-not $folder) {
        Write-Warning "Folder not found: $folderName"
        continue
    }

    $items = $folder.Items
    $items.Sort("[ReceivedTime]", $true)

    $filter = "[ReceivedTime] >= '" + $sinceTime.ToString("g") + "'"
    $restricted = $items.Restrict($filter)

    foreach ($item in $restricted) {
        if ($item -is [__ComObject]) {
            try {
                if (-not ($item.MessageClass -like "IPM.Note*")) {
                    continue
                }

                # Generate a 12-char hex message ID
                $msgId = [System.Guid]::NewGuid().ToString("N").Substring(0, 12)

                $receivedUtc = $item.ReceivedTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                $senderDisplay = $item.SenderName
                $senderEmail   = ""
                try { $senderEmail = $item.SenderEmailAddress } catch {}

                $senderFull = if ($senderEmail -and $senderEmail -notlike "EX:/o=*") {
                    "$senderDisplay <$senderEmail>"
                } else {
                    $senderDisplay
                }

                # Prefer HTML body (richer structure) but fall back to plain text.
                # Strip HTML tags, normalise whitespace, truncate to 1000 chars.
                $rawBody = if ($item.HTMLBody) { Strip-Html $item.HTMLBody } else { $item.Body }
                $bodyText = Truncate-Body ($rawBody -replace '[ \t]+', ' ' -replace '(\r?\n){3,}', "`n`n").Trim()

                # Build the prompt field — formatted for LLM consumption
                $prompt = "Subject: $($item.Subject)`nFrom: $senderFull`nReceived: $($item.ReceivedTime.ToString('yyyy-MM-dd HH:mm:ss'))`nMailbox: $MailboxName`nFolder: $folderName`n`n$bodyText"

                # Build YAML content manually to avoid dependency on a YAML module
                # Values are block-scalar or quoted to handle special characters safely.
                $indentedPrompt = ($prompt -split "`n" | ForEach-Object { "  " + $_ }) -join "`n"

                $yaml = @"
msg_id: $msgId
from_agent: outlook
from_session: outlook-$sessionTag
reply_to_session: null
prompt: |
$indentedPrompt
sent_at: "$receivedUtc"
outlook_entry_id: "$($item.EntryID)"
outlook_store_id: "$($item.Parent.StoreID)"
outlook_mailbox: "$MailboxName"
outlook_folder: "$folderName"
outlook_subject: "$($item.Subject -replace '"', '\"')"
outlook_sender: "$($senderFull -replace '"', '\"')"
outlook_received: "$($item.ReceivedTime.ToString('yyyy-MM-ddTHH:mm:ss'))"
"@

                $outPath = Join-Path $OutputDir "$msgId.yaml"
                [System.IO.File]::WriteAllText($outPath, $yaml, [System.Text.Encoding]::UTF8)
                $written++
                Write-Host "Wrote $outPath"

            } catch {
                Write-Warning "Skipped item: $_"
            }
        }
    }
}

Write-Host "Done. $written message(s) written to $OutputDir"
