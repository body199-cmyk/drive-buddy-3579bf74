# M51-T01 — YouTube Arabic + English audio tracks

**Date:** 2026-10-21  
**Status:** Implemented on branch; PR/CI and real YouTube validation pending.  
**Branch:** `feature/youtube-ar-en-audio-tracks`

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
- Automated tests have been added, but have **not yet been run in this task**. The PR CI result must be checked before calling the code test-passed.
- No real YouTube video has been downloaded with this change, and no Colab/Google Drive runtime test has been performed.
- Some videos may not expose audio language metadata consistently, and not every YouTube video offers both Arabic and English tracks. In those cases the selector falls back rather than intentionally failing the download.
- Switching tracks after download depends on the playback app supporting multiple MKV audio tracks. VLC is a common option; some gallery players may only play the default track.

## Next steps

1. Review the diff and ensure the selector works with current yt-dlp format syntax.
2. Run the existing Python test suite and package/CI checks.
3. After merge and release publication, test a public YouTube video known to have Arabic and English tracks in Colab; verify both tracks are listed in the resulting MKV and can be switched in a player.
4. Update the handoff with the actual CI result and separately record live validation. Do not claim Colab or real-video success from unit tests alone.

## Rollback

Revert the feature PR/commit. The change is isolated to the Universal Downloader and its tests; it does not modify Telegram, Drive Vault, database schema, or queue architecture.
