import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, CloudDownload, Folder, Pause, Play, RefreshCw, RotateCcw, Square, XCircle } from "lucide-react";
import type { FolderChoice, LiveUiState, TeleDriveBridge } from "./bridgeTypes";
import { formatBytes } from "./viewModel";

type UniversalTask = {
  id: string;
  title?: string;
  status: string;
  status_ar?: string;
  progress?: number;
  quality?: string;
  size_bytes?: number;
  speed_bps?: number;
  folder_name?: string;
  pause_supported?: boolean;
  error?: string;
};
type UniversalResult = { ok: boolean; message?: string; tasks?: UniversalTask[] };
type UniversalRequest = NonNullable<TeleDriveBridge["universalRequest"]>;
type Props = {
  state: LiveUiState | null;
  bridge: TeleDriveBridge;
  onSettings: () => void;
  onTasks: () => void;
  onFolderList: (parentId: string) => Promise<FolderChoice[]>;
};

const qualityOptions = [
  ["best", "أفضل جودة فيديو"],
  ["1080p", "1080p Full HD"],
  ["720p", "720p"],
  ["480p", "480p"],
  ["audio_mp3", "صوت MP3"],
  ["audio_m4a", "صوت M4A"],
] as const;

function taskActions(task: UniversalTask): Array<["pause" | "resume" | "cancel" | "retry", string]> {
  if (task.status === "paused") return [["resume", "استئناف"], ["cancel", "إلغاء"]];
  if (task.status === "queued" || task.status === "downloading") {
    return [...(task.pause_supported ? ([["pause", "إيقاف مؤقت"]] as Array<["pause", string]>) : []), ["cancel", "إلغاء"]];
  }
  if (["failed", "cancelled", "canceled"].includes(task.status)) return [["retry", "إعادة المحاولة"]];
  return [];
}

export function UniversalTaskCard({ task, onAction, busy }: {
  task: UniversalTask;
  onAction: (action: "pause" | "resume" | "cancel" | "retry", id: string) => void;
  busy: boolean;
}) {
  const pct = Math.max(0, Math.min(100, Number(task.progress) || 0));
  return (
    <article className="td-universal-task">
      <div className="td-task-head">
        <CloudDownload size={19} aria-hidden="true" />
        <div className="td-task-title">
          <strong title={task.title || task.id}>{task.title || task.id}</strong>
          <small>{task.status_ar || task.status} · {task.quality || "best"}</small>
        </div>
        <strong className="td-task-percent">{pct.toFixed(0)}%</strong>
      </div>
      <div className="td-progress td-progress-wide" role="progressbar" aria-label="تقدم المهمة" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}><span style={{ width: `${pct}%` }} /></div>
      <div className="td-task-meta">
        <span>{formatBytes(task.size_bytes ?? null)}</span>
        <span>{task.status === "downloading" ? `${formatBytes(task.speed_bps ?? null)}/s` : task.status}</span>
        <span>{task.folder_name || "Google Drive"}</span>
      </div>
      {task.error ? <p className="td-task-error" role="alert">{task.error}</p> : null}
      <div className="td-task-controls">
        {taskActions(task).map(([action, label]) => (
          <button key={action} type="button" disabled={busy} className={action === "cancel" ? "td-button td-button-danger" : "td-button td-button-secondary"}
            onClick={() => onAction(action, task.id)}>
            {action === "pause" ? <Pause size={15}/> : action === "resume" ? <Play size={15}/> : action === "retry" ? <RotateCcw size={15}/> : <XCircle size={15}/>}
            {label}
          </button>
        ))}
        {task.status === "uploading" ? <small>الرفع جارٍ؛ الإلغاء غير متاح أثناء الرفع</small> : null}
      </div>
    </article>
  );
}

