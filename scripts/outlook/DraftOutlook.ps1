param(
    [Parameter(Mandatory=$true)]
    [string]$MailboxName,

    [Parameter(Mandatory=$true)]
    [string]$To,

    [Parameter(Mandatory=$true)]
    [string]$Subject,

    [Parameter(Mandatory=$true)]
    [string]$Body
)

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace("MAPI")

$mailbox = $ns.Folders | Where-Object { $_.Name -eq $MailboxName }
if (-not $mailbox) {
    throw "Mailbox not found: $MailboxName"
}

$drafts = $mailbox.Folders | Where-Object { $_.DefaultItemType -eq 0 -and $_.Name -like "*Draft*" }
if (-not $drafts) {
    # Fallback: use the default Drafts folder
    $drafts = $ns.GetDefaultFolder(16)  # olFolderDrafts = 16
}

$mail = $outlook.CreateItem(0)  # olMailItem = 0
$mail.To      = $To
$mail.Subject = $Subject
$mail.Body    = $Body

# Save to Drafts (do not send)
$mail.Save()

# Move to the correct mailbox Drafts if the default ended up elsewhere
if ($drafts -and ($mail.Parent.StoreID -ne $drafts.StoreID)) {
    $mail.Move($drafts) | Out-Null
}

Write-Host "Draft saved: '$Subject' -> $To"
