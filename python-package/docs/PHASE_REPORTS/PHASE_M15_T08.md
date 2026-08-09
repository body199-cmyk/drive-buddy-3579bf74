# PHASE M15-T08 — publish the pinned release `pkg-2026.08.09-m15t07`

Executor: LM Arena Agent · Branch: `arena/019fe868-drive-buddy-3579bf74`
Canonical repo: `body199-cmyk/drive-buddy-3579bf74` (public)
Date: 2026-08-09 UTC

## 1. Scope and baseline

This task was release publication only. No source file, notebook, frontend file, workflow, or
file under `python-package/teledrive/` was changed. The release target was checked before any
release operation:

```text
$ git rev-parse origin/main
10b5d3b1b74542b2388983a2cc582c4906154982

$ git rev-parse HEAD
10b5d3b1b74542b2388983a2cc582c4906154982
```

The merge tree was `78400cd3e8763d0fffee37453fa240f5ffb63f68`, as specified by the task.

## 2. CI and artifact evidence

The pinned post-merge CI run was independently checked through GitHub:

```text
$ gh run view 31329502070 --json databaseId,headSha,status,conclusion,event,workflowName,url
{"conclusion":"success","databaseId":31329502070,"event":"push","headSha":"10b5d3b1b74542b2388983a2cc582c4906154982","status":"completed","url":"https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31329502070","workflowName":"CI"}
```

The artifact API returned the following real metadata:

```text
{
  "id": 9042509940,
  "name": "teledrive-package",
  "size_in_bytes": 177890,
  "expired": false,
  "digest": "sha256:13f010e29d4c3ce5cca2403a4133c2abc56a23315a10d25bd2f090d0a791e133",
  "created_at": "2026-08-09T18:38:24Z",
  "expires_at": "2026-11-07T18:37:24Z",
  "workflow_run": {
    "id": 31329502070,
    "head_sha": "10b5d3b1b74542b2388983a2cc582c4906154982"
  }
}
```

The normal direct artifact download path was attempted twice (`gh run download` and the REST
artifact ZIP endpoint). Both reached the signed Actions storage URL and failed with `EOF` in
this execution environment before any bytes could be extracted. No signed URL or credential was
stored in the repository or this report.

As a byte-level cross-check of the artifact metadata, the GitHub Actions artifact ZIP wrapper was
recreated with the `@actions/artifact` ZIP implementation, one `teledrive_v4.5.zip` entry, and the
artifact creation timestamp `2026-08-09 18:38:24 UTC`. The resulting wrapper matched the GitHub
artifact digest and size exactly:

```text
$ sha256sum /tmp/artifact-repro/matched-wrapper.zip
13f010e29d4c3ce5cca2403a4133c2abc56a23315a10d25bd2f090d0a791e133  /tmp/artifact-repro/matched-wrapper.zip

$ stat -c%s /tmp/artifact-repro/matched-wrapper.zip
177890

$ unzip -l /tmp/artifact-repro/matched-wrapper.zip
  Length      Date    Time    Name
---------  ----------  -----   ----
   188695  2026-08-09 18:38   teledrive_v4.5.zip
---------                     ----
   188695                     1 file
```

Extracting the matched wrapper's inner entry produced the same bytes as the reproducible Path A
build below. This is recorded as a derived artifact-inner check; direct extraction from GitHub was
not possible because of the storage endpoint `EOF`.

## 3. Path A build and archive verification

The lock-pinned dependencies were installed in a temporary virtual environment outside the
repository. The required build command completed successfully:

```text
$ python -m teledrive.package_service --build --output /tmp/teledrive-path-a/teledrive_v4.5.zip
2026-08-09T21:24:35+00:00 tests passed
archive: /tmp/teledrive-path-a/teledrive_v4.5.zip
0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce  /tmp/teledrive-path-a/teledrive_v4.5.zip
188695
```

The measured archive digest and size are therefore:

```text
sha256: 0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce
size_bytes: 188695
```

The archive layout gate passed:

```text
$ unzip -l /tmp/teledrive-path-a/teledrive_v4.5.zip | grep -E "teledrive-v4\\.5/requirements\\.lock"
      393  2020-01-01 00:00   teledrive-v4.5/requirements.lock
```

The earlier phase report's `3452060306c38bd4789bb49e28a66a7f48935623ba6915e5fdd4d20be85baa84`
was treated as an expectation, not as truth. It is the digest obtained when the newly committed
`PHASE_M15_T07.md` file is omitted. The current `10b5d3b1...` tree includes that report, and the
current build plus the artifact wrapper both measure `0179970f...`. Per the DOC contract, the
published object must be the measured current-tree object, not the stale expectation.

## 4. Manifest staged for publication

The manifest was generated from the measured archive bytes, with exactly the required fields:

```json
{
  "schema": 1,
  "release": "pkg-2026.08.09-m15t07",
  "commit": "10b5d3b1b74542b2388983a2cc582c4906154982",
  "product_version": "4.5.0",
  "sha256": "0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce",
  "size_bytes": 188695,
  "archive_url": "https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_v4.5.zip"
}
```

## 5. Release operation and rollback

The first combined `gh release create` operation created the tag/release record but failed while
uploading the first asset. The exact GitHub CLI error was:

```text
Post "https://uploads.github.com/repos/body199-cmyk/drive-buddy-3579bf74/releases/367589798/assets?label=&name=teledrive_v4.5.zip": EOF
```

A no-asset release record was then created to verify the target metadata, but the task's rollback
was applied because the release did not contain the required two assets:

```text
$ gh release delete pkg-2026.08.09-m15t07 --yes --cleanup-tag
rollback complete
```

No release or tag remains. This prevented a partial release from being mistaken for a valid Cell-1
update endpoint. The public endpoint checks after rollback returned:

```text
https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_manifest.json
http_status=404 content_type=text/plain; charset=utf-8 bytes=9
Not Found

https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_v4.5.zip
http_status=404 content_type=text/plain; charset=utf-8 bytes=9
Not Found
```

## 6. Mandatory final report

```plain
GitHub Status:
Release: FAILED (rolled back; no release remains)
Tag: pkg-2026.08.09-m15t07
Target SHA: 10b5d3b1b74542b2388983a2cc582c4906154982
Assets: none; upload endpoint closed with EOF before the first asset completed
Inner archive sha256 (built): 0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce
Inner archive sha256 (artifact 9042509940): 0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce (derived from an exact wrapper-digest match; direct extraction was blocked)
Inner archive size_bytes: 188695
Manifest URL (public, unauthenticated fetch result): HTTP 404 Not Found after rollback
Archive URL (public, unauthenticated fetch result): HTTP 404 Not Found after rollback
Docs commit / PR URL: recorded by the final GitHub handoff after the docs-only PR
Operation error, if any: GitHub Actions storage download and GitHub release asset upload endpoints returned EOF from this sandbox; the release was rolled back safely
Honest status: Code-complete candidate; release publication blocked by the GitHub upload endpoint
```

No `Colab-ready` claim is made. A subsequent execution with a GitHub connection that can reach
`uploads.github.com` can rerun the release creation and asset upload using the staged manifest
values above; no source changes are needed.
