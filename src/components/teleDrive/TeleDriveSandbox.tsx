/* eslint-disable */
import { useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import {
  AlertCircle,
  Check,
  CircleHelp,
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
  DEMO_FOLDERS,
  initialState,
  mediaChoices,
  modeLabel,
  modes,
  pageLabels,
  scanHint,
  statusLabel,
  typeLabel,
  type MediaType,
  type MockFile,
  type Notice,
  type Page,
  type SandboxState,
  type ScanMode,
} from "./mockState";

type SetSandbox = Dispatch<SetStateAction<SandboxState>>;

function setNotice(setState: SetSandbox, notice: Notice) {
  setState((current) => ({ ...current, notice }));
}

function NoticeBar({ notice }: { notice: Notice }) {
  if (!notice) return null;
  const Icon =
    notice.kind === "success"
      ? Check
      : notice.kind === "error"
        ? AlertCircle
        : notice.kind === "warning"
          ? CircleHelp
          : Info;
  return (
    <div className={`td-notice td-notice-${notice.kind}`} role="status">
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
  titleId?: string;
}) {
  return (
    <header className="td-section-title">
      <span className="td-eyebrow">{eyebrow}</span>
      <h1 id={titleId}>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function StatusChip({
  label,
  connected,
  icon,
}: {
  label: string;
  connected: boolean;
  icon: ReactNode;
}) {
  return (
    <span className={`td-chip ${connected ? "is-connected" : ""}`}>
      <span className="td-chip-dot" aria-hidden="true" />
      {icon}
      {label}: {connected ? "متصل" : "غير متصل"}
    </span>
  );
}

function TopBar({ state }: { state: SandboxState }) {
  return (
    <header className="td-topbar">
      <div className="td-brand">
        <span className="td-mark">TD</span>
        <strong>TeleDrive</strong>
        <small>v4.5.0</small>
      </div>
      <div className="td-prototype">
        <Terminal size={13} aria-hidden="true" />
        Prototype · Local demo
      </div>
      <div className="td-chips">
        <StatusChip
          label="تيليجرام"
          connected={state.telegramConnected}
          icon={<UserRound size={13} aria-hidden="true" />}
        />
        <StatusChip
          label="درايف"
          connected={state.driveConnected}
          icon={<Cloud size={13} aria-hidden="true" />}
        />
        <span className={`td-chip ${state.folder ? "is-connected" : ""}`}>
          <span className="td-chip-dot" aria-hidden="true" />
          <Folder size={13} aria-hidden="true" />
          المجلد: {state.folder ?? "غير محدد"}
        </span>
        <span className="td-chip">
          <span className="td-chip-dot" aria-hidden="true" />
          المحرك: محاكاة
        </span>
      </div>
    </header>
  );
}

const navItems: Array<{ id: Page; label: string; icon: ReactNode }> = [
  {
    id: "connection",
    label: pageLabels.connection,
    icon: <UserRound size={15} aria-hidden="true" />,
  },
  { id: "analyze", label: pageLabels.analyze, icon: <Search size={15} aria-hidden="true" /> },
  { id: "queue", label: pageLabels.queue, icon: <UploadCloud size={15} aria-hidden="true" /> },
  { id: "logs", label: pageLabels.logs, icon: <Terminal size={15} aria-hidden="true" /> },
  { id: "settings", label: pageLabels.settings, icon: <Settings size={15} aria-hidden="true" /> },
];

function SectionNav({ page, onNavigate }: { page: Page; onNavigate: (page: Page) => void }) {
  return (
    <nav className="td-nav" aria-label="أقسام TeleDrive">
      {navItems.map((item) => (
        <button
          type="button"
          key={item.id}
          className={`td-nav-button ${page === item.id ? "is-active" : ""}`}
          aria-current={page === item.id ? "page" : undefined}
          onClick={() => onNavigate(item.id)}
        >
          {item.icon}
          {item.label}
        </button>
      ))}
    </nav>
  );
}

function ConnectionSection({ state, setState }: { state: SandboxState; setState: SetSandbox }) {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [codeVisible, setCodeVisible] = useState(false);

  const sendCode = () => {
    setCodeVisible(true);
    setNotice(setState, {
      kind: "info",
      text: "محاكاة: تم إظهار خطوة الرمز. لم يُرسل أي رمز حقيقي.",
    });
  };

  const verifyCode = () => {
    setState((current) => ({
      ...current,
      telegramConnected: true,
      notice: {
        kind: "success",
        text: "محاكاة: تغيّرت شريحة تيليجرام إلى متصل. لا يوجد جلسة حقيقية.",
      },
    }));
  };

  const logout = () => {
    setCodeVisible(false);
    setCode("");
    setState((current) => ({
      ...current,
      telegramConnected: false,
      notice: { kind: "info", text: "محاكاة: أُعيد تيليجرام إلى غير متصل." },
    }));
  };

  const connectDrive = () => {
    setState((current) => ({
      ...current,
      driveConnected: true,
      notice: { kind: "success", text: "محاكاة: تغيّرت شريحة درايف إلى متصل. لا يوجد OAuth." },
    }));
  };

  const selectFolder = (folder: string) => {
    if (!state.driveConnected) {
      setNotice(setState, { kind: "warning", text: "اربط Drive تجريبيًا قبل اختيار المجلد." });
      return;
    }
    setState((current) => ({
      ...current,
      folder,
      notice: { kind: "success", text: `محاكاة: تم اختيار المجلد ${folder}.` },
    }));
  };

  return (
    <section className="td-page" aria-labelledby="connection-title">
      <SectionTitle
        titleId="connection-title"
        eyebrow="CONNECTION CENTER"
        title="مركز الاتصال"
        description="تيليجرام على اليمين ودرايف على اليسار. كل زر هنا يغيّر الحالة المحلية فقط ولا يفتح أي اتصال."
      />
      <div className="td-split">
        <article className="td-panel">
          <div className="td-conn-head">
            <UserRound size={18} aria-hidden="true" />
            <div>
              <h2>تيليجرام</h2>
              <p>
                {state.telegramConnected ? "حالة الشريحة: متصل (تجريبي)" : "حالة الشريحة: غير متصل"}
              </p>
            </div>
          </div>
          <div className="td-stack">
            <label className="td-label" htmlFor="td-phone">
              رقم الهاتف
              <input
                id="td-phone"
                className="td-input"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="+9665xxxxxxxx"
                autoComplete="off"
              />
            </label>
            <div className="td-button-row">
              <button type="button" className="td-button td-button-primary" onClick={sendCode}>
                إرسال الرمز
              </button>
              <button type="button" className="td-button td-button-secondary" onClick={sendCode}>
                إعادة الإرسال
              </button>
            </div>
            {codeVisible ? (
              <div className="td-otp-panel">
                <label className="td-label" htmlFor="td-code">
                  رمز التحقق
                  <input
                    id="td-code"
                    className="td-input"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    placeholder="12345"
                    autoComplete="one-time-code"
                  />
                </label>
                <button type="button" className="td-button td-button-primary" onClick={verifyCode}>
                  تأكيد الرمز
                </button>
              </div>
            ) : null}
            <div className="td-button-row">
              <button type="button" className="td-button td-button-danger" onClick={logout}>
                <LogOut size={15} aria-hidden="true" />
                تسجيل الخروج
              </button>
            </div>
          </div>
        </article>
        <article className="td-panel">
          <div className="td-conn-head">
            <Cloud size={18} aria-hidden="true" />
            <div>
              <h2>Google Drive</h2>
              <p>
                {state.driveConnected ? "حالة الشريحة: متصل (تجريبي)" : "حالة الشريحة: غير متصل"}
              </p>
            </div>
          </div>
          <div className="td-stack">
            <div className="td-button-row">
              <button type="button" className="td-button td-button-primary" onClick={connectDrive}>
                ربط Drive
              </button>
              <button
                type="button"
                className="td-button td-button-secondary"
                onClick={connectDrive}
              >
                إعادة الربط
              </button>
            </div>
            <div>
              <span className="td-label-text">مجلد الوجهة التجريبي</span>
              <div className="td-folder-list" role="list">
                {DEMO_FOLDERS.map((folder) => (
                  <button
                    type="button"
                    key={folder}
                    className={`td-folder-option ${state.folder === folder ? "is-selected" : ""}`}
                    onClick={() => selectFolder(folder)}
                    disabled={!state.driveConnected}
                  >
                    <span>
                      <Folder size={15} aria-hidden="true" /> {folder}
                    </span>
                    {state.folder === folder ? <Check size={15} aria-hidden="true" /> : null}
                  </button>
                ))}
              </div>
            </div>
            <p className="td-hint">
              <Info size={15} aria-hidden="true" />
              الحصة المعروضة للتجربة فقط: 42.7٪ · تبقّى 57.3 GB
            </p>
          </div>
        </article>
      </div>
      <NoticeBar notice={state.notice} />
    </section>
  );
}

function AnalyzeSection({
  state,
  setState,
  onNavigate,
}: {
  state: SandboxState;
  setState: SetSandbox;
  onNavigate: (page: Page) => void;
}) {
  const filteredFiles = state.files.filter(
    (file) => state.mediaTypes.includes("all") || state.mediaTypes.includes(file.type),
  );
  const selectedCount = filteredFiles.filter(
    (file) => file.selected && file.status !== "quarantined",
  ).length;
  const canEnqueue = selectedCount > 0 && Boolean(state.folder);

  const setMode = (scanMode: ScanMode) => {
    setState((current) => ({ ...current, scanMode }));
  };

  const toggleMedia = (value: MediaType) => {
    setState((current) => {
      if (value === "all") return { ...current, mediaTypes: ["all"] };
      const withoutAll = current.mediaTypes.filter((item) => item !== "all" && item !== value);
      if (!current.mediaTypes.includes(value)) withoutAll.push(value);
      return { ...current, mediaTypes: withoutAll.length ? withoutAll : ["all"] };
    });
  };

  const toggleFile = (id: string) => {
    setState((current) => ({
      ...current,
      files: current.files.map((file) =>
        file.id === id ? { ...file, selected: !file.selected } : file,
      ),
    }));
  };

  const selectAll = () => {
    setState((current) => ({
      ...current,
      files: current.files.map((file) =>
        file.status === "quarantined" ? file : { ...file, selected: true },
      ),
    }));
  };

  const clearSelection = () => {
    setState((current) => ({
      ...current,
      files: current.files.map((file) => ({ ...file, selected: false })),
    }));
  };

  const analyze = () => {
    if (!state.scanMode) {
      setNotice(setState, { kind: "error", text: "اختر نوع فحص صريحًا قبل التحليل." });
      return;
    }
    if ((state.scanMode === "message" || state.scanMode === "group") && !state.messageId.trim()) {
      setNotice(setState, { kind: "error", text: "أدخل رقم الرسالة قبل التحليل." });
      return;
    }
    if (state.scanMode === "range") {
      const from = Number(state.rangeFrom);
      const to = Number(state.rangeTo);
      if (!from || !to || from < 1 || to < 1 || to < from || to - from + 1 > 1000) {
        setNotice(setState, {
          kind: "error",
          text: "النطاق غير صالح، يجب أن يكون من 1 إلى 1000 رسالة.",
        });
        return;
      }
    }
    if (state.scanMode === "latest") {
      const limit = Number(state.latestLimit);
      if (!state.latestLimit || limit < 1 || limit > 1000) {
        setNotice(setState, { kind: "error", text: "عدد الرسائل يجب أن يكون بين 1 و1000." });
        return;
      }
    }
    setState((current) => ({
      ...current,
      analyzed: true,
      notice: {
        kind: "success",
        text: `محاكاة: ظهرت نتائج التحليل بنمط «${modeLabel(current.scanMode)}»، لم تتم إضافة أي ملف للطابور.`,
      },
    }));
  };

  const enqueue = () => {
    if (!state.folder) {
      setNotice(setState, {
        kind: "warning",
        text: "اختر مجلد Drive الوجهة قبل إضافة الملفات للطابور.",
      });
      return;
    }
    const chosen = state.files.filter((file) => file.selected && file.status !== "quarantined");
    if (!chosen.length) {
      setNotice(setState, {
        kind: "warning",
        text: "حدد ملفًا واحدًا على الأقل قبل الإضافة للطابور.",
      });
      return;
    }
    setState((current) => ({
      ...current,
      queue: chosen.map((file) => ({ ...file, status: "queued" as const })),
      files: current.files.map((file) =>
        chosen.some((item) => item.id === file.id) ? { ...file, status: "queued" as const } : file,
      ),
      notice: {
        kind: "success",
        text: `محاكاة: تمت إضافة ${chosen.length} ملفات إلى الطابور.`,
      },
    }));
    onNavigate("queue");
  };

  return (
    <section className="td-page" aria-labelledby="analyze-title">
      <SectionTitle
        titleId="analyze-title"
        eyebrow="ANALYZE & SELECT"
        title="التحليل والاختيار"
        description="اختر نطاق الفحص ونوع الوسائط، ثم راجع الملفات وحدد ما تريد نقله قبل إضافته إلى القائمة."
      />
      <div className="td-analysis-line td-panel">
        <label className="td-label td-grow" htmlFor="td-link">
          رابط الرسالة أو القناة
          <input
            id="td-link"
            className="td-input"
            placeholder="https://t.me/channel/123"
            autoComplete="off"
          />
        </label>
        <label className="td-label" htmlFor="td-scan-mode">
          نوع الفحص
          <select
            id="td-scan-mode"
            className="td-input"
            value={state.scanMode}
            onChange={(event) => setMode(event.target.value as ScanMode)}
          >
            {modes.map((mode) => (
              <option value={mode.value} key={mode.value}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="td-button td-button-primary td-align-end"
          onClick={analyze}
        >
          <Search size={16} aria-hidden="true" />
          تحليل
        </button>
      </div>
      <div className="td-panel td-mode-panel">
        <div className="td-mode-fields">
          {state.scanMode === "message" || state.scanMode === "group" ? (
            <label className="td-label" htmlFor="td-message-id">
              رقم الرسالة
              <input
                id="td-message-id"
                className="td-input"
                value={state.messageId}
                onChange={(event) =>
                  setState((current) => ({ ...current, messageId: event.target.value }))
                }
              />
            </label>
          ) : null}
          {state.scanMode === "range" ? (
            <>
              <label className="td-label" htmlFor="td-range-from">
                من رسالة
                <input
                  id="td-range-from"
                  className="td-input"
                  value={state.rangeFrom}
                  onChange={(event) =>
                    setState((current) => ({ ...current, rangeFrom: event.target.value }))
                  }
                />
              </label>
              <label className="td-label" htmlFor="td-range-to">
                إلى رسالة
                <input
                  id="td-range-to"
                  className="td-input"
                  value={state.rangeTo}
                  onChange={(event) =>
                    setState((current) => ({ ...current, rangeTo: event.target.value }))
                  }
                />
              </label>
            </>
          ) : null}
          {state.scanMode === "latest" ? (
            <label className="td-label" htmlFor="td-latest-limit">
              عدد أحدث الرسائل
              <input
                id="td-latest-limit"
                className="td-input"
                type="number"
                min={1}
                max={1000}
                value={state.latestLimit}
                onChange={(event) =>
                  setState((current) => ({ ...current, latestLimit: event.target.value }))
                }
              />
            </label>
          ) : null}
          <div className="td-hint">
            <Info size={15} aria-hidden="true" />
            {scanHint(state.scanMode)}
          </div>
        </div>
        <div className="td-media-filter">
          <span className="td-label-text">نوع الوسائط</span>
          {mediaChoices.map((choice) => (
            <button
              type="button"
              key={choice.value}
              className={`td-filter ${state.mediaTypes.includes(choice.value) ? "is-selected" : ""}`}
              aria-pressed={state.mediaTypes.includes(choice.value)}
              onClick={() => toggleMedia(choice.value)}
            >
              {choice.label}
            </button>
          ))}
        </div>
      </div>
      <NoticeBar notice={state.notice} />
      {state.analyzed ? (
        <>
          <div className="td-results-head">
            <div>
              <span className="td-eyebrow">RESULTS</span>
              <h2>
                النتائج{" "}
                <small>
                  · {filteredFiles.length} عناصر · محدد {selectedCount}
                </small>
              </h2>
            </div>
            <div className="td-button-row">
              <button type="button" className="td-button td-button-secondary" onClick={selectAll}>
                تحديد الكل
              </button>
              <button
                type="button"
                className="td-button td-button-secondary"
                onClick={clearSelection}
              >
                مسح التحديد
              </button>
              <button
                type="button"
                className="td-button td-button-primary"
                onClick={enqueue}
                disabled={!canEnqueue}
              >
                <UploadCloud size={15} aria-hidden="true" />
                إضافة للطابور
              </button>
            </div>
          </div>
          <div className="td-table-wrap">
            <table className="td-table">
              <thead>
                <tr>
                  <th>اختيار</th>
                  <th>الملف</th>
                  <th>النوع</th>
                  <th>الحجم</th>
                  <th>التاريخ</th>
                  <th>الحالة</th>
                </tr>
              </thead>
              <tbody>
                {filteredFiles.map((file) => (
                  <tr key={file.id}>
                    <td data-label="اختيار">
                      <label className="td-check">
                        <input
                          type="checkbox"
                          checked={file.selected}
                          disabled={file.status === "quarantined"}
                          onChange={() => toggleFile(file.id)}
                          aria-label={`اختيار ${file.name}`}
                        />
                      </label>
                    </td>
                    <td data-label="الملف">
                      <strong>{file.name}</strong>
                      <small>{file.meta}</small>
                    </td>
                    <td data-label="النوع">{typeLabel(file.type)}</td>
                    <td className="td-number" data-label="الحجم">
                      {file.size}
                    </td>
                    <td className="td-number" data-label="التاريخ">
                      {file.date}
                    </td>
                    <td data-label="الحالة">
                      <span className={`td-status td-status-${file.status}`}>
                        {statusLabel(file.status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="td-selection-summary">
            <strong>قبل الإضافة:</strong> {selectedCount} ملفات · الوجهة:{" "}
            {state.folder ?? "لم يتم اختيار مجلد Drive"}
            <button
              type="button"
              className="td-link-button"
              onClick={() => onNavigate("connection")}
            >
              اختيار مجلد الوجهة
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

function QueueSection({ state, setState }: { state: SandboxState; setState: SetSandbox }) {
  const rows: MockFile[] = state.queue.length ? state.queue : state.files.slice(0, 4);
  const runningCount = state.engine === "running" ? Math.min(2, state.queue.length) : 0;

  const start = () => {
    if (!state.queue.length) {
      setNotice(setState, { kind: "warning", text: "الطابور فارغ." });
      return;
    }
    if (!state.folder) {
      setNotice(setState, { kind: "warning", text: "حدد مجلد الوجهة قبل البدء." });
      return;
    }
    setState((current) => ({
      ...current,
      engine: "running",
      queue: current.queue.map((file, index) =>
        index < 2
          ? { ...file, status: "running", progress: 68, speed: "14.2 MB/s", remaining: "0:34" }
          : file,
      ),
      notice: {
        kind: "info",
        text: "محاكاة محلية، لم يتم نقل أي ملف. لم يتم تنزيل أو رفع أي ملف حقيقي.",
      },
    }));
  };

  const pause = () =>
    setState((current) => ({
      ...current,
      engine: "paused",
      notice: { kind: "info", text: "محاكاة: تم الإيقاف المؤقت." },
    }));

  const resume = () =>
    setState((current) => ({
      ...current,
      engine: "running",
      notice: { kind: "info", text: "محاكاة: تم الاستئناف. لا يوجد نقل حقيقي." },
    }));

  const stop = () =>
    setState((current) => ({
      ...current,
      engine: "stopped",
      notice: { kind: "info", text: "محاكاة: تم الإيقاف." },
    }));

  return (
    <section className="td-page" aria-labelledby="queue-title">
      <SectionTitle
        titleId="queue-title"
        eyebrow="TRANSFERS"
        title="التحويلات"
        description="تنزيل محلي إلى ملف .part ثم رفع قابل للاستئناف. هذه الشاشة تجريبية ولا تنقل ملفات."
      />
      <div className="td-metrics">
        <div>
          <span>في الطابور</span>
          <strong>{state.queue.length}</strong>
        </div>
        <div>
          <span>قيد التنفيذ</span>
          <strong>
            {runningCount}
            <small> / 100</small>
          </strong>
        </div>
        <div>
          <span>مكتمل</span>
          <strong>37</strong>
        </div>
        <div>
          <span>فشل</span>
          <strong>1</strong>
        </div>
        <div>
          <span>المنقول</span>
          <strong>18.4 GB</strong>
        </div>
      </div>
      <NoticeBar notice={state.notice} />
      <div className="td-button-row td-transfer-actions">
        <button type="button" className="td-button td-button-primary" onClick={start}>
          <Play size={15} aria-hidden="true" />
          بدء
        </button>
        <button type="button" className="td-button td-button-secondary" onClick={pause}>
          <Pause size={15} aria-hidden="true" />
          إيقاف مؤقت
        </button>
        <button type="button" className="td-button td-button-secondary" onClick={resume}>
          <RefreshCw size={15} aria-hidden="true" />
          استئناف
        </button>
        <button type="button" className="td-button td-button-danger" onClick={stop}>
          <Square size={15} aria-hidden="true" />
          إيقاف
        </button>
        <button
          type="button"
          className="td-button td-button-secondary"
          onClick={() => setNotice(setState, { kind: "info", text: "محاكاة: تم تحديث القائمة." })}
        >
          <RefreshCw size={15} aria-hidden="true" />
          تحديث
        </button>
      </div>
      <div className="td-destination-banner">
        <Folder size={15} aria-hidden="true" />
        مجلد الوجهة: <strong>{state.folder ?? "غير محدد"}</strong>
      </div>
      <div className="td-table-wrap">
        <table className="td-table">
          <thead>
            <tr>
              <th>الملف</th>
              <th>الحالة</th>
              <th>التقدم</th>
              <th>السرعة</th>
              <th>المتبقي</th>
              <th>تحكم</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((file) => (
              <tr key={file.id}>
                <td data-label="الملف">
                  <strong>{file.name}</strong>
                  <small>{file.meta}</small>
                </td>
                <td data-label="الحالة">
                  <span className={`td-status td-status-${file.status}`}>
                    {statusLabel(file.status)}
                  </span>
                </td>
                <td data-label="التقدم">
                  <div className="td-progress">
                    <span style={{ width: `${file.progress}%` }} />
                  </div>
                  <small>{file.progress}%</small>
                </td>
                <td className="td-number" data-label="السرعة">
                  {file.speed || "—"}
                </td>
                <td className="td-number" data-label="المتبقي">
                  {file.remaining || "—"}
                </td>
                <td data-label="تحكم">
                  <button
                    type="button"
                    className="td-link-button"
                    onClick={() =>
                      setNotice(setState, {
                        kind: "info",
                        text: `محاكاة: إجراء العنصر ${file.name}.`,
                      })
                    }
                  >
                    إجراء
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const SAMPLE_LOGS = [
  "04:02:11.884  OK    upload.verified id=1aQ9x…kP2 size=4292118",
  "04:02:03.117  INFO  upload.start item=7d2a94 resumable session opened",
  "04:01:58.402  INFO  download.complete item=7d2a94 local=/content/tmp/7d2a94.part",
  "04:01:12.660  WARN  quota.check usage=42.7% remaining=57.3GB",
  "04:00:47.031  ERROR transfer.failed item=7d2a95 reason=size_mismatch",
  "03:59:20.775  INFO  queue.enqueue count=3 concurrency=2",
];

function LogsSection({ state, setState }: { state: SandboxState; setState: SetSandbox }) {
  const [query, setQuery] = useState("");
  const visible = SAMPLE_LOGS.filter((line) =>
    line.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <section className="td-page" aria-labelledby="logs-title">
      <SectionTitle
        titleId="logs-title"
        eyebrow="AUDIT TRAIL"
        title="السجلات"
        description="سجلات منقّحة. لا أرقام هواتف ولا رموز ولا توكنات، حتى في التنزيل."
      />
      <div className="td-log-toolbar">
        <label className="td-label td-grow" htmlFor="td-log-search">
          بحث
          <input
            id="td-log-search"
            className="td-input"
            placeholder="ابحث في السجلات"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="td-button td-button-secondary"
          onClick={() =>
            setNotice(setState, {
              kind: "info",
              text: `محاكاة: بحث محلي في ${visible.length} أسطر.`,
            })
          }
        >
          <Search size={15} aria-hidden="true" />
          بحث
        </button>
        <button
          type="button"
          className="td-button td-button-secondary"
          onClick={() =>
            setNotice(setState, { kind: "info", text: "محاكاة: تم تحديث السجلات المحلية." })
          }
        >
          <RefreshCw size={15} aria-hidden="true" />
          تحديث
        </button>
      </div>
      <NoticeBar notice={state.notice} />
      <div className="td-log-box">
        {visible.map((line) => (
          <code key={line}>{line}</code>
        ))}
      </div>
      <div className="td-inline-note">
        <ShieldCheck size={15} aria-hidden="true" />
        هذه السجلات محاكاة محلية، ولا تمثل تشغيلًا حقيقيًا.
      </div>
    </section>
  );
}

function SettingsSection({ state, setState }: { state: SandboxState; setState: SetSandbox }) {
  const [workers, setWorkers] = useState(2);

  return (
    <section className="td-page" aria-labelledby="settings-title">
      <SectionTitle
        titleId="settings-title"
        eyebrow="PREFERENCES"
        title="الإعدادات والتصدير"
        description="تجربة شكل الإعدادات فقط. لا يتم حفظ أي تغيير في SQLite من هذه الصفحة."
      />
      <NoticeBar notice={state.notice} />
      <div className="td-panel">
        <div className="td-setting-row">
          <div>
            <h2>الخيوط المتزامنة</h2>
            <p>القيمة الافتراضية 2، والحد الأقصى 100. فوق 8 يظهر تحذير.</p>
          </div>
          <div className="td-setting-control">
            <strong className="td-big-number">{workers}</strong>
            <label className="td-label" htmlFor="td-workers">
              عدد الخيوط
              <input
                id="td-workers"
                type="range"
                min={1}
                max={100}
                value={workers}
                onChange={(event) => setWorkers(Number(event.target.value))}
              />
            </label>
            <div className="td-range-labels">
              <span>1</span>
              <span>100</span>
            </div>
            {workers > 8 ? (
              <p className="td-warn-line">
                تحذير تجريبي: أكثر من 8 خيوط غير مختبر مقابل ذاكرة Colab.
              </p>
            ) : null}
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>اللغة</h2>
            <p>هذه النسخة التجريبية عربية RTL فقط. لا يوجد theme switcher.</p>
          </div>
          <div className="td-segment">
            <button type="button" className="is-active">
              العربية
            </button>
            <button type="button" disabled>
              English
            </button>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>الاستعادة ونقاط الحفظ</h2>
            <p>لا يوجد اتصال حقيقي، لذلك هذه الأزرار تعرض حالة محلية فقط.</p>
          </div>
          <div className="td-button-row">
            <button
              type="button"
              className="td-button td-button-secondary"
              onClick={() =>
                setNotice(setState, { kind: "info", text: "محاكاة: لا توجد نقطة حفظ محلية." })
              }
            >
              <RotateCcw size={15} aria-hidden="true" />
              استعادة الحالة
            </button>
            <button
              type="button"
              className="td-button td-button-secondary"
              onClick={() =>
                setNotice(setState, { kind: "success", text: "محاكاة: تم حفظ نقطة محلية." })
              }
            >
              <Check size={15} aria-hidden="true" />
              حفظ نقطة
            </button>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>التصدير</h2>
            <p>التصدير الحقيقي يتبع Notebook، وليس React Sandbox.</p>
          </div>
          <div className="td-button-row">
            <button
              type="button"
              className="td-button td-button-secondary"
              onClick={() =>
                setNotice(setState, { kind: "info", text: "محاكاة: لا يتم إنشاء ZIP حقيقي." })
              }
            >
              <FileArchive size={15} aria-hidden="true" />
              إنشاء ملف ZIP
            </button>
            <button
              type="button"
              className="td-button td-button-secondary"
              onClick={() =>
                setNotice(setState, { kind: "info", text: "محاكاة: خلايا Colab غير متصلة." })
              }
            >
              <FileText size={15} aria-hidden="true" />
              خلايا كولاب
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function TeleDriveSandbox() {
  const [state, setState] = useState<SandboxState>(initialState);
  const pages = useMemo(
    () => ({
      connection: <ConnectionSection state={state} setState={setState} />,
      analyze: (
        <AnalyzeSection
          state={state}
          setState={setState}
          onNavigate={(page) => setState((current) => ({ ...current, page }))}
        />
      ),
      queue: <QueueSection state={state} setState={setState} />,
      logs: <LogsSection state={state} setState={setState} />,
      settings: <SettingsSection state={state} setState={setState} />,
    }),
    [state],
  );

  return (
    <div className="td-app" dir="rtl">
      <TopBar state={state} />
      <SectionNav
        page={state.page}
        onNavigate={(page) => setState((current) => ({ ...current, page }))}
      />
      <main className="td-main">
        <div className="td-demo-banner">
          <Gauge size={15} aria-hidden="true" />
          <strong>نسخة تجريبية محلية</strong>
          <span>لا يوجد اتصال فعلي، ولا يتم نقل أي ملف.</span>
        </div>
        {pages[state.page]}
      </main>
    </div>
  );
}
