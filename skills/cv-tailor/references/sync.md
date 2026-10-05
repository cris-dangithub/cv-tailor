# Google Drive sync

Keeps a copy of the applications in the candidate's Google Drive, with the same structure:
`<My Drive>/<folder>/applications/000001-company-role/<files>`. One way only (computer → Drive),
in the background: the user never waits for it.

## How it reaches Drive (explain it in plain words when asked)

- **Windows / macOS**: the official app *Google Drive for desktop* shows "My Drive" as a folder on
  the computer (Windows: usually `G:\My Drive` / `G:\Mi unidad`; macOS:
  `~/Library/CloudStorage/GoogleDrive-<email>/My Drive`). Copying a file there uploads it. No
  passwords or permissions are given to the skill. Download: https://www.google.com/drive/download/
- **Linux**: no official app. It works through `rclone` with a remote of type `drive` the user set
  up themselves (`rclone config`); the skill never handles their credentials.

## Setup (during the first setup, or whenever the user asks)

1. Ask whether they want their results in Google Drive. No → done (it stays off).
2. `cvt sync detect` → where Drive is.
   - Found one → confirm it with the user. Several (two accounts) → ask which.
   - `installed_but_not_running: true` → ask them to open Google Drive, then detect again.
   - Nothing → explain how to install it (link above) and leave it off; it can be turned on later.
3. Ask the folder inside Drive (default `cv-tailor`).
4. Ask what to sync (default: CVs in PDF, the application report and the offer). Options:
   `pdf`, `report`, `offer`, `yaml` (editable content), `review`, `positioning`.
5. `cvt sync setup --root "<root>" --folder "<folder>" --include pdf,report,offer [--method rclone]`
   (for rclone, `--root gdrive:` with the remote name). It writes a test file to check Drive is
   writable; `DRIVE_NOT_WRITABLE` → tell the user what failed.
6. `cvt sync run --all` once, to upload what already exists.

## When it runs

Automatically, in the background, every time an application changes: created, new file (PDF,
report), status change, new version, knowledge-base update, renumbering. Only files whose content
changed are copied; a file is written under a temporary name and then renamed, so Drive never
shows half a file. If Drive is unavailable (app closed, offline), the application stays pending
and goes up with the next sync.

## What the user can ask

| The user says | Do |
|---|---|
| "is it in Drive?" / "did it upload?" | `cvt sync status [--app <id>]` (local state only, instant) and answer in plain words |
| "upload everything now" | `cvt sync run --all` |
| "stop syncing" | `cvt sync disable` |
| "change the folder / what is synced" | `cvt sync setup ...` again with the new values, then `cvt sync run --all` |
| "clean up Drive" | `cvt sync clean` lists files this sync uploaded whose local file no longer exists; delete them with `--yes` **only after the user confirms the list** |

It never deletes anything in Drive on its own, and never touches files it didn't upload. A
renumbering (after 999999) moves the folders in Drive instead of uploading them again.

## State (for answers, never read Drive)

`.cv-tailor/sync/state.json` (per file: content hash, place in Drive, date, ok/error),
`.cv-tailor/sync/runs/` (one record per run: copied, moved, errors, duration),
`pending.json` (waiting for Drive), `worker.log` (background worker output, for troubleshooting).
