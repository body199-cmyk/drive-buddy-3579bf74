# AI_HANDOFF — Live handoff

> This file records the latest execution session only. Historical evidence is in
> `python-package/docs/PHASE_REPORTS/PHASE_M15_T08.md`.

## Session card

| Field | Value |
|---|---|
| UTC date | 2026-08-09 |
| Session type | M15-T08 — publish the pinned release `pkg-2026.08.09-m15t07` |
| TASK ID | `M15-T08` |
| Repository | `body199-cmyk/drive-buddy-3579bf74` (public) |
| Fixed branch | `arena/019fe868-drive-buddy-3579bf74` |
| HEAD before docs | `10b5d3b1b74542b2388983a2cc582c4906154982` |
| Required release target | `10b5d3b1b74542b2388983a2cc582c4906154982` |
| Merge tree | `78400cd3e8763d0fffee37453fa240f5ffb63f68` |
| Status | `BLOCKED` — release asset upload endpoint returned `EOF`; partial release was rolled back |
| Protected/source files changed | None. Only the requested permanent-memory docs are changed in this session. |
| Last green CI | Run `31329502070` · `https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31329502070` · success · HEAD `10b5d3b1...` |
| Rollback | `gh release delete pkg-2026.08.09-m15t07 --yes --cleanup-tag` — completed; no tag or release remains |
| Next step | From an environment able to reach `uploads.github.com`, publish the two assets using the measured manifest values, then perform the unauthenticated endpoint checks. |

## Verified evidence

- `origin/main` and the session HEAD were both exactly `10b5d3b1b74542b2388983a2cc582c4906154982` before the release operation.
- CI run `31329502070` completed successfully for that SHA.
- Artifact `9042509940` is unexpired through `2026-11-07T18:37:24Z`, has wrapper size `177890`, and API digest `sha256:13f010e29d4c3ce5cca2403a4133c2abc56a23315a10d25bd2f090d0a791e133`.
- The lock-pinned Path A build ran `402` tests through the package builder and produced:
  - inner SHA-256: `0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce`
  - inner size: `188695` bytes
  - required layout: `teledrive-v4.5/requirements.lock`
- Recreating the GitHub Actions artifact wrapper with the recorded artifact timestamp matched the artifact wrapper digest and size exactly. The direct signed storage download itself was blocked by `EOF`, so this is recorded as a derived artifact-inner check rather than a direct extraction claim.
- The stale expectation `3452060306c38bd4789bb49e28a66a7f48935623ba6915e5fdd4d20be85baa84` was not used; it omits the phase-report file present in the current tree.
- The manifest was generated with only the required fields and the measured digest/size. It was not published because the asset upload did not complete.

## GitHub release status

```plain
Release: FAILED (rolled back)
Tag: pkg-2026.08.09-m15t07
Target SHA: 10b5d3b1b74542b2388983a2cc582c4906154982
Assets: none
Upload error: Post https://uploads.github.com/.../assets?name=teledrive_v4.5.zip: EOF
Manifest endpoint after rollback: HTTP 404 Not Found
Archive endpoint after rollback: HTTP 404 Not Found
```

No secret, token, signed artifact URL, or credential is stored in the repository. No `Colab-ready`
claim is made; the real owner-run Telegram/Drive Colab proof remains separate.

## Final report location

- Phase report: `python-package/docs/PHASE_REPORTS/PHASE_M15_T08.md`
- TODO entry: `docs/TODO.md` (`M15-T08 = BLOCKED`)
- Docs-only commit and PR URL: to be recorded in the final GitHub handoff after the fixed branch is pushed and reviewed.
