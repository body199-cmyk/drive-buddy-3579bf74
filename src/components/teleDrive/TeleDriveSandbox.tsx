/* eslint-disable prettier/prettier -- bun CI prettier wraps Arabic JSX differently than local npm prettier */
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
  Moon,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  Square,
  Sun,
  Terminal,
  UploadCloud,
  UserRound,
} from "lucide-react";
import {
  DEMO_FOLDERS,
  MAX_CONCURRENCY,
  MIN_CONCURRENCY,
  enqueueBlockReason,
  formatBytes,
  initialState,
  isPositiveInteger,
  isValidCode,
  isValidPhone,
  localize,
  mediaChoices,
  modeLabel,
  modes,
  pageLabels,
  queueMetrics,
  scanHint,
  setVisibleSelection,
  startQueuedFiles,
  statusLabel,
  transferableSelection,
  typeLabel,
  visibleFiles,
  type Language,
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
  language,
}: {
  label: string;
  connected: boolean;
  icon: ReactNode;
  language: Language;
}) {
  return (
    <span className={`td-chip ${connected ? "is-connected" : ""}`}>
      <span className="td-chip-dot" aria-hidden="true" />
      {icon}
      {label}: {connected ? localize(language, "متصل", "Connected") : localize(language, "غير متصل", "Disconnected")}
    </span>
  );
}

function TopBar({ state }: { state: SandboxState }) {
  const engineLabel = {
    stopped: localize(state.language, "متوقف", "Stopped"),
    running: localize(state.language, "يعمل", "Running"),
    paused: localize(state.language, "متوقف مؤقتًا", "Paused"),
  }[state.engine];

  return (
    <header className="td-topbar">
      <div className="td-brand">
        <span className="td-mark">TD</span>
        <strong>TeleDrive</strong>
      </div>
      <div className="td-prototype">
        <Terminal size={13} aria-hidden="true" />
        Prototype · Local demo
      </div>
      <div className="td-chips">
        <StatusChip
          label={localize(state.language, "تيليجرام", "Telegram")}
          connected={state.telegramConnected}
          icon={<UserRound size={13} aria-hidden="true" />}
          language={state.language}
        />
        <StatusChip
          label={localize(state.language, "درايف", "Drive")}
          connected={state.driveConnected}
          icon={<Cloud size={13} aria-hidden="true" />}
          language={state.language}
        />
        <span className={`td-chip ${state.folder ? "is-connected" : ""}`}>
          <span className="td-chip-dot" aria-hidden="true" />
          <Folder size={13} aria-hidden="true" />
          {localize(state.language, "المجلد", "Folder")}: {state.folder ?? localize(state.language, "غير محدد", "Not selected")}
        </span>
        <span className="td-chip">
          <span className="td-chip-dot" aria-hidden="true" />
          {localize(state.language, "المحرك", "Engine")}: {engineLabel}
        </span>
      </div>
    </header>
  );
}

const navItems: Array<{ id: Page; icon: ReactNode }> = [
  { id: "connection", icon: <UserRound size={15} aria-hidden="true" /> },
  { id: "analyze", icon: <Search size={15} aria-hidden="true" /> },
  { id: "queue", icon: <UploadCloud size={15} aria-hidden="true" /> },
  { id: "logs", icon: <Terminal size={15} aria-hidden="true" /> },
  { id: "settings", icon: <Settings size={15} aria-hidden="true" /> },
];

