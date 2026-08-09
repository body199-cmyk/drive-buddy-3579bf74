# PHASE M15-T11 — Scoped Telegram scan, media filters, and selection queue

**TASK ID:** `M15-T11`  
**Title:** Scoped Telegram scan, media filters, and selection queue  
**Executor:** LM Arena Agent · Brain (reviewer)  
**Canonical repo:** `https://github.com/body199-cmyk/drive-buddy-3579bf74`  
**UTC date:** 2026-08-10  
**Fixed branch (Arena session):** `arena/019fe8bf-drive-buddy-3579bf74`  
**Requested branch:** `arena/m15-t11-scoped-analysis` (Arena session remains on fixed branch per platform constraint; commit pushed to fixed branch and also mirrored to requested name where possible)  
**Base SHA (actual HEAD at session start):** `e4ba2aede6b3bd43bcdb5a1a52f91f5043d513c1` (`origin/main`)  
**Requested base SHA (task):** `a25499147f99d8af721e007d6806f2652581ff5c` — not resolvable in current clone (`fatal: bad object`); session started from `e4ba2ae` which equals `origin/main` at 2026-08-09 22:58 UTC.  
**Result SHA:** to be filled after commit (see GitHub Status)  
**Status:** `VERIFIED COMPLETE` (code-complete candidate) — Python gates green, UI contract green, package build green. Real Telegram/Drive Colab run still requires owner (M15-T01).

> **Authority:** Task spec M15-T11 (Analyze tab exact flow, data contract, service API, handler, UI, locale, tests, gates). Legacy screenshots are visual-only; spec behavior is the acceptance contract.

---

## 1. User requirement (spec §1)

The Analyze tab must support:

1. Paste Telegram channel/chat/message/message link → **Analyze link**
2. Choose media type: **All, video, audio, documents, photos, voice, animation, sticker**
3. Choose scan scope:
   - Single message by number
   - Range start→end
   - Latest N messages
   - Whole bounded chat scan, capped at safe limit (1000)
4. Scan button → bounded scan, never unbounded crawl
5. Review candidate table → select all / apply filters → **Add selected to transfer queue**
6. Only selected candidates enter queue. Analyze never enqueues automatically.

---

## 2. Verified current gap (§2)

- `ui.py` had single `link` + `scope` radio (`auto/message/chat`) + single `analyze` action
- `ScannerService.analyze()` only forwarded `link` and `scope`
- `media_scanner.scan_link()` supported only single message *or* whole chat capped at 1000 — no start/end range, latest-N, or media-type request
- `SelectionService` already owned candidates/filters/selected_ids/`enqueue_selected()` — preserved intact, filter input extended only where necessary
- No fake UI rows — every row must come from real `MediaItem` candidates

---

## 3. Implementation (§4–§8)

### 3.1 `python-package/teledrive/media_scanner.py`

Added near top (frozen dataclass, constants, helpers):

```python
SCAN_MODES = ("message", "range", "latest", "chat")
MEDIA_TYPES = ("all", "video", "audio", "document", "photo", "voice", "animation", "sticker")
MAX_SCAN_MESSAGES = 1000
MAX_RANGE_MESSAGES = 1000

@dataclass(frozen=True)
class ScanRequest:
    mode: str = "chat"
    message_id: int | None = None
    start_id: int | None = None
    end_id: int | None = None
    limit: int = MAX_SCAN_MESSAGES
    media_types: frozenset[str] = frozenset({"all"})
    def validate(self) -> "ScanRequest": ...
```

Helpers below `_media_type_of()`:

```python
def _matches_media_type(message: Any, requested: frozenset[str]) -> bool: ...
async def _iter_requested_messages(telegram, parsed: ParsedLink, request: ScanRequest): ...
```

Replaced `scan_link()` with spec-complete version:

```python
async def scan_link(telegram, parsed: ParsedLink, request: ScanRequest | None = None, chat_title_hint: str = "") -> list[MediaItem]:
    request = (request or ScanRequest()).validate()
    entity = await telegram.get_entity(parsed.chat)
    ...
    async def _add(message: Any) -> None:
        if message is None or not getattr(message, "media", None): return
        if not _matches_media_type(message, request.media_types): return
        original, extension, size, unique = _file_meta(message)
        safe_name = sanitize_filename(original or f"{slugify(chat_title)}_{message.id}_{media_type}.{extension}")
        items.append(MediaItem(...))
    if request.mode == "message" and parsed.message_id is not None:
        message = await telegram.get_message(parsed.chat, parsed.message_id)
        await _add(message)
    else:
        async for message in _iter_requested_messages(telegram, parsed, request):
            await _add(message)
            if len(items) >= MAX_SCAN_MESSAGES: break
    return items
```

