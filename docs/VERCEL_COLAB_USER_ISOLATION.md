# Per-user Colab control — architecture and acceptance gates

**Status: design decision; implementation and live validation are not complete.**

## User contract

The public Vercel app is a control-panel shell only. Every user must run their own TeleDrive engine in their own Google Colab runtime and authorize their own Google Drive and Telegram account. The app must never use the repository owner's Google, Telegram, Colab, Drive token, runtime, or files on behalf of visitors.

## Verified current state

- The Vercel preview builds successfully on `fix/vercel-tanstack-security`; this proves a build, not an operational Colab connection.
- The existing landing page describes itself as a download page.
- `/teledrive-sandbox` renders the React panel with `unavailableBridge` when it is not mounted by the Gradio component. The panel is not a hosted multi-user backend.
- The Python engine and its native Drive authorization run inside Colab. The notebook currently documents `share=False`; there is no Vercel server endpoint that starts a visitor's Colab runtime.
- There is no supported general-purpose Colab API that lets an unrelated Vercel server start and fully control arbitrary notebooks in each visitor's Google account. Do not simulate that capability or claim an OAuth login alone grants it.

## Required architecture

1. **Portal (Vercel):** public onboarding and account-independent static UI; no user secrets or shared runtime.
2. **User-owned runtime:** the user explicitly opens and starts the published notebook in their own Google Colab account. Google prompts for the user's own Drive authorization. Telegram credentials are entered only in that runtime's protected UI.
3. **Explicit pairing:** after the runtime starts, the user pairs the portal to that specific runtime through a short-lived, high-entropy, per-runtime credential. Pairing must never be done by guessing a public URL or by using a global project secret.
4. **Direct, isolated control channel:** browser requests must be authenticated to the paired runtime; every command and snapshot is bound to the runtime's unique identity. No Vercel shared process state may identify a user by an untrusted client-supplied user ID.
5. **Disconnect and expiry:** revoke pairing, expire credentials, stop polling on disconnect, and never persist Drive/Telegram access tokens in Vercel logs or browser storage.
6. **Graceful runtime loss:** Colab timeouts and disconnects must show “runtime offline”; the app must not claim it can keep a free Colab session alive indefinitely.

## Security and product gates before production

- No cross-user state, files, tokens, job status, or command routing.
- No public unauthenticated command endpoint and no secret in query strings, logs, notebook output, or client telemetry.
- Pairing tokens are random, scoped to one runtime, short-lived, revocable, and sent only over HTTPS.
- Origin/CORS and CSRF controls are explicit; server-side proxying must not become an SSRF/open-proxy endpoint.
- Integration tests prove that runtime A cannot read or control runtime B.
- Test connect, refresh, analyze, queue, cancel, disconnect, expired token, offline runtime, and malicious/invalid runtime URLs.
- Test the complete flow with two separate Google accounts and two separate Colab runtimes before enabling production.

## Implementation sequence

1. Preserve the working Python/Colab engine and the existing React-to-Gradio adapter; do not move Telegram/Drive operations into Vercel functions.
2. Build the pairing protocol and browser-to-runtime adapter, choosing a transport only after verifying it supports browser CORS/authentication and the Gradio version in this repo. A raw Vercel serverless function is not assumed to be a long-lived WebSocket relay.
3. Add the onboarding/pairing UI and clear offline state.
4. Add security tests and two-account isolation tests.
5. Only then connect the production domain and advertise remote control.

## Release note

A green Vercel build is not a green end-to-end test. Production must remain unadvertised as “full Colab control” until the gates above pass. The dependency-security PR #126 is separate from this feature and currently removes `bun.lock`; regenerate and commit a valid lockfile before merging it, rather than leaving dependency resolution non-reproducible.
