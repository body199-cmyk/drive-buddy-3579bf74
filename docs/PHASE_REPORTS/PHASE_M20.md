# PHASE M20 — Light-only shell, five-step flow, concurrency cap 100

- UTC date: 2026-08-12
- TASK IDs: M20-T01 … M20-T05 (one interlocked package)
- Repository: `body199-cmyk/drive-buddy-3579bf74`
- Branch: `arena/019ff3b0-drive-buddy-3579bf74` (platform-pinned)
- Base SHA: `77e97b789583b07b375f188894a5aca796b03b68` (`main`, merged PR #34)
- Result SHA: `2bd99b729255f1136b1667678b0255004d1101e3` — PR #35 **MERGED** into `main` (2026-08-12T09:28:41Z)
- CI: green on the PR head `acfd473` **and** re-run green on the merged `main` `2bd99b7` (both jobs)
- Honest status: **Code-complete candidate + Fake-tested** — not Colab-ready, not Complete. Merging is not live proof.

---

## 0. Base verification (§0)

`git rev-parse HEAD` == `git rev-parse origin/main` == `77e97b7…` ✅

The task document names `ad3a454…` as the expected base. That commit is not the
head. The sandbox clone is shallow (`.git/shallow` contains `77e97b7`, so
`git rev-list --count HEAD` == 1) and `gh api …/compare/…` answers
`401 Bad credentials`, so **ancestry could not be verified either way**. The
work was built on the verified latest `main` and this deviation is recorded
rather than assumed away.

A second, larger correction follows from the same drift — see §4.

---

## 1. M20-T01 — concurrency cap 100 (ADR-0001)

| Item | Before | After |
|---|---|---|
| `HARD_CONCURRENCY_CAP` | 4 | **100** |
| `CONCURRENCY_LEVELS` | safe/balanced/fast | + `turbo=16`, `max=100` |
| Default | 2 | 2 (unchanged) |
| Warning threshold | — | `CONCURRENCY_WARN_ABOVE = 8` |
| Out-of-range input | silently clamped | **refused** with a localized error |
| UI control | slider 1..4 | slider 1..100, `release` event |

`transfer_manager.py` and `queue_manager.py` were **not touched**: both import
`HARD_CONCURRENCY_CAP` from `config` at call time, so their clamp ceiling rose
automatically. That is exactly why the protected-file rule holds here.

`SettingsService.set_concurrency` now returns
`{level, workers, cap, warn}`; the handler renders `n/100` and appends
`warn.concurrency_high` above 8, so a risky value is honoured **and** stated.

## 2. M20-T02 — enforced light mode

Two independent guards, because one is not enough:

1. **CSS tokens.** `theme.py` redefines every Gradio variable under `:root`,
   `.dark`, `body.dark` and `.gradio-container.dark` with `!important` plus
   `color-scheme: light`. Even if Gradio flips to its dark palette, the tokens
   it reads are the light ones. The `--td-*` values themselves carry
   `!important` too, because the legacy `ui_theme` style block is injected into
   the body — later in the document — and would otherwise win on equal
   specificity.
2. **Class stripper.** `FORCE_LIGHT_JS` removes the `dark` class on load and
   keeps removing it through a `MutationObserver`, and pins `dir="rtl"`.

**Real bug found and fixed during this session:** the task document ships the
stripper as a `<script>` inside `gr.HTML`. Gradio 6 inserts component HTML with
`innerHTML`, so that script **never executes** — Gradio prints an explicit
warning saying so, which appeared in the test run. The guard was moved to
`head=` / `js=` on `launch()`, which do execute, and `app.py` passes them only
if the installed Gradio's `launch()` signature accepts them.

`services.DEFAULT_THEME = "light"` is now the single source of truth read by
`PreferencesService` and `shell_seed`, closing **KNOWN_ISSUES #42**, which
M19-T01 had to leave open because it could not touch `services.py`.

Served-page evidence (`curl` against the live sandbox server):
`--td-bg:#F4F0F5` ✓ · `color-scheme: light` ✓ · `MutationObserver` ✓.

## 3. M20-T03 — the logical 1→5 flow

```
1 connect   telegram -> drive -> destination folder
     v  (2 hidden until all three are really true)
2 analyze   link + scope -> scan
     v  (3 hidden until real results exist)
3 select    filter -> select -> live summary: count, size, space, folder
     v  (4 hidden until at least one item is selected)
4 queue     enqueue -> queue table -> start/pause/resume/stop
     v  (5 hidden until the queue actually has items)
5 monitor   progress, retries, per-item actions, logs
```

- `flow.py` — `FlowService` / `FlowState`, read-only over the live context, no
  Gradio import, every probe defensive.
- `ui_flow_view.py` — the 12 updates, in `flow_outputs` order, plus `visibility()`
  and `texts()` which the **first paint** reuses. That is the part the document
  left implicit: without it the server-rendered page would show all five steps
  until the first sync landed. Now the first paint and every later sync are
  computed by the same function.
- `ui_binder.py` — `register_sync()` / `load_sync()` and a `.then(flow.sync)`
  chained after every wired action. `release` was added to `_EVENTS`.
- `ui.py` — rebuilt into five numbered cards. No `gr.Tab(`, no `themes.Soft`.

Live gating check against a real context:

```
fresh                 [1,-,-,-,-]  step=connect
telegram only         [1,-,-,-,-]  step=connect
tg+drive, no folder   [1,-,-,-,-]  step=connect   <- a missing folder does NOT unlock 2
connected             [1,2,-,-,-]  step=analyze
analyzed              [1,2,3,-,-]  step=select
selected              [1,2,3,4,-]  step=queue
drive dropped again   [1,-,-,-,-]  step=connect   <- no optimism: it collapses back
```

## 4. M20-T04 — proofs, and an honest correction

The document's §7 instructs flipping 18 actions from `tested=False` to
`tested=True` and un-hiding the "dead" buttons. **On the real base that work
was already done.** All 45 declared actions were already `implemented=True,
tested=True`, each with a `proof_test` that is *stronger* than the table in the
document proposes — e.g. `drive.connect` is proven by
`test_drive_connection_gate.py::test_connect_action_reports_connected_only_after_about_get`
(a real `about().get` gate) rather than by a call recorder.

Therefore:
- **No proof was downgraded.** The registry keeps its existing, stronger proofs.
- The 18 binding proofs were still added, as
  `tests/test_ui_contract_proofs.py`, because they are honest, cheap, and are
  the level of evidence the document asks to be able to cite.
- `export.build_zip` stays ready (it already was). The document's worry about
  `next(action_registry.unready_specs())` raising `StopIteration` does not
  apply: those three tests inject a synthetic unready spec instead, so **no
  `pytest.skip` was added anywhere**.
- One new action exists: `flow.sync` → `46/46`.

## 5. M20-T05 — memory

ADR-0001 · CONSTITUTION (concurrency clause, forbidden list, §14 UI clause) ·
CHANGELOG · AI_HANDOFF · ACTIVE_TASK · TODO · KNOWN_ISSUES (#42 **closed**;
#43 live Colab proof, #44 untested high concurrency, #45 binding-level proofs
**opened**) · this report.

---

## 6. Verification output (real stdout)

```plain
$ python -m compileall -q teledrive
(exit 0)

$ python -m pytest -q tests
629 passed in 24.08s

$ python teledrive_launcher.py --check
binding check ok: 46/46 ready actions resolve

$ python -m teledrive.notebook_cells --check
notebooks are in sync

$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
(identical)

$ python -m teledrive.package_service --build --output teledrive_v4.5.zip
2026-08-12T02:53:17+00:00 tests passed
archive: teledrive_v4.5.zip

$ npx eslint .
✖ 6 problems (0 errors, 6 warnings)

$ npx vite build
✓ built in 269ms

$ grep -rn "gr.Tab(\|themes.Soft" teledrive/ui.py
(no output)
```

Test count moved 596 → 629 (+33) with **zero deletions and zero skips**.

`bun` cannot be installed in this sandbox (TLS to `bun.sh` is blocked), so the
two frontend gates ran through npm against the same `package.json` scripts.
The diff touches no frontend file; CI runs the bun versions on the PR.

## 7. Acceptance criteria

| Criterion | Result |
|---|---|
| `HARD_CONCURRENCY_CAP == 100`, no silent clamp to 4 | ✅ |
| `ui.py` has no `gr.themes.Soft` and no `gr.Tab(` | ✅ |
| `theme.py`, `flow.py`, `ui_flow_view.py` exist and are really imported | ✅ |
| `ctx.resolve("flow.state")` works; `h_flow_sync` returns 12 | ✅ |
| `binder.assert_complete()` raises nothing at build time | ✅ |
| `pytest -q tests` fully green, nothing deleted, no skip added | ✅ 629 |
| ADR + constitution + changelog + handoff updated | ✅ |
| No protected file touched | ✅ |
| Every declared action wired | ✅ 46/46 |

## 8. What is still owed (do not claim otherwise)

0. **Re-publishing the pinned tag `pkg-2026.08.09-m15t07` from the new `main`
   (`2bd99b7`).** This is a hard blocker for seeing M20 in Colab at all: Cell 1
   installs from that release, so until the tag is re-cut it keeps pulling the
   PREVIOUS package and the merge changes nothing on the user's screen. The
   Arena token lacks `actions:write` (#27), so the owner must dispatch it.
1. A real Colab run with a screenshot from the owner: light page on a dark
   browser, stepper at 🔵 1, steps 2–5 hidden (#43).
2. A real high-concurrency run — 100 workers is proven only mathematically, by
   a semaphore bound test (#44).
3. Live Telegram + Drive integration for the M20 proofs, which are
   binding-level (#45).
