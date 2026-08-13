import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  AlertCircle,
  Check,
  Cloud,
  FileArchive,
  FileText,
  Folder,
  Gauge,
  Info,
  LogOut,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  Square,
  Terminal,
  UploadCloud,
  UserRound,
} from "lucide-react";
import {
  newRequestId,
  unavailableBridge,
  type BridgeLanguage,
  type BridgeResponse,
  type FolderChoice,
  type LiveUiState,
  type TeleDriveBridge,
} from "./bridgeTypes";
import {
  enqueueBlockReason,
  formatBytes,
  groupQueueSessions,
  hasActiveTransfer,
  localize,
  mediaChoices,
  pageLabels,
  queueMetrics,
  scanModes,
  selectableCandidates,
  selectedVisibleCandidates,
  validateAnalyzeInput,
  type MediaType,
  type Page,
  type ScanMode,
} from "./viewModel";

/** Quiet auto-refresh heartbeat: how often the live snapshot is polled while a transfer is moving. */
const AUTO_REFRESH_INTERVAL_MS = 2000;

type Notice = { kind: "info" | "success" | "warning" | "error"; text: string } | null;
type RunAction = <T = unknown>(
  actionId: string,
  payload?: Record<string, unknown>,
) => Promise<BridgeResponse<T> | null>;