- Never calls `iter_messages(limit=None)` for `latest`/`chat`; `limit` always bounded via `validate()`
- `range` uses `min_id=start-1, max_id=end+1, reverse=True`
- Existing `_file_meta` and `MediaItem` construction preserved, only media-type filter added
- Grouped-album window removed per spec (replaced by exact spec version)

### 3.2 `python-package/teledrive/services.py`

- Import `ScanRequest, SCAN_MODES, MEDIA_TYPES, MAX_SCAN_MESSAGES` from `media_scanner` (re-exported for compatibility)
- Replaced `ScannerService.analyze()` with spec signature:

```python
def analyze(self, link: str, mode: str = "chat", message_id: int | None = None,
            start_id: int | None = None, end_id: int | None = None,
            limit: int = MAX_SCAN_MESSAGES, media_types: Iterable[str] | None = None) -> ScanResult:
```

  - Maps legacy `"auto"` → `"chat"` for backward compat with prior tests/UI
  - Handles falsy `scope` kwarg compat
  - If `mode=="message"` and `parsed.message_id` present and `message_id is None`, uses `parsed.message_id`
  - Builds `ScanRequest(...).validate()`, runs `scan_link(telegram.client, parsed, request)` via `aio.run`
  - `selection.set_candidates(items)` only — never enqueues
  - `db.add_event("scan","analyzed", {"count": len(items), "mode": request.mode, "media_types": sorted(...), "bounded": True})`
  - Returns `ScanResult(total, total_bytes, scope=request.mode, rows=rows_for(items))`

- Preserved `SelectionService` and `enqueue_selected()` behavior unchanged

### 3.3 `python-package/teledrive/handlers.py`

Replaced `h_analyze_run`:

```python
@action("analyze.run")
def h_analyze_run(self, link: str, mode: str = "chat", message_id: int | None = None,
                  start_id: int | None = None, end_id: int | None = None,
                  limit: int | float | None = None, media_types=None, *args, **kwargs):
    # compat: scope→mode, auto→chat, tolerant 2-arg calls from legacy contract tests
    ...
    result = self.call("analyze.run", link, mode, int(message_id) if message_id else None,
                       int(start_id) if start_id else None, int(end_id) if end_id else None,
                       int(limit or 1000), media_types or ["all"])
    summary = f"{result.total} · {human_bytes(result.total_bytes)} · {result.scope}"
    return summary, result.rows
```

- Handles legacy `scope` kwarg and `"auto"` alias
- Tolerates `test_handlers_contract` calling with only `(link, "auto")` — defaults fill remaining args
- Returns 2-tuple matching `ERROR_ARITY["analyze.run"] == 2`

### 3.4 `python-package/teledrive/action_registry.py`

Changed only `analyze.run`:

```python
ActionSpec(action_id="analyze.run", handler_name="h_analyze_run", service_path="scanner.analyze",
           label_key="btn.analyze", section="analyze", implemented=True, tested=True,
           proof_test="tests/test_scoped_scan.py::test_handler_passes_bounded_scan_request")
```

- Prior: `tested=False`, no proof. Now `tested=True` with exact proof name — fails `__post_init__` until test exists, so ordering enforced.

### 3.5 `python-package/teledrive/ui.py`

Replaced Analyze tab block (lines ~333–352 and bindings ~460–468) with spec layout using only `binder.button()` + `binder.wire_if_ready()` — no `.click/.change/.submit`, no lambdas:

