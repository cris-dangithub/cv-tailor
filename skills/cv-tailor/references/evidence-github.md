# Evidence from GitHub (pool sources of type `github`)

Goal: for every line of the CV, be able to say **where it comes from**. Read-only, always:
never clone, push, comment or change anything; never quote private repository names in a CV.

## 0. Identities first

A repository with many contributors is not the candidate's work. Establish every name/login/email
they appear with **before** counting anything (work and personal accounts, two or three
signatures are common). They live in the source config:

```yaml
- type: github
  owners:
    - {name: octocat, kind: user, account: octocat}
    - {name: acme-inc, kind: org, account: octocat-work}
  identities: [octocat, octo-work, "octo@acme.com"]
  since: 2023-01-01
```

`account` is the gh login whose token reads that owner (`gh auth status` lists them; the cache
uses each token without switching the user's active account).

## 0b. The cache: where to look, not what to claim

```
cvt github sync        # incremental: only repos pushed since the last verification
cvt github status      # no API calls: top repos by own commits, stale entries
cvt github sync --full # re-verify everything (only if something smells wrong)
```

It records, per repo, how many commits are the candidate's and the last one, and also the repos
with **no** trace (otherwise they are re-queried every time and the incremental pass stops being
incremental). Two limits: the fine detail (did they touch that file, do they import that library)
is always checked live; and an entry verified 120+ days ago is a hypothesis again. New repos are
indexed blindly on each pass, so the cache does not only refresh what it already knows.

## 1. Sweep: where they really worked

Count **their** commits per repo, not the repo's: the cache does it. `per_page=100` caps at 100:
a "100" means "a hundred or more". PRs add context commits lack:

```
gh search prs --author <login> --owner <org> --limit 100 --json repository,title,createdAt,state
```

## 2. Open, don't just count

```
gh api "repos/<o>/<r>/git/trees/HEAD?recursive=1" --jq '.tree[].path'
gh api "repos/<o>/<r>/commits?author=<login>&per_page=20" --jq '.[]|"\(.commit.author.date[0:10]) \(.commit.message|split("\n")[0])"'
```

Commit messages are the best source of **decisions** ("replace the guard with atomicity", "real CA
bundle"). **Say how many you opened.** Sweeping 200 and opening 15 is a sample.

## 3. Check authorship before claiming

**Did they touch that file?** The path is the artefact for tests, workflows, infrastructure:

```
gh api "repos/<o>/<r>/commits?author=<login>&path=<path>&per_page=100" --jq 'length'
```

**Did they use that library?** The path is useless here; look at the **content** of the files they touched:

```
# 1. their commit SHAs
gh api "repos/<o>/<r>/commits?author=<login>&per_page=100" --jq '.[].sha'
# 2. files those commits touched
gh api "repos/<o>/<r>/commits/<sha>" --jq '.files[].filename'
# 3. CONTENT of those code files: do they import the library?
gh api "repos/<o>/<r>/contents/<file>" --jq '.content'   # base64; decode and search the import string
```

Step 3 is the one that matters; stopping at step 2 produces the false negative. Repeat in **every**
repo where the library is declared. Only 0 everywhere removes it from the CV.

## 4. What is not on the remote

- Local projects without a remote, if the pool includes local folders: look for `.git` folders.
- Live domains: check they answer **before** putting them in the CV (`cvt verify --check-links`
  does it on the PDF). A certificate that doesn't cover the subdomain, a 403/500: a broken link is
  worse than none.

## 5. Real size of a project

Line counts help **decide whether a project goes in** (a real application vs a 200-line
scaffold). They never go **in** the CV (vanity metric).

## 6. Order of work, to avoid anchoring

1. Read the offer. 2. Gather the evidence. 3. Choose the material. 4. **Only then** open the
previous CV, to see what is missing.