export default function UniversalSection({ state, bridge, onSettings, onTasks, onFolderList }: Props) {
  const api = bridge.universalRequest;
  const [url, setUrl] = useState("");
  const [quality, setQuality] = useState("best");
  const [advanced, setAdvanced] = useState(false);
  const [folderOpen, setFolderOpen] = useState(false);
  const [folderParent, setFolderParent] = useState("root");
  const [folders, setFolders] = useState<FolderChoice[]>([]);
  const [folder, setFolder] = useState<FolderChoice | null>(null);
  const [tasks, setTasks] = useState<UniversalTask[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    if (!api || !bridge.isLive()) return;
    try {
      const result = await api("tasks");
      if (result.ok && Array.isArray(result.tasks)) setTasks(result.tasks);
    } catch {
      // A transient poll error must not erase the previous truthful snapshot.
    }
  }, [api, bridge]);

  useEffect(() => {
    if (!api || !bridge.isLive()) return;
    void refresh();
    const timer = window.setInterval(() => { if (!document.hidden) void refresh(); }, 2500);
    return () => window.clearInterval(timer);
  }, [api, bridge, refresh]);

  const perform = async (path: string, payload: Record<string, unknown> = {}) => {
    if (!api || busy) return;
    setBusy(true);
    setNotice("");
    try {
      const result: UniversalResult = await api(path, payload);
      setNotice(result.message || (result.ok ? "تم تنفيذ الإجراء." : "تعذّر تنفيذ الإجراء."));
      if (result.ok && path === "start") setUrl("");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "تعذّر الاتصال بالمحرك.");
    } finally {
      setBusy(false);
    }
  };

  const loadFolders = async () => {
    setBusy(true);
    try { setFolders(await onFolderList(folderParent)); }
    catch { setNotice("تعذّر عرض مجلدات Google Drive."); }
    finally { setBusy(false); }
  };

  return (
    <section className="td-page td-universal-section" aria-labelledby="td-universal-heading">
      <header className="td-section-title"><span className="td-eyebrow">UNIVERSAL DOWNLOADER</span><h1 id="td-universal-heading">التحميل الشامل</h1><p>روابط الفيديو، الصوت، القوائم والملفات المباشرة إلى Google Drive.</p></header>
      <div className="td-universal-layout">
        <article className="td-panel td-universal-form">
          <div className="td-task-head"><CloudDownload size={22}/><h2>تحميل جديد</h2></div>
          <label className="td-label" htmlFor="td-universal-url">رابط الفيديو أو القائمة أو الملف</label>
          <div className="td-url-line">
            <input id="td-universal-url" className="td-input" dir="ltr" type="url" placeholder="https://..." value={url} onChange={e => setUrl(e.target.value)} autoComplete="url" />
            <button className="td-button td-button-secondary" type="button" onClick={() => void navigator.clipboard?.readText().then(value => setUrl(value.trim())).catch(() => setNotice("الصق الرابط يدويًا؛ الحافظة غير متاحة."))}>لصق</button>
          </div>
          <label className="td-label" htmlFor="td-universal-quality">الجودة أو نوع الصوت</label>
          <select id="td-universal-quality" className="td-input" value={quality} onChange={e => setQuality(e.target.value)}>
            {qualityOptions.map(([value,label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <button className="td-button td-button-primary td-wide-button" type="button" disabled={!api || !bridge.isLive() || busy || !/^https?:\/\//i.test(url.trim())}
            onClick={() => void perform("start", { url: url.trim(), quality, ...(folder ? {folder_id:folder.id,folder_name:folder.name} : {}) })}>
            <CloudDownload size={18}/> بدء التحميل والرفع
          </button>
          {!api ? <p className="td-inline-note">محرك التحميل الشامل غير متاح في الاتصال الحالي. لا تُرسل أي أوامر وهمية.</p> : null}
          {notice ? <p className="td-notice" role="status">{notice}</p> : null}
          <details className="td-extra-options" open={advanced} onToggle={e => setAdvanced(e.currentTarget.open)}>
            <summary>خيارات إضافية <span>مجلد الحفظ</span></summary>
            <div className="td-stack">
              <div className="td-destination-banner"><Folder size={17}/> مجلد الحفظ: <strong>{folder?.name || state?.folder?.name || "لم يُحدد بعد"}</strong></div>
              <div className="td-button-row">
                <button type="button" className="td-button" onClick={() => setFolderOpen(v => !v)}>اختيار مجلد مختلف</button>
                {folder ? <button type="button" className="td-button" onClick={() => setFolder(null)}>استخدام المجلد العام</button> : null}
                <button type="button" className="td-button" onClick={onSettings}>إدارة Google Drive</button>
              </div>
              {folderOpen ? <div className="td-folder-picker">
                <label className="td-label">المجلد الأب (ID)
                  <input className="td-input" value={folderParent} onChange={e => setFolderParent(e.target.value)} dir="ltr"/>
                </label>
                <button type="button" className="td-button" disabled={busy} onClick={() => void loadFolders()}>عرض المجلدات</button>
                <div className="td-folder-grid">{folders.map(f => <button type="button" className="td-button" key={f.id} onClick={() => {setFolder(f);setFolderOpen(false);}}><Folder size={15}/>{f.name}</button>)}</div>
              </div> : null}
              <p className="td-inline-note">اختيار المجلد هنا يخص هذه المهمة فقط، ولا يغير مجلد Telegram.</p>
            </div>
          </details>
        </article>
        <section className="td-panel td-universal-preview" aria-label="التحميلات الأخيرة">
          <div className="td-results-head"><h2>التحميلات النشطة</h2><button className="td-button td-button-secondary" type="button" onClick={() => void refresh()}><RefreshCw size={15}/> تحديث</button></div>
          {tasks.filter(t => ["queued","downloading","paused","uploading","cancelling"].includes(t.status)).slice(0,2).map(t => <UniversalTaskCard key={t.id} task={t} busy={busy} onAction={(action,id) => { if (action === "cancel" && !window.confirm("إلغاء تحميل هذه المهمة؟")) return; void perform(action,{id}); }}/>)}
          {!tasks.some(t => ["queued","downloading","paused","uploading","cancelling"].includes(t.status)) ? <p className="td-empty-state">لا توجد تحميلات نشطة الآن.</p> : null}
          <button type="button" className="td-button td-button-secondary td-wide-button" onClick={onTasks}>عرض كل المهام</button>
          {tasks.some(t => t.status === "done" || t.status === "completed") ? <p className="td-inline-note"><CheckCircle2 size={15}/> آخر التحميلات المكتملة متاحة في صفحة المهام.</p> : null}
        </section>
      </div>
    </section>
  );
}