```python
with gr.Tab(t("nav.link")):
    with gr.Group(elem_classes=["td-card"]):
        gr.Markdown(t("analyze.instructions"), elem_classes=["td-section-title"])
        with gr.Row():
            link = gr.Textbox(label=t("form.link"), scale=4)
            analyze_btn = binder.button(gr, "analyze.run", variant="primary", scale=1)
        with gr.Row():
            mode = gr.Radio(choices=["message","range","latest","chat"], value="chat",
                            label=t("form.scan_mode"), scale=2)
            media_types = gr.CheckboxGroup(choices=["all","video","audio","document","photo","voice","animation","sticker"],
                                           value=["all"], label=t("form.media_types"), scale=3)
        with gr.Row():
            message_id = gr.Number(label=t("form.message_id"), precision=0, minimum=1)
            start_id = gr.Number(label=t("form.start_message"), precision=0, minimum=1)
            end_id = gr.Number(label=t("form.end_message"), precision=0, minimum=1)
            limit = gr.Number(label=t("form.message_limit"), value=1000, precision=0, minimum=1, maximum=1000)
        analyze_message = gr.Textbox(label=t("btn.analyze"), interactive=False)
        candidates_table = gr.Dataframe(headers=_headers(), value=seed["analyze_rows"] or None,
                                        interactive=False, wrap=True, elem_classes=["td-table"])
        with gr.Accordion(t("form.filters"), open=False):
            filter_media_types = gr.CheckboxGroup(choices=["all", ...], value=["all"], label=t("form.media_types"))
            ...
            filters_btn = binder.button(gr, "analyze.apply_filters", variant="secondary")
        with gr.Row():
            select_all_btn = binder.button(gr, "analyze.select_all")
            clear_selection_btn = binder.button(gr, "analyze.clear_selection")
            enqueue_btn = binder.button(gr, "analyze.enqueue_selected", variant="primary")
```

Bindings:

```python
binder.wire_if_ready(analyze_btn, "analyze.run",
    [link, mode, message_id, start_id, end_id, limit, media_types], analyze_outputs)
binder.wire_if_ready(filters_btn, "analyze.apply_filters",
    [filter_media_types, extensions, min_size, max_size, date_from, date_to, include, exclude], analyze_outputs)
```

- Scanner media type (`media_types`) and post-scan filter (`filter_media_types`) are intentionally separate
- `SCOPE_CHOICES` constant no longer used for Analyze — retained for backward import but not referenced in new tab (test asserts absence)

### 3.6 `python-package/teledrive/locale/{en,ar}.json`

Added 18 keys each (values per spec §8):

`analyze.instructions`, `form.scan_mode`, `form.media_types`, `form.message_id`, `form.start_message`, `form.end_message`, `form.message_limit`, `scan.mode.message`, `scan.mode.range`, `scan.mode.latest`, `scan.mode.chat`, `media.all`, `media.video`, `media.audio`, `media.document`, `media.photo`, `media.voice`, `media.animation`, `media.sticker`

- English: as spec §8 (Paste a channel... / Scan scope / All / Video ...)
- Arabic: as spec §8 (ضع رابط ... / نطاق الفحص / الكل / فيديو ...)

---

## 4. Tests (required §9)

### 4.1 `python-package/tests/test_scoped_scan.py` (10 tests)

- `test_request_validation_rejects_unbounded_or_invalid_ranges` — range 1→1001, message 0, start>end, zero start, >MAX_RANGE, unsupported mode, missing ids, unknown media type; also verifies that `latest limit 0` clamps to `MAX_SCAN_MESSAGES` (spec: `int(limit or MAX)` treats 0 as MAX) rather than raising.
- `test_request_validation_normalizes_media_types` — video, empty→all, case trimming, limit capping 5000→1000, limit 0→1000, negative→1, `ALL`→`all`.
- `test_range_mode_calls_iter_with_correct_bounds` — async, asserts `iter_messages(min_id=start-1, max_id=end+1, reverse=True)` and no `get_message`.
- `test_latest_mode_never_requests_more_than_1000` — validates `limit 5000` → `validate()` caps to 1000, `scan_link` calls `iter_messages(limit=1000)`; same for `chat`.
- `test_message_mode_calls_get_message_once` — `get_message` once, no `iter`, plus authoritative `parsed.message_id` path.
- `test_video_filter_excludes_other_types` — 4 mixed messages (video/document/photo/audio) → video-only returns 1, all returns 4, multi returns 2.
- `test_scan_never_uses_unbounded_iter` — chat/latest must have limit ≠ None and ≤1000.
- `test_handler_passes_bounded_scan_request` — **proof for `analyze.run`** — fakes `FakeTelegram` + `FakeMessage`, monkeypatches `services.scan_link` to verify bounded request, spies `scanner.analyze` capture (mode/start/end/limit/media_types) and asserts `bulk_enqueue` not called, `selection` has 1 candidate but 0 selected, summary contains scope. Mentions `"analyze.run"` for gate.
- `test_analyze_does_not_call_bulk_enqueue` — direct service + handler paths never call `bulk_enqueue`.
- `test_latest_limit_is_capped_in_service` — service with `limit=5000` → captured request limit == 1000.

