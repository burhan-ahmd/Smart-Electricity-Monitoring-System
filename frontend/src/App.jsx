import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart3,
  Check,
  Clipboard,
  CloudUpload,
  Copy,
  FileText,
  Gauge,
  ImagePlus,
  Loader2,
  PlugZap,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const REQUEST_TIMEOUT_MS = 180000;

const pipelineSteps = [
  { icon: CloudUpload, label: "Upload", text: "Two meter photos" },
  { icon: Gauge, label: "OCR", text: "Display detection" },
  { icon: ShieldCheck, label: "Validate", text: "Active meter match" },
  { icon: BarChart3, label: "Report", text: "Sheet and forecast" },
];

const featureCards = [
  {
    icon: Gauge,
    title: "Dual Meter OCR",
    body: "Reads two uploaded meter images and extracts decimal readings using the primary Gemini model with fallback support.",
  },
  {
    icon: ShieldCheck,
    title: "Smart Validation",
    body: "Maps photos to the correct active meters even when the images are uploaded in the wrong order.",
  },
  {
    icon: Activity,
    title: "Usage Forecasting",
    body: "Calculates usage, remaining capacity, daily average, and predicted month-end group totals.",
  },
  {
    icon: Clipboard,
    title: "WhatsApp Report",
    body: "Returns a clean client-ready electricity monitoring report that can be copied immediately.",
  },
];

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const units = ["B", "KB", "MB", "GB"];
  const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** power).toFixed(power ? 1 : 0)} ${units[power]}`;
}

function UploadCard({ slot, file, onFile, onClear, disabled }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function acceptFile(nextFile) {
    if (!nextFile) return;
    if (!nextFile.type.startsWith("image/")) return;
    onFile(nextFile);
  }

  return (
    <section
      className={`upload-card ${file ? "has-file" : ""} ${isDragging ? "dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        acceptFile(event.dataTransfer.files?.[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        disabled={disabled}
        onChange={(event) => acceptFile(event.target.files?.[0])}
      />

      {file ? (
        <>
          <img className="preview-image" src={previewUrl} alt={`${slot} preview`} />
          <div className="file-overlay">
            <div>
              <span>{slot}</span>
              <strong>{file.name}</strong>
              <small>{formatBytes(file.size)}</small>
            </div>
            <button className="icon-button glass" type="button" onClick={onClear} disabled={disabled} title="Remove image">
              <Trash2 size={18} />
            </button>
          </div>
        </>
      ) : (
        <button className="empty-upload" type="button" onClick={() => inputRef.current?.click()} disabled={disabled}>
          <span className="upload-icon">
            <ImagePlus size={28} />
          </span>
          <strong>{slot}</strong>
          <span>Drop image here or browse</span>
        </button>
      )}
    </section>
  );
}

function ReportPanel({ report, error, isLoading, onCopy, copied, onReset }) {
  const hasContent = Boolean(report || error || isLoading);

  return (
    <section className="report-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Generated Output</span>
          <h2>Client Report</h2>
        </div>
        <div className="report-actions">
          <button className="icon-button" type="button" onClick={onCopy} disabled={!report} title="Copy report">
            {copied ? <Check size={18} /> : <Copy size={18} />}
          </button>
          <button className="icon-button" type="button" onClick={onReset} disabled={!hasContent} title="Clear session">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      <div className={`report-body ${error ? "error" : ""} ${!hasContent ? "empty" : ""}`}>
        {isLoading && (
          <div className="loading-state">
            <Loader2 className="spin" size={34} />
            <strong>Processing meter photos</strong>
            <span>OCR, validation, sheet update, and analysis are running.</span>
          </div>
        )}

        {!isLoading && error && (
          <div className="message-state">
            <AlertCircle size={26} />
            <pre>{error}</pre>
          </div>
        )}

        {!isLoading && report && <pre>{report}</pre>}

        {!isLoading && !report && !error && (
          <div className="message-state muted">
            <FileText size={28} />
            <strong>Your WhatsApp-ready report will appear here.</strong>
            <span>Upload both active meter images, then run analysis.</span>
          </div>
        )}
      </div>
    </section>
  );
}

