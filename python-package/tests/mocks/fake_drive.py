import os
import uuid


class FakeDrive:
    def __init__(self, limit: int = 10 * 1024**3):
        self.files: dict[str, dict] = {}
        self.folders: dict[str, str] = {}
        self.limit = limit
        self.usage = 0
        self._authed = True
        self.fail_checkpoint = False
        self.checkpoints: list[str] = []

    def storage_quota(self):
        return {"limit": self.limit, "usage": self.usage}

    def find_folder(self, name, parent=None):
        for fid, meta in self.folders.items():
            if meta == name:
                return fid
        return None

    def create_folder(self, name, parent=None):
        fid = f"fld_{uuid.uuid4().hex[:8]}"
        self.folders[fid] = name
        return fid

    def ensure_folder(self, name, parent=None):
        return self.find_folder(name) or self.create_folder(name)

    def list_folders(self, parent=None):
        return [{"id": k, "name": v} for k, v in self.folders.items()]

    def find_by_source_key(self, sk):
        for fid, meta in self.files.items():
            if meta.get("appProperties", {}).get("source_key") == sk:
                return {"id": fid, "name": meta["name"], "size": str(meta["size"]),
                        "appProperties": meta["appProperties"]}
        return None

    def upload_resumable(self, file_path, drive_name, parent_id, source_key,
                          progress_cb=None, mime_type=None):
        size = os.path.getsize(file_path)
        if self.usage + size > self.limit:
            raise RuntimeError("insufficient storage")
        fid = f"file_{uuid.uuid4().hex[:8]}"
        self.files[fid] = {
            "name": drive_name, "size": size, "parent": parent_id,
            "parents": [parent_id],
            "trashed": False,
            "appProperties": {"source_key": source_key,
                              "teledrive_source_key": source_key},
        }
        self.usage += size
        if progress_cb:
            progress_cb(size, size)
        return self.get_file(fid)

    def get_file(self, file_id):
        meta = self.files.get(file_id)
        if not meta:
            return None
        return {"id": file_id, "name": meta["name"], "size": str(meta["size"]),
                "parents": list(meta.get("parents") or []),
                "trashed": bool(meta.get("trashed")),
                "appProperties": meta.get("appProperties", {})}

    def verify_uploaded(self, file_id, expected_size, parent_id, source_key):
        from teledrive.drive_client import verify_metadata
        return verify_metadata(self.get_file(file_id), expected_size, parent_id, source_key)

    def upload_bytes(self, name, data, parent_id, mime_type="application/json"):
        if self.fail_checkpoint and name.startswith("teledrive_checkpoint_"):
            raise RuntimeError("simulated checkpoint upload failure")
        if name.startswith("teledrive_checkpoint_"):
            self.checkpoints.append(name)
        fid = f"json_{uuid.uuid4().hex[:8]}"
        self.files[fid] = {"name": name, "size": len(data), "parent": parent_id,
                           "appProperties": {}, "_bytes": data,
                           "mime_type": mime_type}
        return fid

    def delete_file(self, file_id):
        self.files.pop(file_id, None)

    def upsert_bytes(self, name, data, parent_id, mime_type="application/octet-stream"):
        for fid, meta in list(self.files.items()):
            if meta.get("name") == name and meta.get("parent") == parent_id:
                self.delete_file(fid)
        return self.upload_bytes(name, data, parent_id, mime_type=mime_type)

    def download_bytes(self, file_id):
        return self.files[file_id].get("_bytes", b"")

    def list_children(self, parent_id):
        out = []
        for fid, meta in self.files.items():
            if meta.get("parent") == parent_id:
                out.append({"id": fid, "name": meta["name"],
                            "size": str(meta["size"]),
                            "modifiedTime": "2026-01-01T00:00:00Z",
                            "appProperties": meta.get("appProperties", {})})
        return out

    def revoke(self):
        self._authed = False
