param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("move", "flag", "unflag", "read", "unread")]
    [string]$Action,

    [Parameter(Mandatory=$true)]
    [string]$EntryId,

    [Parameter(Mandatory=$true)]
    [string]$StoreId,

    [string]$DestinationFolder  # Required when Action = "move"
)

if ($Action -eq "move" -and -not $DestinationFolder) {
    throw "DestinationFolder is required when Action is 'move'."
}

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace("MAPI")

$item = $ns.GetItemFromID($EntryId, $StoreId)
if (-not $item) {
    throw "Item not found: EntryId=$EntryId StoreId=$StoreId"
}

switch ($Action) {
    "move" {
        # Walk up to the store root then find the target folder by name
        $store = $ns.Stores | Where-Object { $_.StoreID -eq $StoreId }
        if (-not $store) {
            throw "Store not found: $StoreId"
        }
        $rootFolder = $store.GetRootFolder()

        function Find-Folder($parent, $name) {
            foreach ($f in $parent.Folders) {
                if ($f.Name -eq $name) { return $f }
                $found = Find-Folder $f $name
                if ($found) { return $found }
            }
            return $null
        }

        $target = Find-Folder $rootFolder $DestinationFolder
        if (-not $target) {
            throw "Destination folder not found: $DestinationFolder"
        }
        $item.Move($target) | Out-Null
        Write-Host "Moved item to '$DestinationFolder'"
    }

    "flag" {
        $item.FlagRequest = "Follow up"
        $item.FlagStatus = 1  # olFlagMarked
        $item.Save()
        Write-Host "Flagged item"
    }

    "unflag" {
        $item.FlagStatus = 0  # olNoFlag
        $item.Save()
        Write-Host "Unflagged item"
    }

    "read" {
        $item.UnRead = $false
        $item.Save()
        Write-Host "Marked item as read"
    }

    "unread" {
        $item.UnRead = $true
        $item.Save()
        Write-Host "Marked item as unread"
    }
}
