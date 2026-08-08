# PHASE 0: Audit and align (no behavior change)

**Date:** 2026-07-29 · **Authority:** Lovable Build Order v3.1, Section 4 Phase 0

Goal:
Record the truth of the repo and align metadata before any behavior change: confirm the
Section 1.1 file tree, write CONSTITUTION.md / AUDIT.md / PHASE_REPORTS/, bump the spec
version to 3.1.0, untrack the static ZIP, and pin `requirements.lock`.

Files inspected:
- Full recursive tree of `python-package/` (59 files) — compared against Section 1.1.
- `python-package/teledrive/config.py`, `python-package/.gitignore`, root `.gitignore`,
  `public/` (`TeleDrive.ipynb`, `teledrive-package.zip` 51,162 bytes, `favicon.ico`,
  `robots.txt`).

Files created:
- `python-package/docs/CONSTITUTION.md`
- `python-package/docs/AUDIT.md`
- `python-package/docs/PHASE_REPORTS/.gitkeep`
- `python-package/docs/PHASE_REPORTS/PHASE_0.md` (this file)
- `python-package/requirements.lock`

Files changed:
- `python-package/teledrive/config.py` — `version: "1.0.0" -> "3.1.0"`,
  `spec_version: "2.0" -> "3.1.0"` (defect D9, metadata half).
- `.gitignore` (repo root) — added `public/teledrive-package.zip`.
- `src/routes/index.tsx` — Prettier formatting only, zero content change, so that
  `npm run lint` is green as the phase gate requires. No copy, markup or behavior changed.

Real files confirmed: yes.
Every path listed in Section 1.1 exists as a real file. The `tests/ (+ others)` placeholder
resolves to `__init__.py`, `test_filters.py`, `test_i18n.py`, `test_queue.py`,
`test_resume.py`, `test_retry.py`, `test_snapshot.py`, `test_state_machine.py`,
`test_storage.py`, `test_telegram_links.py`.

Demo data removed: n/a for this phase — no demo data was added or removed. The static ZIP
is now git-ignored (see blockers) and will be replaced in Phase 7 by
`package_service.build_tested_archive()`.

Buttons and handlers wired: none. Phase 0 is metadata-only; the Action Registry and
UIBinder do not exist yet (Phase 2).

Service paths resolved: none. `ApplicationContext` does not exist yet (Phase 1).

Tests command:
```
python -m compileall teledrive
python -m pytest -q tests
npm run build
npm run lint
```

Actual stdout:
```
$ python -m compileall -q teledrive
compileall exit=0

$ python -m pytest -q tests
.....................................                                    [100%]
37 passed in 0.56s

$ npm run build
dist/server/_libs/@tanstack/router-core+[...].mjs     79.65 kB │ gzip:  19.95 kB
dist/server/_libs/@tanstack/react-router+[...].mjs   661.83 kB │ gzip: 139.01 kB
✓ built in 310ms
[nitro] ℹ Using auto generated worker name: tanstack-start-ts
ℹ Generated dist/server/wrangler.json
ℹ Generated .wrangler/deploy/config.json
ℹ Generated dist/client/_headers
ℹ Generated dist/nitro.json
[nitro] ✔ You can preview this build using npx vite preview

$ npm run lint
✖ 6 problems (0 errors, 6 warnings)
```
(The 6 remaining warnings are `react-refresh/only-export-components` in untouched shadcn
primitives: `badge.tsx`, `button.tsx`, `form.tsx`, `navigation-menu.tsx`, `sidebar.tsx`,
`toggle.tsx`. Zero errors.)

Actual stderr:
```
(empty for all four commands; the first pytest attempt printed
"No module named pytest" before pytest/pytest-asyncio were installed into the
verification environment — rerun above is the real result)
```

Real Telegram integration: **not verified** — deliberately untouched. No credential was
entered, no login attempted, per the final instruction of the build order.

Real Drive integration: **not verified** — deliberately untouched.

Remaining blockers:
1. **`git rm --cached public/teledrive-package.zip` was not executed.** Git state in this
   environment is managed externally and stateful git commands are unavailable to the
   agent. The path is now in the root `.gitignore`, and the file is left on disk so the
   landing page download keeps working until `package_service` exists. The owner must run
   `git rm --cached public/teledrive-package.zip` once (or it will be removed as part of
   Phase 7 when generation replaces it).
2. **`docs/CONSTITUTION.md` is a code-bound restatement, not the original v3.1 text.** The
   verbatim constitution document was never supplied to this repo; only the Build Order
   was. Every rule the Build Order binds is captured, including the resolved seven-cell
   notebook contract, and the file says so at the top. If the owner supplies the original,
   replace the file verbatim.
3. `requirements.lock` pins the versions resolved from PyPI on 2026-07-29, which includes
   `gradio==6.20.0` (a major jump from the `>=4.44.0` floor in `requirements.txt`). This
   must be smoke-tested in Colab during Phase 7 UI work; if Gradio 6 breaks the layout,
   the lock is the one place to pin back.
4. Defects D1–D8 and D10 are entirely untouched, as scheduled. `spec_version` is now 3.1.0
   but the notebook markdown still says "TeleDrive v2" — that half of D9 belongs to
   Phase 8.

Next smallest step:
**Phase 1** — create `teledrive/async_runtime.py` exactly as written in Section 3 of the
build order, add `tests/test_no_ad_hoc_loops.py`, then create `teledrive/app_context.py`
and rewrite `bootstrap.py` around `build_context()`. Awaiting owner approval before
starting.
