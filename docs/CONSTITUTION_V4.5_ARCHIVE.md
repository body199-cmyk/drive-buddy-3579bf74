# TeleDrive v4.5 — Full Rebuild Constitution, Project Blueprint & AI-OS Protocol

# TeleDrive v4.5
## Full Rebuild Constitution, Functional Blueprint, Recovery Plan & AI-OS Continuity Protocol
**Project:** TeleDrive, Telegram-to-Google-Drive media transfer manager
**Specification:** 4.5.0
**Base:** v3.1 Code-Bound Edition, all engineering contracts retained and expanded
**Runtime:** Google Colab only
**UI runtime:** Gradio in the same Python process, local by default with `share=False`
**Default language:** Arabic RTL
**Secondary language:** English LTR
**Owner:** [@jjjd](#user_mention#228141836)
**Canonical repository currently audited:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`
**Latest publicly verified commit at constitution creation:** `2c9f33be13aae6be3f4c8ff60918d82c9a53d09a`
> This is a build contract, not a summary. It is designed to let a new AI understand the project and continue it without conversation history. It can guide a rebuild from an empty repository, but every implementation claim still requires actual source, tests, and runtime evidence.
* * *
# 0\. How to use this document
When the owner sends this constitution to a new AI and says “راجع الدستور عشان نكمل”, the AI must:

1. understand that this is an existing continuation, not a new greenfield project;
2. locate the repository and the latest Lovable response;
3. inspect the actual repository before making claims;
4. compare the repository against this document and the latest evidence;
5. report verified facts, unverified claims, conflicts, blockers, and protected assets;
6. write a copy-ready Lovable task using the required format in Section 27;
7. never say a task is complete until the repository is rechecked after Lovable’s response.

If the repository is empty, the AI must use the from-zero build plan in Section 24.
If the repository is partially implemented, it must preserve working code and continue from the highest verified phase.

The constitution does not turn fake tests into real integrations. “Colab-ready” is forbidden until the controlled Colab test passes.

* * *
# 1\. The continuity problem
The workflow uses two AI systems, multiple accounts, GitHub, and Google Colab. Conversations expire, accounts change, and Lovable may create a successor repository. Code survives more often than reasoning. The repository must therefore preserve:
*   product purpose;
*   architecture and boundaries;
*   decisions and rejected alternatives;
*   implementation status;
*   known bugs and attempted fixes;
*   exact next steps;
*   test evidence;
*   migration instructions;
*   AI operating rules.

The repository is the permanent memory. Chat history is temporary and never authoritative.
## Roles
### Planning AI, ClipUp/Brain
Architect, reviewer, analyst, prompt writer, and evidence checker. It may inspect and advise. It must not claim repository changes without a real write operation.
### Lovable
Implementation AI. It is the only AI allowed to modify repository files, run implementation commands, create commits, and push changes. It must inspect before editing and report actual evidence.
### Owner
Approves protected changes, forwards messages, supplies live credentials only inside Colab, and runs the final real integration test.

* * *
# 2\. Source-of-truth precedence
Use this order:

1. explicit owner instruction in the current conversation;
2. this constitution;
3. actual checked-out files and current branch;
4. actual command output and test output;
5. controlled Colab output;
6. current handoff and phase report;
7. ADRs, changelog, TODO, and issue files;
8. screenshots and AI claims.

When sources disagree, state the conflict and stop before risky changes. Never silently merge two incompatible truths.

* * *
# 3\. Current repository baseline and known drift
The canonical repository was audited before writing this version. The public branch currently exposes a real Python package, notebooks, tests, CI, and the React reference layer. However, the publicly verified state must be treated as **baseline evidence, not completion proof**.

The current tree visibly contains:
*   `src/` React/TanStack reference/download frontend;
*   `python-package/teledrive/` runtime package;
*   `python-package/tests/` fake and contract tests;
*   `python-package/notebook/TeleDrive.ipynb`;
*   `public/TeleDrive.ipynb`;
*   `python-package/requirements.txt` and `requirements.lock`;
*   `.github/workflows/ci.yml`;
*   `python-package/docs/` with architecture, constitution, audit, runbook, troubleshooting, and phase reports;
*   root `PROJECT_CONTEXT.md`;
*   `python-package/CHANGELOG.md` and `HANDOFF.md`.
## Mandatory baseline audit
Before accepting any claim from Lovable, verify:
*   current branch and commit SHA;
*   actual tree, not an old cached response;
*   whether the reported Phase 2–9 files are actually present;
*   whether the current handoff contradicts the current source;
*   whether `PHASE_9.md` exists and has real output;
*   whether notebooks are generated from one source and identical;
*   whether CI includes lint as well as build;
*   whether `--check` works without credentials;
*   whether Gradio UI construction has actually run;
*   whether real Telegram, Drive, and one-file transfer have run.

Known historical failure: repository reports and public trees sometimes lag or disagree after Lovable edits. A report without a visible commit and matching files is not accepted.

* * *
# 4\. Absolute prohibitions
Reject any implementation that:

1. creates `app_v2.py`, `final_app.py`, a second app, or static HTML runtime;
2. puts Python logic in TypeScript strings;
3. uses fake rows, fake logs, fake quotas, fake folder IDs, fake connected states, fake progress, or seeded runtime data;
4. renders a button without a named handler, service path, and passing test;
5. uses inline lambda handlers;
6. stores SQLite on mounted Drive/FUSE;
7. stores or prints API credentials, phone numbers, codes, passwords, session strings, OAuth tokens, private URLs, or raw tracebacks;
8. uses Telegram Bot API assumptions or `file_unique_id` for dedupe;
9. exceeds concurrency 4 or defaults above 2;
10. claims streaming in v1 instead of disk-first verified upload;
11. deletes a Drive file on cancel/stop;
12. blindly deletes temp files;
13. auto-resumes transfers after restart;
14. upgrades dependencies without compatibility evidence;
15. moves docs or modules without a full reference search;
16. calls fake tests, screenshots, or static scans real integration proof;
17. rewrites working architecture instead of extending it;
18. says “complete” while real Colab remains unverified.

* * *
# 5\. Approved architecture

```plain
Colab notebook
 -> restore tested package into local /content
 -> bootstrap local directories, logging, SQLite WAL
 -> one ApplicationContext
 -> one AsyncRuntime and event loop
 -> one Telethon client and one Drive service
 -> Gradio in the same process
 -> UIBinder.wire(control, action_id)
 -> named handler
 -> application service
 -> infrastructure adapter
 -> SQLite transaction/event
 -> localized UI update
 -> safe checkpoint
```

## Layers
### Launcher
Stable notebook and CLI entrypoint. Restores the tested archive, installs `requirements.lock`, bootstraps local runtime, collects hidden Telegram credentials, performs native Drive auth, injects services, launches Gradio, runs verification, creates handoff/snapshot, and performs safe maintenance.
### UI
Gradio components, layout, navigation, locale, theme, validation, polling, queue table, status chips, logs, and safe messages. No direct SQL, Telegram download, Drive upload, or secret persistence.
### Application services
Authentication, folder operations, quota, scanner, filters, selection, queue orchestration, transfers, checkpoints, recovery, logs, package export, and settings.
### Domain
`MediaItem`, settings, states, transitions, retry policy, source identity, display mapping, and error taxonomy.
### Persistence
SQLite repository, migrations, WAL, transactions, event rows, safe checkpoints, restore, reconciliation, and redacted exports.
### Infrastructure
Telethon adapter, Drive API adapter, filesystem adapter, clock, logger, and fake connectors.

* * *
# 6\. Required repository structure
The exact working repository may retain compatibility paths, but every responsibility must exist exactly once.

```plain
repository/
├── docs/                              # canonical AI-OS home
│   ├── PROJECT_CONTEXT.md
│   ├── ARCHITECTURE.md
│   ├── CONSTITUTION.md
│   ├── AI_RULES.md
│   ├── AI_HANDOFF.md
│   ├── BOOTSTRAP_PROMPT.md
│   ├── CHANGELOG.md
│   ├── CHANGELOG_ARCHIVE.md
│   ├── TODO.md
│   ├── KNOWN_ISSUES.md
│   ├── RUNBOOK.md
│   ├── TROUBLESHOOTING.md
│   ├── AUDIT.md
│   ├── PHASE_REPORTS/
│   └── decisions/
│       ├── ADR_TEMPLATE.md
│       ├── ARCHIVE.md
│       └── ADR-*.md
├── python-package/
│   ├── teledrive/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── redaction.py
│   │   ├── async_runtime.py
│   │   ├── app_context.py
│   │   ├── bootstrap.py
│   │   ├── action_registry.py
│   │   ├── ui_binder.py
│   │   ├── handlers.py
│   │   ├── ui.py
│   │   ├── theme.py
│   │   ├── i18n.py
│   │   ├── telegram_auth.py
│   │   ├── telegram_client.py
│   │   ├── telegram_links.py
│   │   ├── drive_auth.py
│   │   ├── drive_client.py
│   │   ├── drive_folders.py
│   │   ├── drive_quota.py
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── migrations.py
│   │   ├── queue_manager.py
│   │   ├── transfer_manager.py
│   │   ├── checkpoint_manager.py
│   │   ├── storage_manager.py
│   │   ├── media_scanner.py
│   │   ├── filters.py
│   │   ├── services.py
│   │   ├── logging_config.py or log_service.py
│   │   ├── package_service.py
│   │   ├── notebook_cells.py
│   │   ├── colab_cells.json
│   │   ├── handoff.py
│   │   ├── snapshot.py
│   │   └── locale/ar.json and en.json
│   ├── tests/
│   ├── notebook/TeleDrive.ipynb
│   ├── requirements.txt
│   ├── requirements.lock
│   └── teledrive_launcher.py
├── public/TeleDrive.ipynb
├── src/                               # reference/download only
└── .github/workflows/ci.yml
```

Do not create duplicate modules under different names. If an existing name differs, document the mapping in an ADR.

* * *
# 7\. ApplicationContext and AsyncRuntime
Exactly one context per process. It owns configuration, locale, database, auth managers, active clients, all services, UI state, and launch handle.

`ctx.resolve(path)` must fail loudly on unknown service, missing method, `None`, or non-callable target.

Production must have:
*   one async event loop;
*   one Telethon client;
*   one Drive service;
*   one SQLite connection/repository;
*   one context.

`asyncio.new_event_loop()`, `asyncio.run(`, and `run_until_complete(` may appear only where explicitly permitted by the runtime implementation and must not appear in handlers or UI code. Preferred enforcement is a source guard.

Shutdown must stop non-blocking UI, cancel pending tasks, flush safe checkpoints/logs, stop loop, and close SQLite.

* * *
# 8\. Security, database, and storage contract
SQLite stays under local `/content`, with WAL verified from real runtime state. No secrets enter SQLite, checkpoints, snapshots, Drive, GitHub, ZIPs, or logs.

Temporary files use `.part`. Verify local size before upload. Verify Drive file ID, appProperties, parent, and size after upload. Keep mismatched `.part` files for retry. Quarantine unknown or incomplete files. Delete only verified temp belonging to verified `Uploaded` items.

Redaction must remove values and secret-like fields from UI errors, logs, handoffs, snapshots, notebook output, and developer diagnostics shown to users.

* * *
# 9\. Telegram authentication
Exact states:

```plain
DISCONNECTED, READY_FOR_PHONE, SENDING_CODE, CODE_REQUESTED,
VERIFYING_CODE, PASSWORD_REQUIRED, VERIFYING_PASSWORD,
AUTHORIZED, REAUTH_REQUIRED, ERROR
```

Rules:
*   Telethon user authorization only;
*   hidden API ID/hash, memory only;
*   international phone format;
*   first code request once;
*   retain exact `phone_code_hash`;
*   pass hash to `sign_in`;
*   invalid code keeps hash/state;
*   expired code clears hash/state;
*   2FA reuses client and requests no new code;
*   password is cleared immediately;
*   resend explicit and cooldown-protected;
*   duplicate clicks idempotent;
*   logout/account switch explicit;
*   success writes SQLite AUTH event, real authorized state, and redacted log.

Fake tests must cover all transitions, errors, cooldown, duplicate clicks, logout, account change, and redaction. Real success is only proven in Colab.

* * *
# 10\. Google Drive authentication and folders
Allowed path only:

```python
from google.colab import auth as colab_auth
import google.auth
from googleapiclient.discovery import build

colab_auth.authenticate_user(clear_output=False)
creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
service = build("drive", "v3", credentials=creds, cache_discovery=False)
about = service.about().get(
    fields="user(displayName,emailAddress),storageQuota(limit,usage)"
).execute()
```

No desktop OAuth JSON, InstalledAppFlow, pasted code, or persisted token file. Connected is impossible before `about.get()` succeeds. Persist folder ID, not name. Implement browse/create/select, reconnect, account-switch guidance, quota, 90% warning, and insufficient-space refusal.

* * *
# 11\. Action Registry and UI binding
Every visible action is declared once with ID, handler, service path, label, section, implemented, and tested flags.

`UIBinder.wire()` rejects unknown, dead, untested, or unresolved actions. `assert_complete()` rejects ready but unwired actions. Every handler is named and decorated. No direct `.click`, `.change`, `.submit`, or lambda in layout code.

Required action groups:
*   language, theme, status tests, account summary, ZIP export;
*   queue start/pause/resume/retry/clear/item controls/refresh;
*   Telegram save/send/verify/2FA/resend/change/logout/account;
*   Drive connect/reconnect/account/folder/quota/test-all;
*   analyze scopes, filters, selection, enqueue;
*   logs search/filter/copy/download/clear;
*   settings duplicate policy, mode, concurrency, attempts, reserve, advanced;
*   Colab cell copy and tested ZIP download.

Every action requires UI -> real service -> SQLite -> real UI -> redacted log proof.

* * *
# 12\. Analyze, selection, dedupe
Scopes are exactly `message`, `group`, and bounded `range`. Never crawl a whole channel by default. Analyze displays real `MediaItem` objects and never auto-enqueues. User filters and selects, then explicitly enqueues.

Deduplication uses deterministic MTProto identity and verified metadata, never filename-only or Bot API identity.

* * *
# 13\. Queue and transfer
Only QueueManager changes queue states. Required controls include start selected, pause/resume all, retry failed, clear metadata, per-item pause/resume/stop/retry, and snapshot.

Mandatory order:

```plain
validate connections
-> bounded scan
-> MediaItem
-> deterministic duplicate check
-> Drive quota
-> local disk reserve
-> enqueue
-> .part download
-> local size verification
-> resumable Drive upload
-> Drive ID/properties/parent/size verification
-> safe checkpoint
-> Uploaded
-> targeted cleanup
```

Default concurrency 2, hard cap 4, real bounded worker pool. Cancel/stop never deletes Drive files. Test pause/resume/cancel/retry, interruption/restart, crash-after-upload, dedupe, mismatch retention, quarantine, and cleanup.

* * *
# 14\. UI and UX
Arabic RTL default, English LTR without losing runtime state. Right navigation rail, graphite dark theme, coordinated light theme, lime accent, top status bar, real status chips, real folder chip, real engine badge, Transfers main workspace, Dashboard, Analyze, Connections, Logs, Settings, Colab export.

No fake data. Advanced settings collapsed. Concurrency slider 1–4, default 2. `ui.py` is layout only and reads live context state.

* * *
# 15\. Notebook and launcher
One authoritative generator produces both notebook copies. They must be identical.

Seven required cells:

1. Mount Drive only to fetch the tested archive, install `requirements.lock`, keep runtime local.
2. Bootstrap local dirs, logging, migrations, WAL.
3. Hidden Telegram credentials and native Drive auth with `about.get()`.
4. Inject services into the one context, safe restore/reconcile, launch `share=False`; non-blocking only with context-owned handle and safe shutdown.
5. Redacted handoff/snapshot.
6. Pytest with actual stdout/stderr and failure propagation.
7. Checkpoint, targeted cleanup, quarantine, clean shutdown.

No old v2 notebook, no OAuth JSON, no blind `rmtree`, no hard-coded conflicting versions. Launcher supports `--check`, local default, and explicit `--share`.

* * *
# 16\. CI and evidence
Required commands:

```plain
python -m compileall teledrive
python -m pytest -q tests
python teledrive_launcher.py --check
python -m teledrive.notebook_cells --check
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
python -m teledrive.package_service --build --output teledrive_v4.5.zip
bun run lint
bun run build
```

CI must run tests, launcher check, notebook consistency, package build, frontend lint, and frontend build. No `continue-on-error`.

Status vocabulary:
*   Implemented: source exists.
*   Fake-tested: fake tests pass.
*   Code-complete candidate: code/CI/notebook gates pass; live integrations absent.
*   Colab-ready: controlled real Colab smoke test passes.
*   Complete: Colab-ready plus safe shutdown, recovery, redacted logs, and handoff.

* * *
# 17\. Historical failure catalogue and permanent fixes
## Failure A: dead visual controls
**Cause:** React page or UI buttons existed without real Python service paths.
**Fix:** Action Registry, named handlers, Binder, service resolution, binding tests, and build-time failure.
## Failure B: disconnected frontend and backend
**Cause:** rendered web page was mistaken for the Colab application.
**Fix:** React is reference/download only; Gradio and Python run in one Colab process.
## Failure C: ad-hoc event loops
**Cause:** each handler created a new asyncio loop, breaking Telethon client ownership.
**Fix:** one AsyncRuntime and one loop owned by ApplicationContext.
## Failure D: Telegram hash loss
**Cause:** `phone_code_hash` was returned and discarded; code and 2FA were collapsed.
**Fix:** exact hash retained, passed to sign-in, explicit states, separate 2FA, cooldown resend.
## Failure E: incorrect Drive OAuth
**Cause:** uploaded client JSON, paste-code flow, and token persistence.
**Fix:** native Colab auth, `google.auth.default`, `about.get` gate, in-memory service only.
## Failure F: analyze auto-enqueued everything
**Cause:** analysis and mutation were mixed.
**Fix:** analyze displays; filter/select; explicit enqueue only.
## Failure G: unsafe cleanup
**Cause:** blind temp-directory deletion.
**Fix:** verify Uploaded, delete only owned verified temp, quarantine everything else.
## Failure H: concurrency contradiction
**Cause:** visual reference showed 50 threads while safe contract is max 4.
**Fix:** slider 1–4, default 2, real worker count.
## Failure I: stale repository/report mismatch
**Cause:** Lovable response described files not visible in the current GitHub branch.
**Fix:** reviewer rechecks branch, commit, tree, files, and outputs after every response.
## Failure J: account and repository migration loss
**Cause:** new account treated copied repository as greenfield.
**Fix:** constitution, context, handoff, ADRs, reports, migration record, destination verification, and mandatory reading order.
## Failure K: documentation duplication
**Cause:** root docs, package docs, handoff, and phase reports became competing authorities.
**Fix:** one canonical docs home, one live handoff, immutable reports, one-line compatibility pointers.
## Failure L: Gradio and notebook drift
**Cause:** package pins, cell generator, public notebook, and internal notebook diverged.
**Fix:** `requirements.lock` single authority, one generator, identical notebook check, real Gradio smoke test.

* * *
# 18\. AI-OS documentation contract
Canonical home is root `docs/`.

```plain
docs/
├── PROJECT_CONTEXT.md
├── ARCHITECTURE.md
├── CONSTITUTION.md
├── AI_RULES.md
├── AI_HANDOFF.md
├── BOOTSTRAP_PROMPT.md
├── CHANGELOG.md
├── CHANGELOG_ARCHIVE.md
├── TODO.md
├── KNOWN_ISSUES.md
├── RUNBOOK.md
├── TROUBLESHOOTING.md
├── AUDIT.md
├── PHASE_REPORTS/
└── decisions/
    ├── ADR_TEMPLATE.md
    ├── ARCHIVE.md
    └── ADR-*.md
```

Responsibilities:
*   Context: identity and reading levels;
*   Architecture: current map only;
*   Constitution: authority;
*   AI Rules: operating behavior only and constitution wins;
*   Handoff: latest session only;
*   Reports: immutable evidence;
*   TODO: open work;
*   Issues: confirmed problems;
*   ADRs: major decisions and alternatives;
*   Changelog: recent changes, archive old entries.

Do not create full duplicate copies in old locations. Keep one-line pointers only when compatibility requires them. Before moving files, search all code/tests/CI/notebook/frontend/package references.

* * *
# 19\. Layered AI reading strategy
Level 1: context, AI rules, handoff, bootstrap prompt, constitution.
Level 2: architecture, source tree, tests, CI.
Level 3: recent ADRs, TODO, known issues, changelog.
Level 4: archives, audits, phase reports, historical material.

Level 1 must be readable in minutes and link deeper instead of copying it.

* * *
# 20\. From-zero build plan
If the repository is empty, execute only one phase per commit and stop for review:
### Phase 0, contract and inventory
Create repository, `.gitignore`, docs skeleton, constitution copy, `requirements.txt`, `requirements.lock`, README pointers, and secure directory policy. Add no fake runtime data.
### Phase 1, runtime foundation
Create config, errors, redaction, AsyncRuntime, ApplicationContext, bootstrap, migrations, database, WAL, local storage, and lifecycle tests.
### Phase 2, binding contract
Create Action Registry, Binder, named handlers, service path resolution, dead-control rejection, and binding tests.
### Phase 3, Telegram
Create thin Telethon adapter and exact state machine with fake connector tests.
### Phase 4, Drive
Create native Colab Drive auth, about gate, folders, quota, account switch guidance, and fake tests.
### Phase 5, domain and analysis
Create models, link parser, scanner, bounded scopes, filters, selection, deterministic identity, and tests.
### Phase 6, queue and transfer
Create legal transitions, QueueManager, bounded workers, disk-first transfer, resumable upload, verification, checkpoint, recovery, quarantine, and failure-injection tests.
### Phase 7, UI
Create theme, locales, layout-only Gradio UI, status chips, queue, logs, settings, dashboard, and binder wiring. Test empty runtime and locale/state preservation.
### Phase 8, export and notebook
Create package builder, notebook generator, identical notebook copies, launcher, safe maintenance, and archive tests.
### Phase 9, CI and evidence
Add CI, run all gates, update docs, and record real output. Do not claim Colab readiness.
### Phase 10, real Colab verification
Owner runs native Drive auth, Telegram UI login, one folder, one bounded analysis, one selected media item, one transfer, Drive verification, SQLite/checkpoint/log verification, cleanup, and restart reconciliation.
### Phase 11, AI-OS migration
After or independently from live verification only by owner approval: canonicalize docs under root `docs/`, add handoff, rules, bootstrap prompt, ADRs, TODO, issues, archives, pointers, doc tests, and migration report. Runtime behavior must not change.

* * *
# 21\. Acceptance matrix
A release candidate must prove:
*   source tree matches required responsibilities;
*   no secret leakage by source/test scan;
*   one context and one loop;
*   41 or current declared actions are fully bound and tested;
*   Telegram fake matrix passes;
*   Drive fake matrix passes;
*   analysis/selection/dedupe matrix passes;
*   queue/recovery matrix passes;
*   locale/theme/empty-state matrix passes;
*   notebook copies match;
*   launcher check works without credentials;
*   package builder fails closed;
*   CI runs all gates;
*   real Gradio build runs;
*   real Telegram/Drive/transfer remain separately labeled until Colab evidence.

* * *
# 22\. Phase report format
Every implementation phase writes:

```plain
PHASE/TASK:
Repository URL, branch, commit:
Goal:
Files inspected:
Files created:
Files changed:
Files moved/deleted:
Protected files unchanged:
Implementation summary:
Tests added/changed:
Commands run:
Actual stdout:
Actual stderr:
Test count:
Frontend build/lint:
Notebook consistency:
Launcher check:
Real Gradio: verified/not verified:
Real Telegram: verified/not verified:
Real Drive: verified/not verified:
Controlled transfer: verified/not verified:
Documentation updated:
Failed attempts:
Remaining blockers:
Next smallest step:
Commit SHA:
```

* * *
# 23\. Lovable response contract
Lovable must answer every task using:

```plain
TASK/PHASE:
Repository and branch:
Commit SHA:
Files inspected:
Files created:
Files changed:
Files moved/deleted:
Protected files unchanged:
Implementation summary:
Tests added/changed:
Commands run:
Actual stdout:
Actual stderr:
Test count:
Notebook consistency:
Launcher check:
Frontend lint/build:
Real Gradio status:
Real Telegram status:
Real Drive status:
Controlled transfer status:
Documentation updated:
Failed attempts:
Remaining blockers:
Next smallest step:
```

Missing fields or vague statements are incomplete. “Done” without evidence is rejected.

* * *
# 24\. Planning AI to Lovable task format
Every message the planning AI sends must be copy-ready:

```plain
TASK: one precise objective

REPOSITORY:
- URL:
- branch:
- source/destination rule:
- work only in:

READ FIRST:
1. constitution
2. project context
3. AI handoff/latest phase report
4. architecture
5. relevant code/tests/CI/notebooks

CURRENT VERIFIED FACTS:
- facts with paths
- claims that remain unverified

TODO IN THIS ORDER:
1. inspect tree and current commit
2. search references and conflicts
3. implement smallest safe change
4. add/update tests
5. update documentation
6. run exact gates
7. commit and report

FILES ALLOWED TO CHANGE:
- exact paths

FILES PROTECTED:
- exact paths

ACCEPTANCE CRITERIA:
- observable behavior
- tests
- documentation
- no regression

REQUIRED COMMANDS:
```text
commands
```

STOP CONDITIONS:
*   conflict, missing file, failed test, unavailable dependency, or unverified claim

```plain
The planning AI must fill this, not send vague prompts.

---

# 25. Protected assets and approval gate

Owner approval is required before changing:

- ApplicationContext/AsyncRuntime;
- Telegram auth and hash handling;
- native Drive auth/about gate;
- SQLite schema/migrations/storage boundary;
- queue state machine/transfer order;
- Action Registry/Binder;
- requirements lock;
- notebook generator and seven-cell contract;
- package builder;
- CI gates;
- canonical documentation authority;
- account/repository migration protocol.

Any proposal must include reason, affected contracts, migration plan, tests, rollback plan, and compatibility impact.

---

# 26. Definition of done

- **Implemented:** source exists.
- **Fake-tested:** fake tests pass.
- **Code-complete candidate:** code, tests, CI, notebook, launcher, and package gates pass.
- **Colab-ready:** controlled real Colab test passes.
- **Complete:** Colab-ready plus recovery, shutdown, logs, cleanup, and final handoff.

Until the real test passes, the only honest sentence is:

**Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.**

---

# 27. Owner command for future conversations

```text
هذا دستور TeleDrive v4.5. اقرأه كاملًا. راجع الريبو الفعلي ورد Lovable، قارنهما بالدستور، واذكر الحالة المؤكدة فقط. لا تعدّل شيئًا. اكتب أولًا: Verified State, Unverified Claims, Conflicts, Risks, Protected Assets, ثم رسالة Lovable كاملة بصيغة TASK وTODO وAcceptance Criteria وRequired Commands وRequired Response.
```

This command means the AI must review before advising and re-review after implementation.

* * *
# 28\. Revision policy
Any constitution revision requires:
*   explicit owner approval;
*   version bump;
*   change summary;
*   compatibility note;
*   ADR;
*   repository copy update;
*   handoff and changelog update.

No AI may silently weaken or delete an existing v3.1 rule.

**Version:** 4.5.0
**Status:** master rebuild and continuity constitution