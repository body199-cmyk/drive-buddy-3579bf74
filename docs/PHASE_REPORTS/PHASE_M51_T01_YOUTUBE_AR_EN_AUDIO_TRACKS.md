# M51-T01 — YouTube Arabic + English audio tracks

**Date:** 2026-10-21  
**Status:** Merged to main; CI passed; live YouTube/Colab validation and a release containing this commit are still pending.  
**PR:** [#123](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/123) (merged)  
**Merge commit:** `325848978f1f4def008df8210bc6ca15284626ca`  
**CI:** [Run #39624150025](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39624150025) passed Python package/tests + Colab contract checks, archive build, and frontend lint/build.

## Requirement

When downloading a YouTube video through the Universal Downloader, keep Arabic and English audio tracks in one downloadable file when both are available, so the user can switch tracks in a compatible player. Ignore unrelated languages.

## Implementation

- Added `_youtube_multiaudio_format()` in `python-package/teledrive/universal_downloader.py`.
- The format selector prefers both Arabic and English tracks, then gracefully falls back to either available track, then the best available audio/original track if neither requested language is exposed.
- Language prefix matching supports variants such as `en-US`.
- Enables yt-dlp `audio_multistreams` only for YouTube video downloads; uses MKV as the output container for multi-audio compatibility.
- Keeps audio-only downloads and non-YouTube platform behavior on the existing paths.
- Adds selector and downloader-option regression tests in `python-package/tests/test_universal_downloader.py`.

## Evidence and limits

- The implementation follows yt-dlp's multi-audio format-selection and merge options; multiple audio streams require a compatible container and FFmpeg.
- Automated tests and package checks passed in CI run #39624150025. The frontend lint/build also passed. This is CI evidence only, not live runtime verification.
- No real YouTube video has been downloaded with this change, and no Colab/Google Drive runtime test has been performed.
- Some videos may not expose audio language metadata consistently, and not every YouTube video offers both Arabic and English tracks. In those cases the selector falls back rather than intentionally failing the download.
- Switching tracks after download depends on the playback app supporting multiple MKV audio tracks. VLC is a common option; some gallery players may only play the default track.

## Next steps

1. After publishing a new package/release containing merge commit `325848978f1f4def008df8210bc6ca15284626ca`, verify the release ZIP + manifest/hash/commit so Colab will not use a stale package.
2. Test a public YouTube video known to expose Arabic and English tracks in Colab; verify both streams exist in the resulting MKV and can be switched in a compatible player.
3. Update the handoff with the actual release and live-test evidence. Do not claim Colab or real-video success from unit tests alone.

## Rollback

Revert the feature PR/commit. The change is isolated to the Universal Downloader and its tests; it does not modify Telegram, Drive Vault, database schema, or queue architecture.
