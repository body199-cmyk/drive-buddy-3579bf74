# M52-T01 — Public TeleDrive Portal: implementation foundation

Status: IN PROGRESS — portal route added on a feature branch; OAuth, persistence, worker bridge and live deployment are NOT implemented yet.

## Non-negotiable compatibility boundary
- Do not edit or replace the existing Colab notebooks, `colab_cells.json`, Python transfer engine, Telegram Vault, package launcher, lockfiles, or current landing route as part of the portal foundation.
- The existing Colab workflow remains the working baseline. Portal code must be additive and introduced behind an explicit worker bridge.
- No fake transfer rows, fake progress, or claims of connected services. UI states must be based on backend/worker responses once implemented.

## User journey target
1. User visits the public portal and authenticates with Google OAuth.
2. Drive access is granted as a separate OAuth consent, requesting minimum scopes.
3. Telegram setup is guided according to the actual TeleDrive capability (user session vs bot token); never collect secrets in client-side fields or logs.
4. A per-user worker enrollment token is generated server-side. The Colab worker opens an outbound authenticated connection and renews a short lease/heartbeat.
5. Portal commands are scoped to the authenticated user and accepted only after the worker acknowledges them.
6. UI reports offline state when the Colab session expires. Do not promise Vercel can start a Colab runtime automatically.

## Security and reliability gates before public launch
- Add real authentication and verify sessions on every server endpoint.
- Store refresh tokens and Telegram credentials only server-side in encrypted storage; do not persist credentials in localStorage or expose them to React.
- Add per-user data isolation, CSRF/state checks for OAuth, rate limits, short-lived worker tokens, nonce/idempotency on commands, lease expiry, revocation, and secret redaction.
- Choose persistent storage before storing user accounts or credentials; do not use ephemeral Vercel filesystem or SQLite in serverless functions as shared durable state.
- Add Google OAuth consent screen/authorized redirect URI configuration outside source control; credentials must be configured as Vercel environment secrets.
- Add tests for cross-user access denial, expired sessions, worker disconnect, duplicate commands, and secret redaction.
- Validate the actual Colab worker bridge in a separate test notebook/session before enabling controls. Preserve current notebook operation.

## Current implementation
- `src/routes/portal.tsx` adds an isolated RTL portal route at `/portal`.
- It explicitly shows integrations as unconfigured/offline and disables Google sign-in until OAuth is actually configured.
- The current root landing page is untouched.
- Vercel project creation/linking was blocked: the authenticated Vercel connection has no visible teams and cannot access the intended scope; Git integration also reports that this Vercel connection lacks write/admin access to the repository. No deployment was completed.