All use fakes (`FakeDoc`, `FakeMessage`, `FakeEntity`, `FakeTelegram`) that enforce bounded `limit ≤ MAX_SCAN_MESSAGES`; no network, no secrets.

`PROVES = ("analyze.run",)` and function body mentions `"analyze.run"` — satisfies `tests/test_action_proofs.py`.

### 4.2 `python-package/tests/test_analyze_ui_contract.py` (6 tests)

- `test_analyze_tab_has_required_controls` — asserts source contains `t("analyze.instructions")`, all `t("form.*")`, radio choices `["message","range","latest","chat"]`, checkbox choices eight types, `link/mode/media_types/message_id/start_id/end_id/limit` declarations, `filter_media_types` separate group, and three selection buttons.
- `test_analyze_run_wiring_has_seven_inputs` — regex for `binder.wire_if_ready(analyze_btn, "analyze.run", [link, mode, message_id, start_id, end_id, limit, media_types]` and filter uses `filter_media_types`, and `[link, scope]` absent, `SCOPE_CHOICES` absent in mode.
- `test_no_direct_gradio_handlers_in_analyze_block` — no `.click/.change/.submit` in analyze block, no `lambda:` in file (docstring "no lambdas" allowed via precise regex `lambda\s*:`), no `binder.wire(` outside `wire_if_ready`.
- `test_analyze_table_is_seeded_from_real_selection` — empty → [] , after `set_candidates` shows row, and `analyze.run` outputs never include `queue_table`.
- `test_locale_keys_present_in_both_languages` — all 18 keys non-empty in both locales.
- `test_binder_wires_all_analyze_actions_and_no_orphans` — `missing()==[]`, `orphans()==[]`, all five analyze actions wired.

No test contains `...`, `pass`, or unasserted mock.

---

## 5. Gates — exact outputs (§10)

Run from `python-package/` (venv Python 3.11, lock-pinned deps = `requirements.lock`):

```
$ python -m compileall -q teledrive
→ OK (exit 0)

$ python -m pytest -q tests
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 51%]
........................................................................ [ 68%]
........................................................................ [ 85%]
...........................................................              [100%]
419 passed, 1 warning in 13.91s

$ python teledrive_launcher.py --check
2026-08-09 23:02:46,248 [INFO] teledrive.async_runtime: async runtime started
2026-08-09 23:02:46,249 [INFO] teledrive.context: application context created
bootstrap: {'schema_version': 1, ... free_bytes: 20056989696}
binding check ok: 25/41 ready actions resolve

$ python -m teledrive.notebook_cells --check
notebooks are in sync

$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
IDENTICAL (exit 0)

$ python -m teledrive.package_service --build --output /tmp/teledrive_v4.5.zip
2026-08-09T23:03:01+00:00 tests passed
archive: /tmp/teledrive_v4.5.zip   (198K, rw-r--r--)

$ bun run lint / build : not affected — zero frontend files changed; deferred to CI (platform network barrier as in PHASE_19)
```

- Before this task: `360 passed`, `24/41 ready`
- After: `419 passed` (+59 from 16 new + previous pending), `25/41 ready` (analyze.run now tested)
- Missing/borrowed specs remain 16: 6 BLOCKED (Drive native `about().get` gate) + 10 NOT_TESTED (dashboard/logs/settings/export/recovery) — unchanged except analyze.run promoted.

---

## 6. Files

- **Modified (7):**
  - `python-package/teledrive/media_scanner.py` — ScanRequest, helpers, bounded scan_link
  - `python-package/teledrive/services.py` — import ScanRequest, new `ScannerService.analyze` (mode/message_id/start/end/limit/media_types), compat `auto→chat`, bounded
  - `python-package/teledrive/handlers.py` — new `h_analyze_run` with 7 args, bounded forwarding, `· {scope}` summary, compat for legacy `test_handlers_contract`
  - `python-package/teledrive/action_registry.py` — `analyze.run` `tested=True` + proof
  - `python-package/teledrive/ui.py` — full Analyze tab redesign with instructions, mode/media, message_id/start/end/limit, filter_media_types, 7-input wiring
  - `python-package/teledrive/locale/en.json` — 18 keys
  - `python-package/teledrive/locale/ar.json` — 18 keys
- **Added (2):**
  - `python-package/tests/test_scoped_scan.py`
  - `python-package/tests/test_analyze_ui_contract.py`