function SectionNav({
  page,
  language,
  onNavigate,
}: {
  page: Page;
  language: Language;
  onNavigate: (page: Page) => void;
}) {
  return (
    <nav className="td-nav" aria-label={localize(language, "أقسام TeleDrive", "TeleDrive sections")}>
      {navItems.map((item) => (
        <button
          type="button"
          key={item.id}
          className={`td-nav-button ${page === item.id ? "is-active" : ""}`}
          aria-current={page === item.id ? "page" : undefined}
          onClick={() => onNavigate(item.id)}
        >
          {item.icon}
          {pageLabels[item.id][language]}
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
    if (!isValidPhone(phone)) {
      setCodeVisible(false);
      setNotice(setState, {
        kind: "error",
        text: localize(
          state.language,
          "أدخل رقم هاتف صالحًا من 8 إلى 15 رقمًا قبل إرسال الرمز.",
          "Enter a valid phone number containing 8 to 15 digits before sending a code.",
        ),
      });
      return;
    }
    setCodeVisible(true);
    setNotice(setState, {
      kind: "info",
      text: localize(
        state.language,
        "محاكاة: تم إظهار خطوة الرمز. لم يُرسل أي رمز حقيقي.",
        "Simulation: the code step is now visible. No real code was sent.",
      ),
    });
  };

  const verifyCode = () => {
    if (!isValidCode(code)) {
      setNotice(setState, {
        kind: "error",
        text: localize(
          state.language,
          "أدخل رمز تحقق صالحًا من 5 أو 6 أرقام.",
          "Enter a valid 5- or 6-digit verification code.",
        ),
      });
      return;
    }
    setState((current) => ({
      ...current,
      telegramConnected: true,
      notice: {
        kind: "success",
        text: localize(
          current.language,
          "محاكاة: تغيّرت شريحة تيليجرام إلى متصل. لا توجد جلسة حقيقية.",
          "Simulation: Telegram is shown as connected. No real session exists.",
        ),
      },
    }));
  };

  const logout = () => {
    setCodeVisible(false);
    setCode("");
    setState((current) => ({
      ...current,
      telegramConnected: false,
      notice: {
        kind: "info",
        text: localize(
          current.language,
          "محاكاة: أُعيد تيليجرام إلى غير متصل.",
          "Simulation: Telegram was reset to disconnected.",
        ),
      },
    }));
  };

  const connectDrive = () => {
    setState((current) => ({
      ...current,
      driveConnected: true,
      notice: {
        kind: "success",
        text: localize(
          current.language,
          "محاكاة: تغيّرت شريحة درايف إلى متصل. لا يوجد OAuth.",
          "Simulation: Drive is shown as connected. No OAuth request was made.",
        ),
      },
    }));
  };

  const selectFolder = (folder: string) => {
    if (!state.driveConnected) {
      setNotice(setState, {
        kind: "warning",
        text: localize(
          state.language,
          "اربط Drive تجريبيًا قبل اختيار المجلد.",
          "Connect the Drive demo before choosing a folder.",
        ),
      });
      return;
    }
    setState((current) => ({
      ...current,
      folder,
      notice: {
        kind: "success",
        text: localize(
          current.language,
          `محاكاة: تم اختيار المجلد ${folder}.`,
          `Simulation: selected ${folder}.`,
        ),
      },
    }));
  };

  return (
    <section className="td-page" aria-labelledby="connection-title">
      <SectionTitle
        titleId="connection-title"
        eyebrow="CONNECTION CENTER"
        title={pageLabels.connection[state.language]}
        description={localize(
          state.language,
          "تيليجرام على اليمين ودرايف على اليسار. كل زر هنا يغيّر الحالة المحلية فقط ولا يفتح أي اتصال.",
          "Telegram and Drive are local controls. Every action changes this demo only and opens no connection.",
        )}
      />
      <div className="td-split">
        <article className="td-panel">
          <div className="td-conn-head">
            <UserRound size={18} aria-hidden="true" />
            <div>
              <h2>{localize(state.language, "تيليجرام", "Telegram")}</h2>
              <p>
                {state.telegramConnected
                  ? localize(state.language, "حالة الشريحة: متصل (تجريبي)", "Status: connected (demo)")
                  : localize(state.language, "حالة الشريحة: غير متصل", "Status: disconnected")}
              </p>
            </div>
          </div>
          <div className="td-stack">
            <label className="td-label" htmlFor="td-phone">
              {localize(state.language, "رقم الهاتف", "Phone number")}
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
                {localize(state.language, "إرسال الرمز", "Send code")}
              </button>
              <button type="button" className="td-button td-button-secondary" onClick={sendCode}>
                {localize(state.language, "إعادة الإرسال", "Resend")}
              </button>
            </div>
            {codeVisible ? (
              <div className="td-otp-panel">
                <label className="td-label" htmlFor="td-code">
                  {localize(state.language, "رمز التحقق", "Verification code")}
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
                  {localize(state.language, "تأكيد الرمز", "Verify code")}
                </button>
              </div>
            ) : null}
            <div className="td-button-row">
              <button type="button" className="td-button td-button-danger" onClick={logout}>
                <LogOut size={15} aria-hidden="true" />
                {localize(state.language, "تسجيل الخروج", "Log out")}
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
                {state.driveConnected
                  ? localize(state.language, "حالة الشريحة: متصل (تجريبي)", "Status: connected (demo)")
                  : localize(state.language, "حالة الشريحة: غير متصل", "Status: disconnected")}
              </p>
            </div>
          </div>
          <div className="td-stack">
            <div className="td-button-row">
              <button type="button" className="td-button td-button-primary" onClick={connectDrive}>
                {localize(state.language, "ربط Drive", "Connect Drive")}
              </button>
              <button
                type="button"
                className="td-button td-button-secondary"
                onClick={connectDrive}
              >
                {localize(state.language, "إعادة الربط", "Reconnect")}
              </button>
            </div>
            <div>
              <span className="td-label-text">
                {localize(state.language, "مجلد الوجهة التجريبي", "Demo destination folder")}
              </span>
              {!state.driveConnected ? (
                <p id="td-folder-gate" className="td-control-reason">
                  {localize(
                    state.language,
                    "اربط Drive التجريبي أولًا لتفعيل اختيار المجلد.",
                    "Connect the Drive demo first to enable folder selection.",
                  )}
                </p>
              ) : null}
              <div className="td-folder-list" role="list">
                {DEMO_FOLDERS.map((folder) => (
                  <button
                    type="button"
                    key={folder}
                    className={`td-folder-option ${state.folder === folder ? "is-selected" : ""}`}
                    onClick={() => selectFolder(folder)}
                    disabled={!state.driveConnected}
                    aria-describedby={!state.driveConnected ? "td-folder-gate" : undefined}
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
  const filteredFiles = visibleFiles(state.files, state.mediaTypes);
  const selectedCount = transferableSelection(filteredFiles).length;
  const blockReason = enqueueBlockReason(state.folder, selectedCount);
  const canEnqueue = blockReason === null;
  const blockReasonText =
    blockReason === "folder"
      ? localize(
          state.language,
          "اختر مجلد Drive الوجهة قبل إضافة الملفات للطابور.",
          "Choose a Drive destination folder before adding files to the queue.",
        )
      : blockReason === "selection"
        ? localize(
            state.language,
            "حدد ملفًا ظاهرًا واحدًا على الأقل؛ الملفات المعزولة لا يمكن إضافتها.",
            "Select at least one visible file; quarantined files cannot be queued.",
          )
        : localize(
            state.language,
            "جاهز لإضافة الملفات المحددة والظاهرة إلى الطابور.",
            "Ready to add the selected visible files to the queue.",
          );

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
        file.id === id && file.status !== "quarantined"
          ? { ...file, selected: !file.selected }
          : file,
      ),
    }));
  };

  const selectAll = () => {
    setState((current) => ({
      ...current,
      files: setVisibleSelection(current.files, current.mediaTypes, true),
    }));
  };

  const clearSelection = () => {
    setState((current) => ({
      ...current,
      files: setVisibleSelection(current.files, current.mediaTypes, false),
    }));
  };

  const analyze = () => {
    if (!state.sourceLink.trim()) {
      setNotice(setState, {
        kind: "error",
        text: localize(state.language, "أدخل رابط الرسالة أو القناة قبل التحليل.", "Enter a message or channel link before analyzing."),
      });
      return;
    }
    if (
      (state.scanMode === "message" || state.scanMode === "group") &&
      !isPositiveInteger(state.messageId)
    ) {
      setNotice(setState, {
        kind: "error",
        text: localize(state.language, "أدخل رقم رسالة صحيحًا قبل التحليل.", "Enter a valid positive message ID before analyzing."),
      });
      return;
    }
    if (state.scanMode === "range") {
      const from = Number(state.rangeFrom);
      const to = Number(state.rangeTo);
      if (
        !isPositiveInteger(state.rangeFrom) ||
        !isPositiveInteger(state.rangeTo) ||
        to < from ||
        to - from + 1 > 1000
      ) {
        setNotice(setState, {
          kind: "error",
          text: localize(
            state.language,
            "النطاق غير صالح، ويجب ألا يتجاوز 1000 رسالة.",
            "The range is invalid or exceeds 1,000 messages.",
          ),
        });
        return;
      }
    }
    if (
      state.scanMode === "latest" &&
      (!isPositiveInteger(state.latestLimit) || Number(state.latestLimit) > 1000)
    ) {
      setNotice(setState, {
        kind: "error",
        text: localize(
          state.language,
          "عدد الرسائل يجب أن يكون بين 1 و1000.",
          "The message count must be between 1 and 1,000.",
        ),
      });
      return;
    }
    setState((current) => ({
      ...current,
      analyzed: true,
      notice: {
        kind: "success",
        text: localize(
          current.language,
          `محاكاة: ظهرت نتائج التحليل بنمط «${modeLabel(current.scanMode, current.language)}»، ولم يُضف أي ملف للطابور.`,
          `Simulation: ${modeLabel(current.scanMode, current.language)} results are visible; nothing was added to the queue.`,
        ),
      },
    }));
  };

  const enqueue = () => {
    const chosen = transferableSelection(filteredFiles);
    const reason = enqueueBlockReason(state.folder, chosen.length);
    if (reason) {
      setNotice(setState, { kind: "warning", text: blockReasonText });
      return;
    }
    setState((current) => {
      const existingIds = new Set(current.queue.map((file) => file.id));
      const additions = chosen
        .filter((file) => !existingIds.has(file.id))
        .map((file) => ({
          ...file,
          status: "queued" as const,
          progress: 0,
          speed: "",
          remaining: "",
        }));
      return {
        ...current,
        queue: [...current.queue, ...additions],
        files: current.files.map((file) =>
          chosen.some((item) => item.id === file.id)
            ? { ...file, status: "queued" as const }
            : file,
        ),
        notice: {
          kind: "success",
          text: localize(
            current.language,
            `محاكاة: أُضيف ${additions.length} ملف للطابور المحلي.`,
            `Simulation: ${additions.length} file(s) were added to the local queue.`,
          ),
        },
      };
    });
    onNavigate("queue");
  };

  return (
    <section className="td-page" aria-labelledby="analyze-title">
      <SectionTitle
        titleId="analyze-title"
        eyebrow="ANALYZE & SELECT"
        title={pageLabels.analyze[state.language]}
        description={localize(
          state.language,
          "اختر نطاق الفحص ونوع الوسائط، ثم راجع الملفات وحدد ما تريد نقله قبل إضافته إلى القائمة.",
          "Choose a scan scope and media types, review the results, then select files before queuing them.",
        )}
      />
      <div className="td-analysis-line td-panel">
        <label className="td-label td-grow" htmlFor="td-link">
          رابط الرسالة أو القناة
          <input
            id="td-link"
            className="td-input"
            placeholder="https://t.me/channel/123"
            autoComplete="off"
            value={state.sourceLink}
            onChange={(event) =>
              setState((current) => ({ ...current, sourceLink: event.target.value }))
            }
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
                  {mode.label[state.language]}
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
            {scanHint(state.scanMode, state.language)}
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
              {choice.label[state.language]}
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
                aria-describedby="td-enqueue-reason"
              >
                <UploadCloud size={15} aria-hidden="true" />
                إضافة للطابور
              </button>
            </div>
          </div>
          <p
            id="td-enqueue-reason"
            className={`td-control-reason ${canEnqueue ? "is-ready" : ""}`}
          >
            {blockReasonText}
          </p>
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
                    <td data-label={localize(state.language, "النوع", "Type")}>
                      {typeLabel(file.type, state.language)}
                    </td>
                    <td className="td-number" data-label="الحجم">
                      {file.size}
                    </td>
                    <td className="td-number" data-label="التاريخ">
                      {file.date}
                    </td>
                    <td data-label="الحالة">
                      <span className={`td-status td-status-${file.status}`}>
                        {statusLabel(file.status, state.language)}
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
  const rows: MockFile[] = state.queue;
  const metrics = queueMetrics(state.queue);

  const start = () => {
    if (!state.queue.length) {
      setNotice(setState, {
        kind: "warning",
        text: localize(state.language, "الطابور فارغ.", "The queue is empty."),
      });
      return;
    }
    if (!state.folder) {
      setNotice(setState, {
        kind: "warning",
        text: localize(
          state.language,
          "حدد مجلد الوجهة قبل البدء.",
          "Choose a destination folder before starting.",
        ),
      });
      return;
    }
    setState((current) => ({
      ...current,
      engine: "running",
      queue: startQueuedFiles(current.queue, current.concurrency),
      notice: {
        kind: "info",
        text: localize(
          current.language,
          `محاكاة محلية بتزامن ${current.concurrency}، ولم يُنقل أي ملف حقيقي.`,
          `Local simulation with concurrency ${current.concurrency}; no real file was transferred.`,
        ),
      },
    }));
  };

  const pause = () =>
    setState((current) => ({
      ...current,
      engine: "paused",
      notice: {
        kind: "info",
        text: localize(current.language, "محاكاة: تم الإيقاف المؤقت.", "Simulation paused."),
      },
    }));

  const resume = () =>
    setState((current) => ({
      ...current,
      engine: "running",
      queue: startQueuedFiles(current.queue, current.concurrency),
      notice: {
        kind: "info",
        text: localize(
          current.language,
          "محاكاة: تم الاستئناف. لا يوجد نقل حقيقي.",
          "Simulation resumed. No real transfer is running.",
        ),
      },
    }));

  const stop = () =>
    setState((current) => ({
      ...current,
      engine: "stopped",
      queue: current.queue.map((file) =>
        file.status === "running"
          ? { ...file, status: "queued" as const, speed: "", remaining: "" }
          : file,
      ),
      notice: {
        kind: "info",
        text: localize(current.language, "محاكاة: تم الإيقاف.", "Simulation stopped."),
      },
    }));

  return (
    <section className="td-page" aria-labelledby="queue-title">
      <SectionTitle
        titleId="queue-title"
        eyebrow="TRANSFERS"
        title={pageLabels.queue[state.language]}
        description={localize(
          state.language,
          "هذه محاكاة لطابور قابل للاستئناف؛ الشاشة التجريبية لا تنزّل أو ترفع ملفات.",
          "This is a resumable-queue simulation; the sandbox downloads and uploads no files.",
        )}
      />
      <div className="td-metrics">
        <div>
          <span>{localize(state.language, "في الانتظار", "Queued")}</span>
          <strong>{metrics.queued}</strong>
        </div>
        <div>
          <span>{localize(state.language, "قيد التنفيذ", "Running")}</span>
          <strong>
            {metrics.running}
            <small> / {state.concurrency}</small>
          </strong>
        </div>
        <div>
          <span>{localize(state.language, "مكتمل", "Completed")}</span>
          <strong>{metrics.uploaded}</strong>
        </div>
        <div>
          <span>{localize(state.language, "فشل", "Failed")}</span>
          <strong>{metrics.failed}</strong>
        </div>
        <div>
          <span>{localize(state.language, "المنقول", "Transferred")}</span>
          <strong>{formatBytes(metrics.transferredBytes)}</strong>
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
        {localize(state.language, "مجلد الوجهة", "Destination folder")}: {" "}
        <strong>{state.folder ?? localize(state.language, "غير محدد", "Not selected")}</strong>
      </div>
      {!rows.length ? (
        <div className="td-empty-state" role="status">
          {localize(
            state.language,
            "الطابور فارغ. حلّل النتائج وحدد الملفات ثم أضفها هنا.",
            "The queue is empty. Analyze, select files, and add them here.",
          )}
        </div>
      ) : null}
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
                    {statusLabel(file.status, state.language)}
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
  "04:01:58.402  INFO  download.complete item=7d2a94 local=[redacted]/7d2a94.part",
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
        title={pageLabels.logs[state.language]}
        description={localize(
          state.language,
          "سجلات عينة منقّحة بلا أرقام هواتف أو رموز أو توكنات أو مسارات تشغيل حقيقية.",
          "Redacted sample logs with no phone numbers, codes, tokens, or real runtime paths.",
        )}
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
  const setLanguage = (language: Language) =>
    setState((current) => ({
      ...current,
      language,
      notice: {
        kind: "success",
        text: localize(
          language,
          "تم تغيير اللغة والاتجاه محليًا مع الاحتفاظ بالحالة.",
          "Language and direction changed locally without resetting state.",
        ),
      },
    }));

  return (
    <section className="td-page" aria-labelledby="settings-title">
      <SectionTitle
        titleId="settings-title"
        eyebrow="PREFERENCES"
        title={pageLabels.settings[state.language]}
        description={localize(
          state.language,
          "إعدادات محلية لهذه الصفحة فقط؛ لا يُحفظ أي تغيير خارج الذاكرة.",
          "Local settings for this page only; no change is persisted outside memory.",
        )}
      />
      <NoticeBar notice={state.notice} />
      <div className="td-panel">
        <div className="td-setting-row">
          <div>
            <h2>{localize(state.language, "التحويلات المتزامنة", "Concurrent transfers")}</h2>
            <p>
              {localize(
                state.language,
                "النطاق المحلي من 1 إلى 4، والقيمة الافتراضية 2.",
                "The local range is 1 to 4, with a default of 2.",
              )}
            </p>
          </div>
          <div className="td-setting-control">
            <strong className="td-big-number">{state.concurrency}</strong>
            <label className="td-label" htmlFor="td-workers">
              عدد الخيوط
              <input
                id="td-workers"
                type="range"
                min={MIN_CONCURRENCY}
                max={MAX_CONCURRENCY}
                value={state.concurrency}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    concurrency: Number(event.target.value),
                    notice: {
                      kind: "info",
                      text: localize(
                        current.language,
                        `محاكاة: التزامن الآن ${event.target.value}.`,
                        `Simulation: concurrency is now ${event.target.value}.`,
                      ),
                    },
                  }))
                }
              />
            </label>
            <div className="td-range-labels">
              <span>{MIN_CONCURRENCY}</span>
              <span>{MAX_CONCURRENCY}</span>
            </div>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(state.language, "اللغة", "Language")}</h2>
            <p>
              {localize(
                state.language,
                "تبديل محلي بين العربية RTL والإنجليزية LTR من دون تصفير الحالة.",
                "Switch locally between Arabic RTL and English LTR without resetting state.",
              )}
            </p>
          </div>
          <div className="td-segment" aria-label={localize(state.language, "اللغة", "Language")}>
            <button
              type="button"
              className={state.language === "ar" ? "is-active" : ""}
              aria-pressed={state.language === "ar"}
              onClick={() => setLanguage("ar")}
            >
              العربية
            </button>
            <button
              type="button"
              className={state.language === "en" ? "is-active" : ""}
              aria-pressed={state.language === "en"}
              onClick={() => setLanguage("en")}
            >
              English
            </button>
          </div>
        </div>
        <div className="td-setting-row">
          <div>
            <h2>{localize(state.language, "المظهر", "Theme")}</h2>
            <p>
              {localize(
                state.language,
                "المظهر محلي داخل صفحة التجربة فقط.",
                "The theme applies only inside this local sandbox.",
              )}
            </p>
          </div>
          <div className="td-segment" aria-label={localize(state.language, "المظهر", "Theme")}>
            <button
              type="button"
              className={state.theme === "light" ? "is-active" : ""}
              aria-pressed={state.theme === "light"}
              onClick={() =>
                setState((current) => ({
                  ...current,
                  theme: "light",
                  notice: {
                    kind: "success",
                    text: localize(current.language, "تم تفعيل المظهر الفاتح محليًا.", "Local light theme enabled."),
                  },
                }))
              }
            >
              <Sun size={15} aria-hidden="true" />
              {localize(state.language, "فاتح", "Light")}
            </button>
            <button
              type="button"
              className={state.theme === "dark" ? "is-active" : ""}
              aria-pressed={state.theme === "dark"}
              onClick={() =>
                setState((current) => ({
                  ...current,
                  theme: "dark",
                  notice: {
                    kind: "success",
                    text: localize(current.language, "تم تفعيل المظهر الداكن محليًا.", "Local dark theme enabled."),
                  },
                }))
              }
            >
              <Moon size={15} aria-hidden="true" />
              {localize(state.language, "داكن", "Dark")}
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
    <div
      className="td-app"
      lang={state.language}
      dir={state.language === "ar" ? "rtl" : "ltr"}
      data-theme={state.theme}
    >
      <TopBar state={state} />
      <SectionNav
        page={state.page}
        language={state.language}
        onNavigate={(page) => setState((current) => ({ ...current, page }))}
      />
      <main className="td-main">
        <div className="td-demo-banner">
          <Gauge size={15} aria-hidden="true" />
          <strong>{localize(state.language, "نسخة تجريبية محلية", "Local UI prototype")}</strong>
          <span>
            {localize(
              state.language,
              "لا يوجد اتصال فعلي، ولا يتم نقل أي ملف.",
              "There is no live connection and no file is transferred.",
            )}
          </span>
        </div>
        {pages[state.page]}
      </main>
    </div>
  );
}
