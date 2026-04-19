import React from "react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const T = {
  bg: "#0f1117",
  surface: "#1a1f2e",
  border: "#2a3248",
  accent: "#6366f1",
  accentHv: "#818cf8",
  text: "#e2e8f0",
  muted: "#64748b",
  green: "#10b981",
  yellow: "#f59e0b",
  red: "#ef4444",
  blue: "#3b82f6",
};

// ── Badge ─────────────────────────────────────────────────────────────────────
const STATUS_COLORS = {
  pending: { bg: "#1e3a5f", color: "#60a5fa" },
  processing: { bg: "#1e3a5f", color: "#93c5fd" },
  verified: { bg: "#064e3b", color: "#34d399" },
  rejected: { bg: "#4c0519", color: "#f87171" },
  review: { bg: "#451a03", color: "#fbbf24" },
  clear: { bg: "#064e3b", color: "#34d399" },
  flagged: { bg: "#4c0519", color: "#f87171" },
  under_review: { bg: "#451a03", color: "#fbbf24" },
  escalated: { bg: "#3b0764", color: "#c084fc" },
  cleared: { bg: "#064e3b", color: "#34d399" },
  delivered: { bg: "#064e3b", color: "#34d399" },
  failed: { bg: "#4c0519", color: "#f87171" },
  retrying: { bg: "#451a03", color: "#fbbf24" },
  high: { bg: "#4c0519", color: "#f87171" },
  medium: { bg: "#451a03", color: "#fbbf24" },
  low: { bg: "#064e3b", color: "#34d399" },
};

export function Badge({ status, label }) {
  const s = STATUS_COLORS[status] || { bg: "#1a1f2e", color: "#94a3b8" };
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: "999px",
        fontSize: "11px",
        fontWeight: 600,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        background: s.bg,
        color: s.color,
      }}
    >
      {label || status}
    </span>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, style = {} }) {
  return (
    <div
      style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: "12px",
        padding: "20px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// ── StatCard ──────────────────────────────────────────────────────────────────
export function StatCard({ label, value, color = T.accent, icon }) {
  return (
    <Card style={{ textAlign: "center", flex: 1 }}>
      <div style={{ fontSize: "28px", fontWeight: 700, color }}>
        {value ?? "-"}
      </div>
      <div style={{ fontSize: "13px", color: T.muted, marginTop: "4px" }}>
        {label}
      </div>
    </Card>
  );
}

// ── Table ─────────────────────────────────────────────────────────────────────
export function Table({ columns, rows, onRowClick }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}
      >
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{
                  padding: "10px 14px",
                  textAlign: "left",
                  color: T.muted,
                  fontWeight: 600,
                  borderBottom: `1px solid ${T.border}`,
                  whiteSpace: "nowrap",
                }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{ padding: "32px", textAlign: "center", color: T.muted }}
              >
                No records found
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick && onRowClick(row)}
                style={{
                  borderBottom: `1px solid ${T.border}`,
                  cursor: onRowClick ? "pointer" : "default",
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => {
                  if (onRowClick) e.currentTarget.style.background = "#1e2538";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    style={{ padding: "10px 14px", color: T.text }}
                  >
                    {c.render ? c.render(row[c.key], row) : (row[c.key] ?? "-")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
export function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled,
  style = {},
}) {
  const bg =
    variant === "primary" ? T.accent : variant === "danger" ? T.red : T.surface;
  const color = variant === "ghost" ? T.muted : "#fff";
  const pad = size === "sm" ? "5px 12px" : "9px 18px";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: pad,
        background: disabled ? T.border : bg,
        color: disabled ? T.muted : color,
        border: variant === "ghost" ? `1px solid ${T.border}` : "none",
        borderRadius: "8px",
        fontSize: "13px",
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "opacity 0.15s",
        ...style,
      }}
    >
      {children}
    </button>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
export function Input({ label, ...props }) {
  return (
    <div style={{ marginBottom: "12px" }}>
      {label && (
        <label
          style={{
            display: "block",
            fontSize: "12px",
            color: T.muted,
            marginBottom: "4px",
            fontWeight: 500,
          }}
        >
          {label}
        </label>
      )}
      <input
        {...props}
        style={{
          width: "100%",
          background: "#0f1117",
          border: `1px solid ${T.border}`,
          borderRadius: "8px",
          padding: "8px 12px",
          color: T.text,
          fontSize: "13px",
          outline: "none",
        }}
      />
    </div>
  );
}

// ── Section Header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, action }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: "20px",
      }}
    >
      <div>
        <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#f1f5f9" }}>
          {title}
        </h2>
        {subtitle && (
          <p style={{ fontSize: "13px", color: T.muted, marginTop: "3px" }}>
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
      <div
        style={{
          width: "32px",
          height: "32px",
          border: `3px solid #2a3248`,
          borderTop: `3px solid #6366f1`,
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Alert ─────────────────────────────────────────────────────────────────────
export function Alert({ type = "info", message }) {
  const colors = {
    error: T.red,
    success: T.green,
    warning: T.yellow,
    info: T.blue,
  };
  const bg = {
    error: "#2d0a0a",
    success: "#022c22",
    warning: "#1c0f00",
    info: "#0c1a2e",
  };
  return (
    <div
      style={{
        padding: "12px 16px",
        borderRadius: "8px",
        border: `1px solid ${colors[type]}30`,
        background: bg[type],
        color: colors[type],
        fontSize: "13px",
        marginBottom: "16px",
      }}
    >
      {message}
    </div>
  );
}

export const colors = T;