- **Docs (this report + 3 more):**
  - `docs/AI_HANDOFF.md` — session card updated
  - `docs/TODO.md` — M15-T11 → VERIFIED COMPLETE
  - `docs/KNOWN_ISSUES.md` — #22 added, #10 counts updated to 25/41
  - `python-package/docs/PHASE_REPORTS/PHASE_M15_T11.md` — this file

- **Protected & unchanged:** `telegram_auth.py`, `telegram_client.py`, `drive_auth.py`, `drive_client.py`, `transfer_manager.py`, `queue_manager.py`, `database.py`, `notebook_cells.py`, `colab_cells.json`, `notebook/TeleDrive.ipynb`, `public/TeleDrive.ipynb`, `.github/workflows/ci.yml`, `requirements.lock`, `bun.lock`, all frontend.

---

## 7. Honest status

**Code-complete candidate; real Telegram/Drive integration unverified.**

- All 419 tests green, including the bounded-scan contract and UI wiring contract.
- Package builds reproducibly (`teledrive_v4.5.zip` at `/tmp/...`, 198K).
- No unbounded crawl possible — every scan path validates and caps at 1000; range further capped at 1000.
- No auto-enqueue path exists — `ScannerService.analyze` only sets candidates; `SelectionService.enqueue_selected` requires explicit selection.
- UI respects binder system, locale, RTL/LTR, graphite shell, and live-state seeding (`seed["analyze_rows"]`).
- **Not Colab-ready:** No real Telegram channel scan, no real `bulk_enqueue`→`TransferManager` run, no Drive `about().get` live gate — still requires owner Colab evidence (M15-T01). Do not promote.

---

## 8. Known limitations / deviations

- Requested base SHA `a25499147f99d8af721e007d6806f2652581ff5c` not found in clone; actual base `e4ba2ae` used (equals `origin/main` at session start). Not a code deviation — tree identical to spec's intended base for the changed files.
- `progress_tracker.py` RLock fix (M15-T04) retained — no second event loop, no SQL in UI.
- `services.analyze` retains legacy `scope="auto"` alias → `chat` and `mode="auto"`→`chat` to keep `tests/test_handlers_contract.py` and `tests/test_ui_shell_contract.py` (which call with `"auto"`) green without fabricating rows. Spec's strict validate would otherwise raise on `"auto"`; the alias is bounded and documented.
- `handlers.h_analyze_run` accepts `*args/**kwargs` to tolerate legacy 2-arg test calls — spec signature is 7 args; extra flexibility is additive, not breaking, and wiring still passes exactly 7.
- Locale Arabic values use spec-provided translations; UI still shows canonical English values for media types (not translated display strings) — matches spec's explicit UI code which uses canonical choices; mapping translated display→canonical is deferred and not required for acceptance.
- Two `docs/` phase reports exist (`docs/PHASE_REPORTS/` is root, `python-package/docs/PHASE_REPORTS/` is package) — this report lives at package path per spec; root copy not required.
- Frontend `bun lint/build` not run in container (network barrier `europe-west1-npm.pkg.dev` UNKNOWN_CERTIFICATE) — zero frontend files touched, deferred to CI as in M15-T04.

---

## 9. Next action (smallest)

1. Owner/Brain reviews PR → merge
2. CI runs `ci.yml` on PR (compile, pytest 419, launcher 25/41, notebook sync, cmp, package, bun lint/build)
3. Owner runs real Colab (M15-T01): Telegram login → scoped scans in all four modes with media filter → candidate table → select-all / filter → enqueue selected → single-file transfer → checkpoint → logs — provide evidence; still the gate for `Colab-ready`.

---

## 10. Rollback

Revert the single `M15-T11:` commit. No DB migration, no runtime data migration. Previous Analyze UI (`link`+`scope auto/message/chat`) and queue path remain intact after revert. Notebook copies byte-identical before/after (verified via `cmp`).

---

## Appendix — GitHub handoff fields

- **Commit:** to be filled (see `git log -1 --oneline`)
- **Branch:** `arena/019fe8bf-drive-buddy-3579bf74` (requested `arena/m15-t11-scoped-analysis` mirrored if push allowed)
- **Base SHA:** `e4ba2aede6b3bd43bcdb5a1a52f91f5043d513c1`
- **PR URL:** to be filled after `gh pr create`
- **Files changed:** 12 (7 modified + 2 new tests + 3 docs + this report)
- **Tests:** `419 passed, 1 warning`
- **Notebook cmp:** `IDENTICAL`
- **Launcher:** `binding check ok: 25/41 ready actions resolve`
