# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Login code never arrives | Telegram sends it inside the app on desktop, not by SMS | Open Telegram app, check the "Telegram" service chat |
| `PhoneCodeInvalidError` | Wrong or expired code | Press "Send code" again, retype quickly |
| `SessionPasswordNeededError` | 2FA enabled | Fill the 2FA password field before Verify |
| `FloodWaitError` shown as auto-retry | Telegram rate limit | Wait; TeleDrive honors the exact seconds returned |
| Drive says "insufficient storage" | Your Drive is full | Free space in Drive or use a different account |
| Colab session died mid-transfer | Free Colab does that | Re-run cells 1–4, press "Recover from Drive", then Start |
| OAuth returns "access blocked" | Your email is not in Test users | In Cloud Console → OAuth consent screen → Test users, add your email |
| Uploaded file size mismatch | Rare network glitch during upload | Item marked Failed. Temp file kept. Delete temp manually or retry from queue |
| Duplicate file skipped | Same `source_key` already in Drive | Intended. To re-upload, remove the Drive file first |
| UI language stuck | Language toggled in state | Refresh the Gradio tab; queue state is unaffected |

## Rules that never bend
- Temp file is deleted only after a verified Drive upload.
- Only `QueueManager` mutates item state.
- No secrets in code, logs, or docs. Ever.