function NoticeBar({ notice }: { notice: Notice }) {
  if (!notice) return null;
  const Icon = notice.kind === "success" ? Check : notice.kind === "error" ? AlertCircle : Info;
  return (
    <div className={`td-notice td-notice-${notice.kind}`} role="status" aria-live="polite">
      <Icon size={16} aria-hidden="true" />
      <span>{notice.text}</span>
    </div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  description,
  titleId,
}: {
  eyebrow: string;
  title: string;
  description: string;
  titleId: string;
}) {
  return (
    <header className="td-section-title">
      <span className="td-eyebrow">{eyebrow}</span>
      <h1 id={titleId}>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function StateChip({ label, status, icon }: { label: string; status: string; icon: ReactNode }) {
  const normalized = (status ?? "").toLowerCase();
  const connected = ["authorized", "connected", "running"].includes(normalized);
  return (
    <span className={`td-chip ${connected ? "is-connected td-status-live" : ""}`}>
      <span className="td-chip-dot" aria-hidden="true" />
      {icon}
      {label}: {status || "—"}
    </span>
  );
}

function ActionButton({
  actionId,
  busyAction,
  live,
  className = "td-button td-button-secondary",
  disabled = false,
  onClick,
  children,
}: {
  actionId: string;
  busyAction: string | null;
  live: boolean;
  className?: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  const blocked = !live || disabled || busyAction !== null;
  return (
    <button
      type="button"
      className={className}
      disabled={blocked}
      data-action-id={actionId}
      title={!live ? "Backend bridge unavailable" : undefined}
      onClick={onClick}
    >
      {busyAction === actionId ? (
        <RefreshCw className="td-spin" size={15} aria-hidden="true" />
      ) : null}
      {children}
    </button>
  );
}

const navItems: Array<{ id: Page; icon: ReactNode }> = [
  { id: "connection", icon: <UserRound size={15} aria-hidden="true" /> },
  { id: "analyze", icon: <Search size={15} aria-hidden="true" /> },
  { id: "queue", icon: <UploadCloud size={15} aria-hidden="true" /> },
  { id: "logs", icon: <Terminal size={15} aria-hidden="true" /> },
  { id: "settings", icon: <Settings size={15} aria-hidden="true" /> },
];

function TopBar({
  state,
  language,
  live,
}: {
  state: LiveUiState | null;
  language: BridgeLanguage;
  live: boolean;
}) {
  return (
    <header className="td-topbar">
      <div className="td-brand">
        <span className="td-mark">TD</span>
        <strong>TeleDrive</strong>
      </div>
      <div className={`td-prototype ${live ? "td-status-live" : "td-status-demo"}`}>
        <Terminal size={13} aria-hidden="true" />
        {live ? "Gradio · Live bridge" : "Backend bridge unavailable"}
      </div>
      <div className="td-chips">
        <StateChip
          label={localize(language, "تيليجرام", "Telegram")}
          status={state?.telegram?.status ?? "—"}
          icon={<UserRound size={13} aria-hidden="true" />}
        />
        <StateChip
          label={localize(language, "درايف", "Drive")}
          status={state?.drive?.status ?? "—"}
          icon={<Cloud size={13} aria-hidden="true" />}
        />
        <span className={`td-chip ${state?.folder?.id ? "is-connected" : ""}`}>
          <span className="td-chip-dot" aria-hidden="true" />
          <Folder size={13} aria-hidden="true" />
          {localize(language, "المجلد", "Folder")}: {state?.folder?.name ?? "—"}
        </span>
        <StateChip
          label={localize(language, "المحرك", "Engine")}
          status={state?.engine ?? "—"}
          icon={<Gauge size={13} aria-hidden="true" />}
        />
      </div>
    </header>
  );
}

function ConnectionSection({
  state,
  language,
  live,
  busyAction,
  run,
}: {
  state: LiveUiState | null;
  language: BridgeLanguage;
  live: boolean;
  busyAction: string | null;
  run: RunAction;
}) {
  const [parentId, setParentId] = useState("root");
  const [folderName, setFolderName] = useState("");
  const [folderId, setFolderId] = useState("");
  const [folders, setFolders] = useState<FolderChoice[]>([]);

  const listFolders = async () => {
    const response = await run<{ folders?: FolderChoice[] }>("drive.list_folders", { parentId });
    if (response?.status === "ok") setFolders(response.data?.folders ?? []);
  };

  return (
    <section className="td-page" aria-labelledby="connection-title">
      <SectionTitle
        titleId="connection-title"
        eyebrow="CONNECTION CENTER"
        title={pageLabels.connection[language]}
        description={localize(
          language,
          "الحالة من ApplicationContext الحي. حقول Telegram السرية تبقى في لوحة Gradio الآمنة ولا تدخل React.",
          "Status comes from the live ApplicationContext. Secret Telegram fields stay in the secure Gradio panel and never enter React.",
        )}
      />
      <div className="td-split">
        <article className="td-panel">
          <div className="td-conn-head">
            <UserRound size={18} aria-hidden="true" />
            <div>
              <h2>Telegram</h2>
              <p>{state?.telegram?.status ?? "—"}</p>
              {state?.telegram?.accountLabel ? <small>{state.telegram.accountLabel}</small> : null}
            </div>
          </div>
          <div className="td-stack">
            <div className="td-bridge-blocked">
              <ShieldCheck size={16} aria-hidden="true" />
              {localize(
                language,
                "API hash ورقم الهاتف والرمز و2FA تُدخل فقط في عناصر Gradio الآمنة أسفل لوحة React.",
                "API hash, phone, code, and 2FA are entered only in the secure Gradio controls below React.",
              )}
            </div>
            <button type="button" className="td-button td-button-secondary" disabled>
              {localize(language, "استخدم لوحة مصادقة Gradio", "Use secure Gradio authentication")}
            </button>
            <div className="td-button-row">
              <ActionButton
                actionId="telegram.status"
                busyAction={busyAction}
                live={live}
                onClick={() => void run("telegram.status")}
              >
                <RefreshCw size={15} aria-hidden="true" />
                {localize(language, "تحديث الحالة", "Refresh status")}
              </ActionButton>
              <ActionButton
                actionId="telegram.logout"
                busyAction={busyAction}
                live={live}
                className="td-button td-button-danger"
                onClick={() => void run("telegram.logout")}
              >
                <LogOut size={15} aria-hidden="true" />
                {localize(language, "تسجيل الخروج", "Log out")}
              </ActionButton>
            </div>
          </div>
        </article>

        <article className="td-panel">
          <div className="td-conn-head">
            <Cloud size={18} aria-hidden="true" />
            <div>
              <h2>Google Drive</h2>
              <p>{state?.drive?.status ?? "—"}</p>
              {state?.drive?.accountLabel ? <small>{state.drive.accountLabel}</small> : null}
            </div>
          </div>
          <div className="td-stack">
            <div className="td-button-row">
              <ActionButton
                actionId="drive.connect"
                busyAction={busyAction}
                live={live}
                className="td-button td-button-primary"
                onClick={() => void run("drive.connect")}
              >
                {localize(language, "ربط Drive الأصلي", "Native Drive connect")}
              </ActionButton>
              <ActionButton
                actionId="drive.reconnect"
                busyAction={busyAction}
                live={live}
                onClick={() => void run("drive.reconnect")}
              >
                {localize(language, "إعادة الربط", "Reconnect")}
              </ActionButton>
              <ActionButton
                actionId="drive.refresh_quota"
                busyAction={busyAction}
                live={live}
                onClick={() => void run("drive.refresh_quota")}
              >
                {localize(language, "تحديث الحصة", "Refresh quota")}
              </ActionButton>
            </div>
            <div className="td-quota-line">
              <span>
                {localize(language, "الاستخدام", "Usage")}:{" "}
                {formatBytes(state?.drive?.quotaUsed ?? null)}
              </span>
              <span>
                {localize(language, "السعة", "Limit")}:{" "}
                {formatBytes(state?.drive?.quotaLimit ?? null)}
              </span>
            </div>
            <label className="td-label" htmlFor="td-parent-id">
              {localize(language, "معرّف المجلد الأب", "Parent folder ID")}
              <input
                id="td-parent-id"
                className="td-input"
                value={parentId}
                onChange={(event) => setParentId(event.target.value)}
              />
            </label>
            <ActionButton
              actionId="drive.list_folders"
              busyAction={busyAction}
              live={live}
              disabled={(state?.drive?.status?.toLowerCase?.() ?? "") !== "connected"}
              onClick={() => void listFolders()}
            >
              <RefreshCw size={15} aria-hidden="true" />
              {localize(language, "عرض المجلدات الحقيقية", "List live folders")}
            </ActionButton>
            <label className="td-label" htmlFor="td-folder-choice">
              {localize(language, "مجلد الوجهة", "Destination folder")}
              <select
                id="td-folder-choice"
                className="td-input"
                value={folderId}
                onChange={(event) => setFolderId(event.target.value)}
              >
                <option value="">—</option>
                {folders.map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name}
                  </option>
                ))}
              </select>
            </label>
            <ActionButton
              actionId="drive.select_folder"
              busyAction={busyAction}
              live={live}
              disabled={!folderId}
              onClick={() => void run("drive.select_folder", { folderId })}
            >
              <Folder size={15} aria-hidden="true" />
              {localize(language, "اختيار المجلد", "Select folder")}
            </ActionButton>
            <label className="td-label" htmlFor="td-new-folder">
              {localize(language, "اسم مجلد جديد", "New folder name")}
              <input
                id="td-new-folder"
                className="td-input"
                value={folderName}
                onChange={(event) => setFolderName(event.target.value)}
              />
            </label>
            <ActionButton
              actionId="drive.create_folder"
              busyAction={busyAction}
              live={live}
              disabled={!folderName.trim()}
              onClick={() => void run("drive.create_folder", { name: folderName, parentId })}
            >
              {localize(language, "إنشاء واختيار", "Create and select")}
            </ActionButton>
          </div>
        </article>
      </div>
    </section>
  );
}

