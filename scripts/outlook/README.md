# Outlook Integration Scripts

These PowerShell scripts bridge the Council email agent (running in a Linux
container) with Outlook on the Windows host. Communication happens entirely
through files in a shared directory.

## Scripts

### `GetOutlook.ps1`

Reads emails from one or more Outlook folders and writes each message as a
YAML file into a target directory. The YAML files follow the Council mailbox
format, so they are picked up by the email agent's inbox automatically.

**Parameters**

| Parameter | Required | Description |
|---|---|---|
| `-MailboxName` | Yes | Display name of the Outlook mailbox (e.g. `user@example.com`) |
| `-Folders` | Yes | Array of folder names to read (e.g. `@("Inbox", "Work")`) |
| `-OutputDir` | Yes | Directory to write YAML files into (e.g. `data\messages\email\inbox`) |
| `-Since` | No | How far back to look. Format: `<N>h` or `<N>d`. Default: `25h`. Max: `7d` |

**Example**

```powershell
.\GetOutlook.ps1 `
    -MailboxName "user@example.com" `
    -Folders @("Inbox", "Work") `
    -OutputDir "D:\dev\Council\data\messages\email\inbox" `
    -Since "25h"
```

---

### `ManipulateOutlook.ps1`

Performs a single action on an existing Outlook item identified by its
`EntryID` and `StoreID` (both are emitted by `GetOutlook.ps1` as
`outlook_entry_id` / `outlook_store_id`).

**Parameters**

| Parameter | Required | Description |
|---|---|---|
| `-Action` | Yes | One of: `move`, `flag`, `unflag`, `read`, `unread` |
| `-EntryId` | Yes | Outlook EntryID of the item |
| `-StoreId` | Yes | Outlook StoreID of the item |
| `-DestinationFolder` | move only | Target folder name (e.g. `Processed`) |

**Example**

```powershell
.\ManipulateOutlook.ps1 -Action move -EntryId "000ABC..." -StoreId "000DEF..." -DestinationFolder "Processed"
.\ManipulateOutlook.ps1 -Action flag  -EntryId "000ABC..." -StoreId "000DEF..."
```

---

### `DraftOutlook.ps1`

Creates a new draft message in the Drafts folder of the specified mailbox.
Does **not** send the message — human review is required before sending.

**Parameters**

| Parameter | Required | Description |
|---|---|---|
| `-MailboxName` | Yes | Display name of the target mailbox |
| `-To` | Yes | Recipient address(es) |
| `-Subject` | Yes | Message subject |
| `-Body` | Yes | Plain-text message body |

**Example**

```powershell
.\DraftOutlook.ps1 `
    -MailboxName "user@example.com" `
    -To "alice@example.com" `
    -Subject "Re: Q1 Budget" `
    -Body "Hi Alice,`n`nThank you for sending this over..."
```

---

### `ExecuteOutlookCommands.ps1`

Reads a `commands.yaml` file written by the Council email agent and
dispatches each command to `ManipulateOutlook.ps1` or `DraftOutlook.ps1`.
Archives the commands file to a `processed/` subdirectory on completion.

**Parameters**

| Parameter | Required | Description |
|---|---|---|
| `-CommandsFile` | Yes | Full path to the `commands.yaml` file |
| `-ScriptsDir` | No | Directory containing the other scripts. Defaults to the same directory as this script |

**Command file format** (`commands.yaml`)

```yaml
commands:
  - action: move
    entry_id: "000ABC..."
    store_id: "000DEF..."
    destination_folder: Processed

  - action: flag
    entry_id: "000ABC..."
    store_id: "000DEF..."

  - action: unflag
    entry_id: "000ABC..."
    store_id: "000DEF..."

  - action: read
    entry_id: "000ABC..."
    store_id: "000DEF..."

  - action: unread
    entry_id: "000ABC..."
    store_id: "000DEF..."

  - action: draft
    mailbox: "user@example.com"
    to: "alice@example.com"
    subject: "Re: Q1 Budget"
    body: "Hi Alice, ..."
```

> **Note:** `ExecuteOutlookCommands.ps1` works without any extra modules. If
> the optional [`powershell-yaml`](https://github.com/cloudbase/powershell-yaml)
> module is installed it will be used; otherwise the script falls back to a
> built-in parser.

---

## Windows Task Scheduler Setup

Two scheduled tasks are recommended:

### Task 1 — Fetch emails into the agent inbox

Runs `GetOutlook.ps1` on a schedule to pull new emails into the Council
mailbox directory.

1. Open **Task Scheduler** → **Create Task**
2. **General** tab
   - Name: `Council - Fetch Outlook Emails`
   - Run whether user is logged on or not: ✓
   - Run with highest privileges: ✓
3. **Triggers** tab → **New**
   - Begin the task: **On a schedule**
   - Daily, repeat every **1 hour** (or adjust to preference)
4. **Actions** tab → **New**
   - Program: `powershell.exe`
   - Arguments:
     ```
     -NonInteractive -ExecutionPolicy Bypass -File "D:\dev\Council\scripts\outlook\GetOutlook.ps1" -MailboxName "user@example.com" -Folders @("Inbox") -OutputDir "D:\dev\Council\data\messages\email\inbox" -Since "25h"
     ```
   - Replace `user@example.com`, folder names, and paths as needed.
5. **Conditions** tab — uncheck "Start the task only if the computer is on AC power" if needed.
6. Click **OK**.

### Task 2 — Execute agent-generated Outlook commands

Runs `ExecuteOutlookCommands.ps1` periodically to apply moves, flags, and
drafts that the email agent has queued.

1. Open **Task Scheduler** → **Create Task**
2. **General** tab
   - Name: `Council - Execute Outlook Commands`
   - Run whether user is logged on or not: ✓
   - Run with highest privileges: ✓
3. **Triggers** tab → **New**
   - Begin the task: **On a schedule**
   - Daily, repeat every **15 minutes** (should run more frequently than Task 1)
4. **Actions** tab → **New**
   - Program: `powershell.exe`
   - Arguments:
     ```
     -NonInteractive -ExecutionPolicy Bypass -File "D:\dev\Council\scripts\outlook\ExecuteOutlookCommands.ps1" -CommandsFile "D:\dev\Council\data\workspace\outlook\commands\commands.yaml"
     ```
5. Click **OK**.

> **Tip:** The `-ExecutionPolicy Bypass` flag is required if your system
> policy is set to `Restricted` or `AllSigned`. Alternatively, sign the
> scripts or adjust the machine policy.

---

## Shared Directory Layout

```
data/
  messages/
    email/
      inbox/        ← GetOutlook.ps1 writes one .yaml per email here
      processed/    ← engine moves files here after the agent handles them
  workspace/
    outlook/
      commands/
        commands.yaml    ← agent writes this; ExecuteOutlookCommands.ps1 reads it
        processed/       ← archived command files (timestamped)
```
