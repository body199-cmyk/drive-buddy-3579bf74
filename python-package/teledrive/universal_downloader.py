# -*- coding: utf-8 -*-
"""Universal URL Downloader (yt-dlp + gdown + direct HTTP) -> Google Drive.

Completely isolated from Telegram / MTProto flows. Uses the active
ApplicationContext only to read the selected Drive destination folder and
upload completed files via the official DriveService.upload_resumable.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import TEMP_DIR
from .logging_config import get_logger
from .redaction import redact

_log = get_logger("teledrive.universal_downloader")


class UniversalDownloadManager:
    """Thread-safe background downloader for external URLs."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx
        self._lock = threading.Lock()
        self._tasks: list[dict[str, Any]] = []
        self._cancel_events: dict[str, threading.Event] = {}
        self._yt_dlp_update_checked = False

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(t) for t in reversed(self._tasks[-30:])]

    def clear_finished(self) -> int:
        with self._lock:
            before = len(self._tasks)
            self._tasks = [t for t in self._tasks if t.get("status") in {"queued", "downloading", "uploading"}]
            return before - len(self._tasks)

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        """Cancel an active download before it enters the Drive upload phase."""
        with self._lock:
            task = next((item for item in self._tasks if item.get("id") == task_id), None)
            if task is None:
                return {"ok": False, "message": "مهمة التحميل غير موجودة."}
            if task.get("status") not in {"queued", "downloading"}:
                return {
                    "ok": False,
                    "message": "لا يمكن الإلغاء بعد بدء الرفع إلى Google Drive.",
                }
            event = self._cancel_events.get(task_id)
            if event is None:
                return {"ok": False, "message": "المهمة انتهت بالفعل."}
            event.set()
            task.update(status="cancelling", status_ar="⏹️ جاري إلغاء التحميل...")
        return {"ok": True, "message": "تم طلب إلغاء التحميل."}

    def _is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            event = self._cancel_events.get(task_id)
            return bool(event and event.is_set())

    def start_download(
        self,
        url: str,
        quality: str = "best",
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        clean_url = (url or "").strip()
        if not clean_url or not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            return {"ok": False, "message": "يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://"}

        # التحقق من اتصال Google Drive واختيار المجلد
        try:
            drive_service = self.ctx.drive_client
            if drive_service is None:
                drive_service = self.ctx.drive_auth.require_service()
        except Exception:
            return {"ok": False, "message": "يرجى ربط حساب Google Drive أولاً من قسم الحسابات."}

        target_folder_id = (folder_id or "").strip()
        target_folder_name = ""
        if not target_folder_id:
            selected = self.ctx.drive_folders.selected()
            if selected is None:
                return {"ok": False, "message": "يرجى اختيار مجلد الحفظ في Google Drive أولاً (من قسم الوجهة أو القائمة أعلاه)."}
            target_folder_id = selected.id
            target_folder_name = selected.name or selected.id
        else:
            target_folder_name = self.ctx.drive_folders.current_folder_name() or target_folder_id

        task_id = f"udl-{uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "url": clean_url,
            "quality": quality,
            "folder_id": target_folder_id,
            "folder_name": target_folder_name,
            "title": clean_url[:65],
            "status": "queued",
            "status_ar": "في الانتظار...",
            "progress": 0.0,
            "size_bytes": 0,
            "speed_bps": 0.0,
            "drive_file_id": "",
            "error": "",
            "created_at": time.strftime("%H:%M:%S"),
        }
        with self._lock:
            self._tasks.append(task)
            self._cancel_events[task_id] = threading.Event()

        worker = threading.Thread(
            target=self._run_task,
            args=(task_id, clean_url, quality, target_folder_id),
            name=f"universal-dl-{task_id}",
            daemon=True,
        )
        worker.start()
        return {"ok": True, "task": dict(task), "message": "تم بدء التحميل في الخلفية بنجاح!"}

    def _update(self, task_id: str, **kwargs: Any) -> None:
        with self._lock:
            for t in self._tasks:
                if t["id"] == task_id:
                    t.update(kwargs)
                    break

    def _ensure_packages(self) -> None:
        """Ensure both optional downloader backends are importable.

        Some Colab sessions already have yt-dlp but not gdown. Checking only
        yt-dlp silently skipped installation and made every Google Drive URL
        fail later with ModuleNotFoundError. Verify both modules and surface a
        useful error if the runtime cannot install them.
        """
        import importlib
        import subprocess
        import sys

        packages = {"yt_dlp": "yt-dlp", "gdown": "gdown"}
        missing = []
        for module_name in packages:
            try:
                importlib.import_module(module_name)
            except ImportError:
                missing.append(packages[module_name])

        install_args = list(missing)
        if not self._yt_dlp_update_checked:
            install_args = ["--upgrade", "yt-dlp[default]", *install_args]

        if install_args:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", *install_args],
                check=False,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()[-500:]
                label = ", ".join(missing) if missing else "yt-dlp update"
                raise RuntimeError(
                    "تعذر تثبيت/تحديث مكونات التحميل المطلوبة "
                    f"({label}). "
                    f"{detail or 'تحقق من اتصال الإنترنت ثم أعد المحاولة.'}"
                )
            self._yt_dlp_update_checked = True

        importlib.invalidate_caches()
        still_missing = []
        for module_name, package_name in packages.items():
            try:
                importlib.import_module(module_name)
            except ImportError:
                still_missing.append(package_name)
        if still_missing:
            raise RuntimeError(
                "تمت محاولة تثبيت مكونات التحميل لكنها ما زالت غير متاحة: "
                + ", ".join(still_missing)
            )

    def _run_task(self, task_id: str, url: str, quality: str, folder_id: str) -> None:
        work_dir = Path(TEMP_DIR) / "universal_dl" / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._update(task_id, status="downloading", status_ar="جاري التحضير والتحميل...", progress=2.0)
            if self._is_cancelled(task_id):
                raise RuntimeError("cancelled")
            self._ensure_packages()
            if self._is_cancelled(task_id):
                raise RuntimeError("cancelled")

            downloaded_files = self._download_to_dir(task_id, url, quality, work_dir)
            if self._is_cancelled(task_id):
                raise RuntimeError("cancelled")
            if not downloaded_files:
                raise RuntimeError("لم يتم العثور على ملفات محملة من هذا الرابط.")

            drive_svc = self.ctx.drive_client
            if drive_svc is None:
                from .drive_client import DriveService
                drive_svc = DriveService.from_auth(self.ctx.drive_auth)

            total_files = len(downloaded_files)
            last_drive_id = ""
            for idx, file_path in enumerate(downloaded_files, start=1):
                if self._is_cancelled(task_id):
                    raise RuntimeError("cancelled")
                fname = file_path.name
                fsize = file_path.stat().st_size if file_path.exists() else 0
                self._update(
                    task_id,
                    title=fname if total_files == 1 else f"({idx}/{total_files}) {fname}",
                    size_bytes=fsize,
                    status="uploading",
                    status_ar=f"☁️ جاري الرفع إلى Drive ({idx}/{total_files})...",
                    progress=85.0,
                    speed_bps=0.0,
                )

                source_hash = hashlib.sha256(f"{url}::{fname}::{quality}".encode("utf-8")).hexdigest()[:24]
                source_key = f"url:{source_hash}"
                mime_type, _ = mimetypes.guess_type(str(file_path))

                upload_sample = {"sent": 0, "time": time.monotonic()}

                def _on_upload_prog(sent: int, total: int) -> None:
                    now = time.monotonic()
                    elapsed = now - upload_sample["time"]
                    speed_bps = (
                        max(0, sent - upload_sample["sent"]) / elapsed
                        if elapsed > 0
                        else 0.0
                    )
                    upload_sample.update(sent=sent, time=now)
                    pct = 85.0 + (14.0 * (sent / max(total, 1)))
                    self._update(
                        task_id,
                        progress=round(min(pct, 99.0), 1),
                        speed_bps=round(speed_bps, 1),
                    )

                res = drive_svc.upload_resumable(
                    file_path=str(file_path),
                    drive_name=fname,
                    parent_id=folder_id,
                    source_key=source_key,
                    progress_cb=_on_upload_prog,
                    mime_type=mime_type or "application/octet-stream",
                )
                last_drive_id = str(res.get("id") or "")

            self._update(
                task_id,
                status="completed",
                status_ar="✅ اكتمل الحفظ في Drive",
                progress=100.0,
                speed_bps=0.0,
                drive_file_id=last_drive_id,
            )
            _log.info("universal download completed task=%s files=%d", task_id, total_files)
        except Exception as exc:  # noqa: BLE001
            if self._is_cancelled(task_id):
                self._update(
                    task_id,
                    status="cancelled",
                    status_ar="⏹️ تم إلغاء التحميل",
                    error="",
                    speed_bps=0.0,
                )
            else:
                err_msg = redact(str(exc))[:240]
                _log.warning("universal download failed task=%s: %s", task_id, err_msg)
                self._update(
                    task_id,
                    status="failed",
                    status_ar=f"❌ فشل: {err_msg}",
                    error=err_msg,
                    speed_bps=0.0,
                )
        finally:
            with self._lock:
                self._cancel_events.pop(task_id, None)
            shutil.rmtree(work_dir, ignore_errors=True)

    def _download_to_dir(self, task_id: str, url: str, quality: str, work_dir: Path) -> list[Path]:
        lower_url = url.lower()

        # 1. روابط Google Drive العامة عبر gdown
        if "drive.google.com" in lower_url or "docs.google.com" in lower_url:
            import gdown
            self._update(task_id, status_ar="📁 جاري التحميل من Google Drive...")
            if "/folders/" in lower_url:
                gdown.download_folder(url=url, output=str(work_dir), quiet=True, use_cookies=False)
            else:
                gdown.download(url=url, output=str(work_dir) + "/", quiet=True, fuzzy=True)
            if self._is_cancelled(task_id):
                raise RuntimeError("cancelled")
            return [p for p in work_dir.rglob("*") if p.is_file() and not p.name.endswith(".part")]

        # 2. الروابط المباشرة السريعة للملفات (PDF, ZIP, RAR, إلخ)
        direct_exts = (".pdf", ".zip", ".rar", ".7z", ".apk", ".iso", ".docx", ".xlsx", ".pptx", ".csv", ".txt")
        path_part = lower_url.split("?")[0]
        if path_part.endswith(direct_exts):
            fname = os.path.basename(path_part) or f"file_{task_id}"
            dest = work_dir / fname
            self._update(task_id, title=fname, status_ar="⚡ جاري تحميل الملف المباشر...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                read = 0
                last_sample_bytes = 0
                last_sample_time = time.monotonic()
                while True:
                    if self._is_cancelled(task_id):
                        raise RuntimeError("cancelled")
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    read += len(chunk)
                    now = time.monotonic()
                    elapsed = now - last_sample_time
                    speed_bps = (
                        max(0, read - last_sample_bytes) / elapsed
                        if elapsed > 0
                        else 0.0
                    )
                    if elapsed >= 0.5:
                        last_sample_bytes, last_sample_time = read, now
                    self._update(
                        task_id,
                        progress=round((read / total) * 80.0, 1) if total > 0 else 40.0,
                        size_bytes=total or read,
                        speed_bps=round(speed_bps, 1),
                    )
            return [dest]

        # 3. جميع مواقع الفيديو والمنصات والصوتيات عبر yt-dlp
        import yt_dlp

        fmt_map = {
            "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
            "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
            "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
            "audio_mp3": "bestaudio/best",
            "audio_m4a": "bestaudio[ext=m4a]/bestaudio/best",
        }
        selected_fmt = fmt_map.get(quality, fmt_map["best"])

        def _yt_hook(d: dict[str, Any]) -> None:
            if self._is_cancelled(task_id):
                raise yt_dlp.utils.DownloadError("Download cancelled by user")
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                info = d.get("info_dict") or {}
                title = info.get("title")
                pct = (downloaded / total * 80.0) if total else 40.0
                self._update(
                    task_id,
                    title=str(title or url)[:70],
                    progress=round(min(pct, 82.0), 1),
                    size_bytes=int(total or downloaded),
                    speed_bps=round(float(d.get("speed") or 0.0), 1),
                    status_ar=f"⬇️ جاري التحميل ({int(pct / 0.8)}%)...",
                )
            elif d.get("status") == "finished":
                self._update(task_id, progress=83.0, status_ar="🔧 جاري معالجة ودمج الميديا...")

        ydl_opts: dict[str, Any] = {
            "format": selected_fmt,
            "outtmpl": str(work_dir / "%(title).120s.%(ext)s"),
            "progress_hooks": [_yt_hook],
            "noplaylist": False,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4" if not quality.startswith("audio") else None,
        }

        if "youtube.com" in lower_url or "youtu.be" in lower_url:
            # Do not pin a single YouTube player client: YouTube can mark one
            # client LOGIN_REQUIRED while another works. Let current yt-dlp
            # choose its supported defaults and install recommended EJS
            # dependencies through yt-dlp[default].
            ydl_opts["sleep_interval_requests"] = 1
            ydl_opts["extractor_retries"] = 3
            ydl_opts["retries"] = 3
            ydl_opts["socket_timeout"] = 30

            # Optional Netscape-format cookies can be uploaded to Colab by the
            # user. Never store cookies in the repository or log their contents.
            cookie_candidates = [
                os.environ.get("YTDLP_COOKIES_FILE", ""),
                "/content/youtube_cookies.txt",
                "/content/cookies.txt",
                str(Path(TEMP_DIR) / "youtube_cookies.txt"),
            ]
            cookie_file = next(
                (Path(p).expanduser() for p in cookie_candidates
                 if p and Path(p).expanduser().is_file()),
                None,
            )
            if cookie_file is not None:
                ydl_opts["cookiefile"] = str(cookie_file)

        if quality == "audio_mp3":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]

        is_youtube = "youtube.com" in lower_url or "youtu.be" in lower_url
        attempts = [ydl_opts]
        if is_youtube:
            # Try the normal current yt-dlp defaults first. Only after YouTube
            # rejects that attempt as a bot, retry a second supported client
            # profile; forcing this profile for every video can break videos
            # that work with the default player.
            fallback_opts = dict(ydl_opts)
            fallback_opts["extractor_args"] = {
                "youtube": {"player_client": ["tv", "web_safari"]}
            }
            attempts.append(fallback_opts)

        last_bot_error = None
        for attempt_index, attempt_opts in enumerate(attempts):
            try:
                with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                    ydl.download([url])
                break
            except yt_dlp.utils.DownloadError as exc:
                message = str(exc)
                is_bot_challenge = (
                    ("Sign in to confirm you're not a bot" in message)
                    or ("LOGIN_REQUIRED" in message)
                ) and is_youtube
                if not is_bot_challenge:
                    raise
                last_bot_error = exc
                if attempt_index < len(attempts) - 1:
                    _log.warning(
                        "YouTube default player was challenged; retrying with fallback player profile"
                    )
                    continue

                cookie_hint = (
                    " تم العثور على ملف cookies محليًا واستخدامه في المحاولتين؛ "
                    "إذا استمر الخطأ فصدّر Cookies حديثة من المتصفح."
                    if ydl_opts.get("cookiefile")
                    else
                    " لم يتم العثور على Cookies صالحة. إذا استمر الرفض، صدّر Cookies يوتيوب بصيغة Netscape "
                    "وارفعها بنفسك إلى جلسة Colab باسم /content/youtube_cookies.txt. "
                    "لا ترسل الملف لأي شخص ولا ترفعه إلى GitHub لأنه يحتوي بيانات جلسة حسابك."
                )
                raise RuntimeError(
                    "يوتيوب رفض طلب التحميل حتى بعد تجربة إعدادات yt-dlp الافتراضية وملف تعريف بديل. "
                    "قد يكون السبب حظر عنوان IP الخاص بـ Colab أو اشتراط جلسة موثّقة."
                    + cookie_hint
                ) from exc
        if self._is_cancelled(task_id):
            raise RuntimeError("cancelled")

        return [p for p in work_dir.rglob("*") if p.is_file() and not p.name.endswith((".part", ".ytdl"))]


def get_universal_downloader(ctx: Any) -> UniversalDownloadManager:
    mgr = getattr(ctx, "_universal_downloader", None)
    if mgr is None:
        mgr = UniversalDownloadManager(ctx)
        ctx._universal_downloader = mgr
    return mgr