function AnalyzeSection({
  state,
  language,
  live,
  busyAction,
  run,
  onNavigate,
}: {
  state: LiveUiState | null;
  language: BridgeLanguage;
  live: boolean;
  busyAction: string | null;
  run: RunAction;
  onNavigate(page: Page): void;
}) {
  const [sourceLink, setSourceLink] = useState("");
  const [mode, setMode] = useState<ScanMode>("message");
  const [messageId, setMessageId] = useState("");
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");
  const [limit, setLimit] = useState("100");
  const [selectionFrom, setSelectionFrom] = useState("");
  const [selectionTo, setSelectionTo] = useState("");
  const [mediaTypes, setMediaTypes] = useState<MediaType[]>(["all"]);
  const candidates = state?.candidates ?? [];
  const selected = selectedVisibleCandidates(candidates);
  const blockReason = enqueueBlockReason(state, candidates);

  const toggleMedia = (value: MediaType) => {
    if (value === "all") return setMediaTypes(["all"]);
    setMediaTypes((current) => {
      const next = current.filter((item) => item !== "all" && item !== value);
      if (!current.includes(value)) next.push(value);
      return next.length ? next : ["all"];
    });
  };

  const analyze = async () => {
    const invalid = validateAnalyzeInput({
      sourceLink,
      mode,
      messageId,
      rangeFrom,
      rangeTo,
      limit,
    });
    if (invalid) return;
    await run("analyze.run", {
      link: sourceLink,
      mode,
      messageId: messageId || null,
      startId: rangeFrom || null,
      endId: rangeTo || null,
      limit,
      mediaTypes,
    });
  };

  const blockText =
    blockReason === "bridge"
      ? "Backend bridge unavailable"
      : blockReason === "folder"
        ? localize(language, "اختر مجلد Drive حقيقيًا أولًا.", "Choose a live Drive folder first.")
        : blockReason === "selection"
          ? localize(
              language,
              "حدد ملفًا حقيقيًا واحدًا على الأقل.",
              "Select at least one live candidate.",
            )
          : localize(language, "جاهز للإضافة الصريحة إلى الطابور.", "Ready for explicit enqueue.");

  return (
    <section className="td-page" aria-labelledby="analyze-title">
      <SectionTitle
        titleId="analyze-title"
        eyebrow="ANALYZE & SELECT"
        title={pageLabels.analyze[language]}
        description={localize(
          language,
          "التحليل يحدّث المرشحين فقط؛ الإضافة للطابور إجراء مستقل.",
          "Analyze updates candidates only; enqueue is always a separate action.",
        )}
      />
      <div className="td-analysis-line td-panel">
        <label className="td-label td-grow" htmlFor="td-link">
          {localize(language, "رابط الرسالة أو القناة", "Message or channel link")}
          <input
            id="td-link"
            className="td-input"
            value={sourceLink}
            onChange={(event) => setSourceLink(event.target.value)}
            placeholder="https://t.me/channel/123"
          />
        </label>
        <label className="td-label" htmlFor="td-scan-mode">
          {localize(language, "نوع الفحص", "Scan mode")}
          <select
            id="td-scan-mode"
            className="td-input"
            value={mode}
            onChange={(event) => setMode(event.target.value as ScanMode)}
          >
            {scanModes.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label[language]}
              </option>
            ))}
          </select>
        </label>
        <ActionButton
          actionId="analyze.run"
          busyAction={busyAction}
          live={live}
          className="td-button td-button-primary td-align-end"
          onClick={() => void analyze()}
        >
          <Search size={16} aria-hidden="true" />
          {localize(language, "تحليل", "Analyze")}
        </ActionButton>
      </div>
      <div className="td-panel td-mode-panel">
        <div className="td-mode-fields">
          {mode === "message" ? (
            <label className="td-label">
              {localize(language, "رقم الرسالة", "Message ID")}
              <input
                className="td-input"
                value={messageId}
                onChange={(event) => setMessageId(event.target.value)}
              />
            </label>
          ) : null}
          {mode === "range" ? (
            <>
              <label className="td-label">
                {localize(language, "من", "From")}
                <input
                  className="td-input"
                  value={rangeFrom}
                  onChange={(event) => setRangeFrom(event.target.value)}
                />
              </label>
              <label className="td-label">
                {localize(language, "إلى", "To")}
                <input
                  className="td-input"
                  value={rangeTo}
                  onChange={(event) => setRangeTo(event.target.value)}
                />
              </label>
            </>
          ) : null}
          {mode === "latest" || mode === "chat" ? (
            <label className="td-label">
              {localize(language, "الحد الأقصى", "Limit")}
              <input
                className="td-input"
                type="number"
                min={1}
                max={1000}
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
              />
            </label>
          ) : null}
          <span className="td-hint">
            <Info size={15} aria-hidden="true" />
            {localize(
              language,
              "الفحص محدود بحد أقصى 1000 رسالة.",
              "The scan is bounded to at most 1,000 messages.",
            )}
          </span>
        </div>
        <div className="td-media-filter">
          <span className="td-label-text">{localize(language, "نوع الوسائط", "Media types")}</span>
          {mediaChoices.map((choice) => (
            <button
              type="button"
              key={choice.value}
              className={`td-filter ${mediaTypes.includes(choice.value) ? "is-selected" : ""}`}
              aria-pressed={mediaTypes.includes(choice.value)}
              onClick={() => toggleMedia(choice.value)}
            >
              {choice.label[language]}
            </button>
          ))}
        </div>
      </div>
      <div className="td-results-head">
        <div>
          <span className="td-eyebrow">LIVE CANDIDATES</span>
          <h2>
            {localize(language, "النتائج", "Results")}{" "}
            <small>
              · {candidates.length} · {selected.length}
            </small>
          </h2>
        </div>
        <div className="td-button-row">
          <ActionButton
            actionId="analyze.select_all"
            busyAction={busyAction}
            live={live}
            onClick={() => void run("analyze.select_all")}
          >
            {localize(language, "تحديد الكل الظاهر", "Select visible")}
          </ActionButton>
          <ActionButton
            actionId="analyze.clear_selection"
            busyAction={busyAction}
            live={live}
            onClick={() => void run("analyze.clear_selection")}
          >
            {localize(language, "مسح التحديد", "Clear")}
          </ActionButton>
          <ActionButton
            actionId="analyze.enqueue_selected"
            busyAction={busyAction}
            live={live}
            disabled={blockReason !== null}
            className="td-button td-button-primary"
            onClick={() =>
              void run("analyze.enqueue_selected").then((response) => {
                if (response?.status === "ok") onNavigate("queue");
              })
            }
          >
            <UploadCloud size={15} aria-hidden="true" />
            {localize(language, "إضافة للطابور", "Enqueue")}
          </ActionButton>
        </div>
      </div>
      <p className={`td-control-reason ${blockReason === null ? "is-ready" : ""}`}>{blockText}</p>
      <div className="td-selection-tools td-panel">
        <label className="td-label">
          {localize(language, "تحديد من رسالة", "Select from message")}
          <input
            className="td-input"
            value={selectionFrom}
            onChange={(event) => setSelectionFrom(event.target.value)}
          />
        </label>
        <label className="td-label">
          {localize(language, "إلى رسالة", "To message")}
          <input
            className="td-input"
            value={selectionTo}
            onChange={(event) => setSelectionTo(event.target.value)}
          />
        </label>
        <ActionButton
          actionId="analyze.select_range"
          busyAction={busyAction}
          live={live}
          disabled={!selectionFrom || !selectionTo}
          onClick={() =>
            void run("analyze.select_range", { startId: selectionFrom, endId: selectionTo })
          }
        >
          {localize(language, "تحديد النطاق", "Select range")}
        </ActionButton>
      </div>
      {!candidates.length ? (
        <div className="td-empty-state">
          {localize(language, "لا توجد مرشحات حية بعد.", "No live candidates yet.")}
        </div>
      ) : null}
      {candidates.length ? (
        <div className="td-table-wrap">
          <table className="td-table">
            <thead>
              <tr>
                <th>{localize(language, "اختيار", "Select")}</th>
                <th>{localize(language, "الملف", "File")}</th>
                <th>{localize(language, "النوع", "Type")}</th>
                <th>{localize(language, "الحجم", "Size")}</th>
                <th>{localize(language, "المجموعة", "Group")}</th>
                <th>{localize(language, "الحالة", "Status")}</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => {
                const selectable = selectableCandidates([candidate]).length === 1;
                return (
                  <tr key={candidate.sourceId}>
                    <td data-label="Select">
                      <ActionButton
                        actionId="analyze.toggle_row"
                        busyAction={busyAction}
                        live={live}
                        disabled={!selectable}
                        className="td-link-button"
                        onClick={() =>
                          void run("analyze.toggle_row", { sourceId: candidate.sourceId })
                        }
                      >
                        {candidate.selected ? "☑" : "☐"}
                      </ActionButton>
                    </td>
                    <td data-label="File">
                      <strong>{candidate.name}</strong>
                      <small>{candidate.dateLabel ?? "—"}</small>
                    </td>
                    <td data-label="Type">{candidate.mediaType}</td>
                    <td className="td-number" data-label="Size">
                      {formatBytes(candidate.sizeBytes)}
                    </td>
                    <td data-label="Group">{candidate.groupLabel ?? "—"}</td>
                    <td data-label="Status">
                      <span
                        className={`td-status td-status-${(candidate.status ?? "").toLowerCase()}`}
                      >
                        {candidate.status ?? "—"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function QueueSection({
  state,
  language,
  live,
  busyAction,
  run,
}: {
  state: LiveUiState | null;
  language: BridgeLanguage;
  live: boolean;
  busyAction: string | null;
  run: RunAction;
}) {
  const [stopConfirm, setStopConfirm] = useState(false);
  const rows = state?.queue ?? [];
  const metrics = queueMetrics(rows);
  const sessions = groupQueueSessions(rows);
  const stopOnly = () => {
    setStopConfirm(false);
    void run("queue.stop");
  };
  const stopAndClear = async () => {
    setStopConfirm(false);
    await run("queue.stop");
    await run("queue.clear_incomplete");
  };
  return (
    <section className="td-page" aria-labelledby="queue-title">
      <SectionTitle
        titleId="queue-title"
        eyebrow="LIVE TRANSFERS"
        title={pageLabels.queue[language]}
        description={localize(
          language,
          "كل الأرقام والصفوف مشتقة من queue وSQLite الحيين.",
          "Every count and row is derived from the live queue and SQLite state.",
        )}
      />
      <div className="td-metrics">
        <div>
          <span>{localize(language, "في الانتظار", "Queued")}</span>
          <strong>{metrics.queued}</strong>
        </div>
        <div>
          <span>{localize(language, "قيد التنفيذ", "Running")}</span>
          <strong>
            {metrics.running}
            <small> / {state?.concurrency ?? "—"}</small>
          </strong>
        </div>
        <div>
          <span>{localize(language, "مكتمل", "Completed")}</span>
          <strong>{metrics.uploaded}</strong>
        </div>
        <div>
          <span>{localize(language, "فشل", "Failed")}</span>
          <strong>{metrics.failed}</strong>
        </div>
        <div>
          <span>{localize(language, "المنقول", "Transferred")}</span>
          <strong>{formatBytes(metrics.transferredBytes)}</strong>
        </div>
      </div>
      <div className="td-button-row td-transfer-actions">
        <ActionButton
          actionId="queue.start_selected"
          busyAction={busyAction}
          live={live}
          className="td-button td-button-primary"
          onClick={() => void run("queue.start_selected")}
        >
          <Play size={15} aria-hidden="true" />
          {localize(language, "بدء", "Start")}
        </ActionButton>
        <ActionButton
          actionId="queue.pause"
          busyAction={busyAction}
          live={live}
          onClick={() => void run("queue.pause")}
        >
          <Pause size={15} aria-hidden="true" />
          {localize(language, "إيقاف مؤقت", "Pause")}
        </ActionButton>
        <ActionButton
          actionId="queue.resume"
          busyAction={busyAction}
          live={live}
          onClick={() => void run("queue.resume")}
        >
          <RefreshCw size={15} aria-hidden="true" />
          {localize(language, "استئناف", "Resume")}
        </ActionButton>
        <ActionButton
          actionId="queue.stop"
          busyAction={busyAction}
          live={live}
          className="td-button td-button-danger"
          onClick={() => setStopConfirm(true)}
        >
          <Square size={15} aria-hidden="true" />
          {localize(language, "إيقاف", "Stop")}
        </ActionButton>
        <ActionButton
          actionId="queue.retry_failed"
          busyAction={busyAction}
          live={live}
          onClick={() => void run("queue.retry_failed")}
        >
          <RotateCcw size={15} aria-hidden="true" />
          {localize(language, "إعادة الفاشلة", "Retry failed")}
        </ActionButton>
        <ActionButton
          actionId="queue.clear_completed"
          busyAction={busyAction}
          live={live}
          onClick={() => void run("queue.clear_completed")}
        >
          {localize(language, "مسح المكتملة", "Clear completed")}
        </ActionButton>
        <ActionButton
          actionId="queue.clear_incomplete"
          busyAction={busyAction}
          live={live}
          className="td-button td-button-danger"
          onClick={() => void run("queue.clear_incomplete")}
        >
          {localize(language, "مسح غير المكتمل", "Clear incomplete")}
        </ActionButton>
        <ActionButton
          actionId="queue.refresh"
          busyAction={busyAction}
          live={live}
          onClick={() => void run("queue.refresh")}
        >
          <RefreshCw size={15} aria-hidden="true" />
          {localize(language, "تحديث", "Refresh")}
        </ActionButton>
      </div>
      {stopConfirm ? (
        <div className="td-confirm" role="dialog" aria-labelledby="td-stop-title">
          <p id="td-stop-title">
            {localize(
              language,
              "إيقاف العمال فقط، أم إيقاف ومسح الصفوف غير المكتملة من الطابور؟ ملفات Drive المرفوعة لا تُحذف أبدًا.",
              "Stop the workers only, or also clear unfinished queue rows? Uploaded Drive files are never deleted.",
            )}
          </p>
          <div className="td-button-row">
            <ActionButton
              actionId="queue.stop"
              busyAction={busyAction}
              live={live}
              onClick={stopOnly}
            >
              {localize(language, "إيقاف فقط", "Stop only")}
            </ActionButton>
            <ActionButton
              actionId="queue.clear_incomplete"
              busyAction={busyAction}
              live={live}
              className="td-button td-button-danger"
              onClick={() => void stopAndClear()}
            >
              {localize(language, "إيقاف ومسح غير المكتمل", "Stop and clear incomplete")}
            </ActionButton>
            <button
              type="button"
              className="td-button td-button-secondary"
              onClick={() => setStopConfirm(false)}
            >
              {localize(language, "إلغاء", "Cancel")}
            </button>
          </div>
        </div>
      ) : null}
      <div className="td-destination-banner">
        <Folder size={15} aria-hidden="true" />
        {localize(language, "مجلد الوجهة", "Destination")}:{" "}
        <strong>{state?.folder?.name ?? "—"}</strong>
      </div>
      {!rows.length ? (
        <div className="td-empty-state">
          {localize(language, "الطابور الحي فارغ.", "The live queue is empty.")}
        </div>
      ) : (
        <div className="td-session-list">
          {sessions.map((session) => (
            <details key={session.key} className="td-session" open>
              <summary className="td-session-head">
                <Folder size={16} aria-hidden="true" />
                <strong>
                  {session.title} · {session.dateLabel}
                </strong>
                <small>
                  {session.rows.length} {localize(language, "ملف", "files")} ·{" "}
                  {localize(language, "مكتمل", "uploaded")} {session.uploaded} ·{" "}
                  {localize(language, "انتظار", "pending")} {session.pending}
                </small>
              </summary>
              <div className="td-table-wrap">
                <table className="td-table">
                  <thead>
                    <tr>
                      <th>{localize(language, "الملف", "File")}</th>
                      <th>{localize(language, "الحالة", "Status")}</th>
                      <th>{localize(language, "التقدم", "Progress")}</th>
                      <th>{localize(language, "الحجم", "Size")}</th>
                      <th>{localize(language, "تحكم", "Controls")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {session.rows.map((row) => (
                      <tr key={row.id}>
                        <td data-label="File">
                          <strong>{row.name}</strong>
                          <small>{row.id}</small>
                        </td>
                        <td data-label="Status">
                          <span
                            className={`td-status td-status-${(row.status ?? "").toLowerCase()}`}
                          >
                            {row.status ?? "—"}
                          </span>
                        </td>
                        <td data-label="Progress">
                          <div className="td-progress">
                            <span
                              style={{
                                width: `${Math.max(0, Math.min(100, Number(row.progress) || 0))}%`,
                              }}
                            />
                          </div>
                          <small>{(Number(row.progress) || 0).toFixed(0)}%</small>
                        </td>
                        <td data-label="Size">{formatBytes(row.sizeBytes)}</td>
                        <td data-label="Controls">
                          <div className="td-button-row">
                            <ActionButton
                              actionId="queue.pause_item"
                              busyAction={busyAction}
                              live={live}
                              className="td-link-button"
                              onClick={() => void run("queue.pause_item", { itemId: row.id })}
                            >
                              {localize(language, "إيقاف", "Pause")}
                            </ActionButton>
                            <ActionButton
                              actionId="queue.resume_item"
                              busyAction={busyAction}
                              live={live}
                              className="td-link-button"
                              onClick={() => void run("queue.resume_item", { itemId: row.id })}
                            >
                              {localize(language, "استئناف", "Resume")}
                            </ActionButton>
                            <ActionButton
                              actionId="queue.retry_item"
                              busyAction={busyAction}
                              live={live}
                              className="td-link-button"
                              onClick={() => void run("queue.retry_item", { itemId: row.id })}
                            >
                              {localize(language, "إعادة", "Retry")}
                            </ActionButton>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}

function LogsSection({
  language,
  live,
  busyAction,
  run,
}: {
  language: BridgeLanguage;
  live: boolean;
  busyAction: string | null;
  run: RunAction;
}) {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("ALL");
  const [logs, setLogs] = useState("");
  const load = async (actionId: "logs.refresh" | "logs.search") => {
    const response = await run<{ logs?: string }>(actionId, { query, level });
    if (response?.status === "ok") setLogs(response.data?.logs ?? "");
  };
  return (
    <section className="td-page" aria-labelledby="logs-title">
      <SectionTitle
        titleId="logs-title"
        eyebrow="REDACTED AUDIT TRAIL"
        title={pageLabels.logs[language]}
        description={localize(
          language,
          "المحتوى يأتي من LogService ويمر بالتنقيح قبل المتصفح.",
          "Content comes from LogService and is redacted before reaching the browser.",
        )}
      />
      <div className="td-log-toolbar">
        <label className="td-label td-grow">
          {localize(language, "بحث", "Search")}
          <input
            className="td-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label className="td-label">
          {localize(language, "المستوى", "Level")}
          <select
            className="td-input"
            value={level}
            onChange={(event) => setLevel(event.target.value)}
          >
            {["ALL", "INFO", "WARNING", "ERROR", "RECOVERY"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <ActionButton
          actionId="logs.search"
          busyAction={busyAction}
          live={live}
          onClick={() => void load("logs.search")}
        >
          <Search size={15} aria-hidden="true" />
          {localize(language, "بحث", "Search")}
        </ActionButton>
        <ActionButton
          actionId="logs.refresh"
          busyAction={busyAction}
          live={live}
          onClick={() => void load("logs.refresh")}
        >
          <RefreshCw size={15} aria-hidden="true" />
          {localize(language, "تحديث", "Refresh")}
        </ActionButton>
      </div>
      <div className="td-log-box">
        {logs ? (
          logs.split("\n").map((line, index) => <code key={`${index}-${line}`}>{line}</code>)
        ) : (
          <div className="td-empty-state">
            {localize(language, "لا توجد سجلات حية معروضة.", "No live logs displayed.")}
          </div>
        )}
      </div>
      <div className="td-inline-note">
        <ShieldCheck size={15} aria-hidden="true" />
        {localize(
          language,
          "لا يُعرض payload الخام أو المسار المحلي أو بيانات الاعتماد.",
          "Raw payloads, local paths, and credentials are never displayed.",
        )}
      </div>
    </section>
  );
}

function SettingsSection({
  state,
  language,
  live,
  busyAction,
  run,
}: {
  state: LiveUiState | null;
  language: BridgeLanguage;
  live: boolean;
  busyAction: string | null;
  run: RunAction;
}) {
  const [concurrency, setConcurrency] = useState(state?.concurrency ?? 2);
  useEffect(() => {
    if (state?.concurrency != null) setConcurrency(state.concurrency);
  }, [state]);
  return (
    <section className="td-page" aria-labelledby="settings-title">
      <SectionTitle
        titleId="settings-title"
        eyebrow="LIVE PREFERENCES"
        title={pageLabels.settings[language]}
        description={localize(
          language,
          "الإعدادات تُكتب عبر الخدمات الحالية؛ لا تخزين متصفح ولا حالة نجاح محلية.",
          "Settings are written through existing services; there is no browser storage or optimistic success state.",
        )}
      />
      <div className="td-panel">
        <div className="td-setting-row">
          <div>
            <h2>{localize(language, "التحويلات المتزامنة", "Concurrent transfers")}</h2>
            <p>
              {localize(
                language,
                "النطاق الدستوري 1–100، الافتراضي 2، وتحذير فوق 8.",
                "Constitutional range 1–100, default 2, with a warning above 8.",
              )}
            </p>
          </div>
          <div className="td-setting-control">
            <strong className="td-big-number">{concurrency}</strong>
            <input
              type="range"
              min={1}
              max={100}
              value={concurrency}
              onChange={(event) => setConcurrency(Number(event.target.value))}
            />
            <ActionButton
              actionId="settings.set_concurrency"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("settings.set_concurrency", { value: concurrency })}
            >
              {localize(language, "حفظ في Python", "Save in Python")}
            </ActionButton>
            {concurrency > 8 ? (
              <p className="td-warn-line">
                {localize(
                  language,
                  "تحذير: هذه القيمة غير مثبتة على ذاكرة Colab الحية.",
                  "Warning: this value is not proven against live Colab memory.",
                )}
              </p>
            ) : null}
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(language, "اللغة", "Language")}</h2>
            <p>Arabic RTL · English LTR</p>
          </div>
          <div className="td-segment">
            <ActionButton
              actionId="settings.toggle_language"
              busyAction={busyAction}
              live={live}
              className="td-link-button"
              onClick={() => void run("settings.toggle_language")}
            >
              {language === "ar" ? "English" : "العربية"}
            </ActionButton>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(language, "المظهر", "Theme")}</h2>
            <p>
              {localize(
                language,
                "M20 يفرض الوضع النهاري؛ الداكن غير متاح.",
                "M20 enforces light mode; dark mode is unavailable.",
              )}
            </p>
          </div>
          <div className="td-button-row">
            <ActionButton
              actionId="settings.set_theme"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("settings.set_theme", { theme: "light" })}
            >
              {localize(language, "تطبيق النهاري", "Apply light")}
            </ActionButton>
            <button type="button" className="td-button td-button-secondary" disabled>
              {localize(language, "الداكن محظور", "Dark is blocked")}
            </button>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(language, "الاستعادة ونقاط الحفظ", "Recovery & checkpoints")}</h2>
          </div>
          <div className="td-button-row">
            <ActionButton
              actionId="recovery.restore"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("recovery.restore")}
            >
              <RotateCcw size={15} aria-hidden="true" />
              {localize(language, "استعادة", "Restore")}
            </ActionButton>
            <ActionButton
              actionId="maintenance.checkpoint"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("maintenance.checkpoint")}
            >
              <Check size={15} aria-hidden="true" />
              {localize(language, "حفظ نقطة", "Checkpoint")}
            </ActionButton>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(language, "التصدير", "Export")}</h2>
          </div>
          <div className="td-button-row">
            <ActionButton
              actionId="export.build_zip"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("export.build_zip")}
            >
              <FileArchive size={15} aria-hidden="true" />
              ZIP
            </ActionButton>
            <ActionButton
              actionId="export.colab_cells"
              busyAction={busyAction}
              live={live}
              onClick={() => void run("export.colab_cells")}
            >
              <FileText size={15} aria-hidden="true" />
              Colab
            </ActionButton>
          </div>
        </div>
      </div>
    </section>
  );
}

export type TeleDriveSandboxProps = { bridge?: TeleDriveBridge };

export default function TeleDriveSandbox({ bridge = unavailableBridge }: TeleDriveSandboxProps) {
  const [liveState, setLiveState] = useState<LiveUiState | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [page, setPage] = useState<Page>("connection");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  /** Latest in-flight requestId per actionId — drops stale responses that would clobber newer state/notices. */
  const latestRequest = useRef(new Map<string, string>());
  const live = bridge.isLive();
  const language = liveState?.language ?? "ar";

  useEffect(() => bridge.subscribe(setLiveState), [bridge]);

  // Quiet auto-refresh: while a transfer is moving, poll the live snapshot so
  // every panel (chips, folder, queue, candidates) follows Python on its own —
  // exactly like pressing Refresh, but without flashing notices or busy states.
  const liveStateRef = useRef<LiveUiState | null>(null);
  const pollInFlight = useRef(false);
  useEffect(() => {
    liveStateRef.current = liveState;
  }, [liveState]);

  useEffect(() => {
    if (!live) return;
    const interval = setInterval(() => {
      const snapshot = liveStateRef.current;
      if (!snapshot || !hasActiveTransfer(snapshot)) return;
      if (pollInFlight.current) return;
      pollInFlight.current = true;
      void bridge
        .request({
          requestId: newRequestId(),
          actionId: "queue.refresh",
          payload: {},
          language: snapshot.language,
        })
        .then((response) => {
          if (response.state) setLiveState(response.state);
        })
        .catch(() => {
          // Silent heartbeat: a transient bridge failure must not surface as a
          // user-facing notice or block the next tick.
        })
        .finally(() => {
          pollInFlight.current = false;
        });
    }, AUTO_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [bridge, live]);

  const run: RunAction = async <T,>(actionId: string, payload: Record<string, unknown> = {}) => {
    if (!bridge.isLive()) {
      setNotice({ kind: "warning", text: "Backend bridge unavailable" });
      return null;
    }
    const requestId = newRequestId();
    latestRequest.current.set(actionId, requestId);
    setBusyAction(actionId);
    try {
      const response = await bridge.request<T>({
        requestId,
        actionId,
        payload,
        language,
      });
      // Stale response: a newer request for the same action already owns the UI.
      if (latestRequest.current.get(actionId) !== requestId) return null;
      if (response.state) setLiveState(response.state);
      if (response.status !== "ok") {
        setNotice({
          kind: response.status === "blocked" ? "warning" : "error",
          text:
            response.message ??
            response.errorKey ??
            localize(language, "فشل الإجراء.", "Action failed."),
        });
        return response;
      }
      setNotice({
        kind: "success",
        text:
          response.message ??
          localize(language, "تم تنفيذ الإجراء عبر Python.", "Action completed through Python."),
      });
      return response;
    } catch (error) {
      if (latestRequest.current.get(actionId) !== requestId) return null;
      setNotice({
        kind: "error",
        text:
          error instanceof Error
            ? error.message
            : localize(language, "فشل bridge.", "Bridge failed."),
      });
      return null;
    } finally {
      if (latestRequest.current.get(actionId) === requestId) {
        setBusyAction(null);
      }
    }
  };

  const pages: Record<Page, ReactNode> = {
    connection: (
      <ConnectionSection
        state={liveState}
        language={language}
        live={live}
        busyAction={busyAction}
        run={run}
      />
    ),
    analyze: (
      <AnalyzeSection
        state={liveState}
        language={language}
        live={live}
        busyAction={busyAction}
        run={run}
        onNavigate={setPage}
      />
    ),
    queue: (
      <QueueSection
        state={liveState}
        language={language}
        live={live}
        busyAction={busyAction}
        run={run}
      />
    ),
    logs: <LogsSection language={language} live={live} busyAction={busyAction} run={run} />,
    settings: (
      <SettingsSection
        state={liveState}
        language={language}
        live={live}
        busyAction={busyAction}
        run={run}
      />
    ),
  };

  return (
    <div
      className="td-app"
      lang={language}
      dir={language === "ar" ? "rtl" : "ltr"}
      data-theme="light"
    >
      <TopBar state={liveState} language={language} live={live} />
      <nav
        className="td-nav"
        aria-label={localize(language, "أقسام TeleDrive", "TeleDrive sections")}
      >
        {navItems.map((item) => (
          <button
            type="button"
            key={item.id}
            className={`td-nav-button ${page === item.id ? "is-active" : ""}`}
            aria-current={page === item.id ? "page" : undefined}
            onClick={() => setPage(item.id)}
          >
            {item.icon}
            {pageLabels[item.id][language]}
          </button>
        ))}
      </nav>
      <main className="td-main">
        {!live || !liveState ? (
          <div className="td-bridge-blocked" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            <strong>Backend bridge unavailable</strong>
            <span>
              {localize(
                language,
                "الأفعال الحساسة معطّلة، ولا تُعرض أي حالة نجاح متفائلة.",
                "Sensitive actions are disabled and no optimistic success state is shown.",
              )}
            </span>
          </div>
        ) : (
          <div className="td-demo-banner td-status-live">
            <ShieldCheck size={15} aria-hidden="true" />
            <strong>
              {localize(language, "متصل بـApplicationContext", "Connected to ApplicationContext")}
            </strong>
            <span>
              {localize(
                language,
                "كل حالة ونتيجة أدناه من Python الحي.",
                "Every state and result below comes from live Python.",
              )}
            </span>
          </div>
        )}
        <NoticeBar notice={notice} />
        {pages[page]}
      </main>
    </div>
  );
}
