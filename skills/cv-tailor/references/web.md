# Web app

A local web app over the same workspace, for people who would rather not live in a chat window:
paste offers, follow the agent while it works, answer its questions, approve what it asks, keep
the status of every application, and open, compare or download the PDFs. It works from a phone
too, on the same network or through a tunnel.

It does not replace the skill: every conversation it starts is an ordinary Claude Code session
in the workspace, using this skill, so the rules here still apply. Those sessions also appear
in Claude Code's own history.

## Starting it

```
cvt setup-env --web        # once: installs the optional web dependencies
cvt web                    # http://127.0.0.1:8765, this computer only; opens the browser
cvt web --lan              # also other devices on the network (prints the address and a QR)
cvt web --public           # any host name, for a tunnel: `ngrok http 8765`, cloudflared...
```

When the user asks for "the app", "the web interface" or to use it from their phone:

1. `cvt doctor`. The line `web app (cvt web)` must be ok. If it is not, run `cvt setup-env --web`.
   The UI comes already built, so Node is not needed.
2. Start `cvt web` as a background process and give them the URL it prints:
   - add `--lan` if they mention a phone or another device on the same network;
   - add `--public` if they want it from anywhere through a tunnel.
3. Everyone signs in (see below). If `--lan` or `--public` stops with `DEFAULT_ADMIN`, the
   superuser password has not been set yet.
   - Ask the user for one and write it to `<ws>/.cv-tailor/web/.env`; never choose it yourself.
   - Never put it in the repository.

If the `Claude Code CLI` line of `cvt doctor` says it is missing, or the app shows the sign-in
notice, the user has to run `claude auth login` in a terminal once. The desktop app's login
does not cover the CLI. Never run the login for them.

## Accounts

- **The superuser** comes from the environment:
  - variables `CVT_ADMIN_USER` and `CVT_ADMIN_PASSWORD`;
  - otherwise from `<ws>/.cv-tailor/web/.env` (`KEY=VALUE` lines);
  - otherwise `admin` / `admin`, which works only on this computer.
  - It manages users and cannot be deleted from the app. Changing its password means changing
    the variable and restarting.
- **Creating accounts:** anyone can create one on the sign-in screen. The first account is
  active at once; every later one waits until the superuser approves it on the Users screen,
  which shows a dot while someone is waiting.
- **What the superuser can do:** approve, reject, disable or enable an account, set a new
  password, sign someone out everywhere, and delete an account.
- **Sessions** never expire; they end when the user signs out. Disabling an account, deleting
  it, or giving it a new password signs it out everywhere.
- **Shared data:** every user sees the same workspace. Conversations record who wrote each
  message and who approved each action.

## What it does

| Screen | What |
|---|---|
| Desk | paste one or more offers (text or link) and choose high or medium effort; each offer opens its own session, queued up to `concurrency` at once |
| Applications | index or board by status; search (same scoring as `cvt index search`); change status with a note |
| Application | the route of statuses, the CV per language and version, report, offer, positioning, feedback log; feedback continues the application's session |
| Documents | every PDF; preview, download, ZIP of a selection |
| Conversations | every session; streaming replies, collapsed tool steps, approval cards, stop |
| Styles | switch the active style; create one from a sample CV (a session following `styles.md`) |
| Settings | model (default `claude-opus-5-5`), default effort, compaction window, concurrency, UI language, network access, remembered approvals |
| Users | superuser only: accounts waiting for approval and everyone else |

## How it runs the agent

- One message is one turn: `claude` starts with `--resume <session>` in the workspace, with the
  chosen `--effort` and `--autocompact` (100k tokens by default, so long chats stay cheap). It
  then exits. It is the user's own installed CLI and login.
- Questions to the user (step 5 of `generate.md`) arrive as a normal reply. The thread is
  marked "needs you" and the user answers in it, so nothing in this skill needs to change for
  the web app.
- Without asking, the agent may:
  - read anything;
  - write inside the workspace;
  - write into the pool when its managing skill accepts write-back;
  - run `cvt.py` and read-only shell commands;
  - fetch the web and use subagents.

  Anything else shows an approval card. "Always allow" stores the rule in
  `.cv-tailor/web/settings.json`.
- Index writes take a workspace lock (`.cv-tailor/index.lock`), so the app and any number of
  sessions can create applications at the same time without sharing an id.

## Where its data lives

`<ws>/.cv-tailor/web/` holds:

- `.env`: the superuser, if set there;
- `users.json`: password hashes, never the passwords themselves;
- `sessions.json`: hashes of session tokens;
- `settings.json`;
- `threads/`: what the browser shows of each conversation; the real transcript is Claude
  Code's;
- `uploads/`: sample CVs sent for new styles.

The folder is ignored by git. Deleting it signs everyone out and empties the app's chat
history, but no application or CV is lost.