function App() {
  const [image1, setImage1] = useState(null);
  const [image2, setImage2] = useState(null);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const canSubmit = image1 && image2 && !isLoading;

  async function fetchTextWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      const contentType = response.headers.get("content-type") || "";
      const body = contentType.includes("application/json") ? await response.json() : await response.text();

      if (!response.ok) {
        throw new Error(typeof body === "string" ? body : body.message || "Meter processing failed.");
      }

      return body;
    } catch (err) {
      if (err.name === "AbortError") {
        throw err;
      }

      if (err instanceof TypeError) {
        throw new Error(
          `Network request failed for ${url}.\n\nCheck that the backend is running on http://127.0.0.1:8000 and that the frontend was restarted after the proxy update.`
        );
      }

      throw err;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  async function recoverLatestReport() {
    const latest = await fetchTextWithTimeout(`${API_BASE_URL}/latest-report`, {
      method: "GET",
      cache: "no-store",
    });

    if (typeof latest === "string" && latest.trim()) {
      setReport(latest);
      setError("");
      return true;
    }

    return false;
  }

  async function submitImages() {
    if (!canSubmit) return;

    const payload = new FormData();
    payload.append("image1", image1);
    payload.append("image2", image2);

    setIsLoading(true);
    setReport("");
    setError("");
    setCopied(false);

    try {
      const body = await fetchTextWithTimeout(`${API_BASE_URL}/process-meters`, {
        method: "POST",
        body: payload,
      });

      if (typeof body === "string") {
        setReport(body);
      } else if (body.status === "error") {
        setError(body.message || "Validation failed. Please upload the correct active meter images.");
      } else {
        setReport(body.report || JSON.stringify(body, null, 2));
      }
    } catch (err) {
      try {
        const recovered = await recoverLatestReport();
        if (!recovered) {
          setError("The upload finished unclearly, and no latest report was available. Please try again.");
        }
      } catch {
        const message = err.name === "AbortError"
          ? "The request took too long. The backend may still be processing; please check the sheet and try again."
          : err.message || "Could not connect to the meter backend through /api.";
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function copyReport() {
    if (!report) return;
    await navigator.clipboard.writeText(report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function resetSession() {
    setImage1(null);
    setImage2(null);
    setReport("");
    setError("");
    setCopied(false);
  }

  return (
    <main className="app-shell">
      <aside className="side-rail">
        <div className="brand-mark">
          <PlugZap size={24} />
        </div>
        <div className="rail-icons">
          <Gauge size={20} />
          <Activity size={20} />
          <BarChart3 size={20} />
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow"><Zap size={14} /> Meter Reading Console</span>
            <h1>Smart Electricity Monitoring System </h1>
          </div>
          <div className="api-pill">
            <span />
            {API_BASE_URL === "/api" ? "Vite proxy -> 127.0.0.1:8000" : API_BASE_URL.replace(/^https?:\/\//, "")}
          </div>
        </header>

        <section className="flow-strip">
          {pipelineSteps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div className="flow-step" key={step.label}>
                <Icon size={20} />
                <div>
                  <strong>{step.label}</strong>
                  <span>{step.text}</span>
                </div>
                {index < pipelineSteps.length - 1 && <ArrowRight className="flow-arrow" size={18} />}
              </div>
            );
          })}
        </section>

        <div className="main-grid">
          <section className="capture-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">Active Meter Images</span>
                <h2>Upload Today&apos;s Photos</h2>
              </div>
              <Sparkles size={22} />
            </div>

            <div className="upload-grid">
              <UploadCard slot="Image 1" file={image1} onFile={setImage1} onClear={() => setImage1(null)} disabled={isLoading} />
              <UploadCard slot="Image 2" file={image2} onFile={setImage2} onClear={() => setImage2(null)} disabled={isLoading} />
            </div>

            <div className="submit-row">
              <button className="primary-button" type="button" disabled={!canSubmit} onClick={submitImages}>
                {isLoading ? <Loader2 className="spin" size={19} /> : <Send size={19} />}
                {isLoading ? "Processing..." : "Process Meters"}
              </button>
              <button className="secondary-button" type="button" onClick={resetSession} disabled={isLoading && !report && !error}>
                Clear
              </button>
            </div>

            <div className="feature-grid">
              {featureCards.map((card) => {
                const Icon = card.icon;
                return (
                  <article className="feature-card" key={card.title}>
                    <Icon size={20} />
                    <strong>{card.title}</strong>
                    <p>{card.body}</p>
                  </article>
                );
              })}
            </div>
          </section>

          <ReportPanel report={report} error={error} isLoading={isLoading} onCopy={copyReport} copied={copied} onReset={resetSession} />
        </div>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
