# Runbook

## First run
1. Open `notebook/TeleDrive.ipynb` in Colab (File → Upload notebook).
2. Cell 1: Upload the TeleDrive package ZIP when prompted.
3. Cell 2: `bootstrap.run()` — should print `schema_version=1` and the runtime dirs.
4. Cell 3: paste your Telegram `api_id` and `api_hash` into `getpass` prompts (never plaintext in cells).
5. Cell 4: `app.launch(share=False, inline=True)` — Gradio opens.
6. In the Telegram tab: type your phone → Send code → paste the code Telegram sends (in-app, not SMS) → verify.
7. In the Drive tab: upload your OAuth Desktop client JSON → open the returned URL → paste the auth code back.
8. In "Link & Analyze": paste a Telegram link → Analyze → review the file list.
9. In Transfer settings: pick Safe/Balanced/Fast → Start.

## Recovery after Colab disconnect
1. Reconnect the runtime.
2. Re-run cells 1–4 (bootstrap re-authenticates via saved session/token if they still exist).
3. In Transfer settings, press "Recover from Drive" — this pulls the newest checkpoint and reconciles queue state against Drive.
4. Press Start again.

## Reboot prompt (paste above HANDOFF.md into a new AI chat)
> You are receiving a project handoff. Read HANDOFF.md, do NOT invent state, do NOT reset progress. Continue from "Next smallest step".
