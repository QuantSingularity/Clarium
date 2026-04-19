import React, { useEffect, useState } from "react";
import { aml as amlApi } from "../api";
import {
  Table,
  Badge,
  Button,
  SectionHeader,
  Spinner,
  Alert,
  Card,
  colors,
} from "../components/UI";
import { format } from "date-fns";

export default function AMLPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [flagOnly, setFlagOnly] = useState(true);
  const [selected, setSelected] = useState(null);
  const [updating, setUpdating] = useState(false);

  const load = (fo = flagOnly) => {
    setLoading(true);
    amlApi
      .flags({ flagged_only: fo, limit: 100 })
      .then((r) => setRows(r.data))
      .catch(() => setError("Failed to load AML flags"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleStatusUpdate = async (id, status) => {
    setUpdating(true);
    try {
      await amlApi.review(id, status);
      setSelected(null);
      load();
    } catch (e) {
      setError("Update failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setUpdating(false);
    }
  };

  const columns = [
    { key: "transaction_id", label: "Transaction ID" },
    { key: "user_id", label: "User ID" },
    {
      key: "amount",
      label: "Amount",
      render: (v, r) => `${parseFloat(v).toLocaleString()} ${r.currency}`,
    },
    {
      key: "risk_score",
      label: "Risk Score",
      render: (v) => (
        <span
          style={{
            color:
              v >= 0.7 ? colors.red : v >= 0.4 ? colors.yellow : colors.green,
            fontWeight: 600,
          }}
        >
          {(v * 100).toFixed(0)}%
        </span>
      ),
    },
    {
      key: "pep_match",
      label: "PEP",
      render: (v) => (v ? <Badge status="high" label="PEP" /> : "-"),
    },
    { key: "status", label: "Status", render: (v) => <Badge status={v} /> },
    {
      key: "checked_at",
      label: "Checked",
      render: (v) => format(new Date(v), "dd MMM HH:mm"),
    },
  ];

  return (
    <div>
      <SectionHeader
        title="AML Flags"
        subtitle="Transaction monitoring - flagged by amount, velocity, geo risk, or PEP match"
      />

      {error && <Alert type="error" message={error} />}

      <Card
        style={{
          marginBottom: "20px",
          display: "flex",
          gap: "12px",
          alignItems: "center",
        }}
      >
        <Button
          size="sm"
          variant={flagOnly ? "primary" : "ghost"}
          onClick={() => {
            setFlagOnly(true);
            load(true);
          }}
        >
          Flagged only
        </Button>
        <Button
          size="sm"
          variant={!flagOnly ? "primary" : "ghost"}
          onClick={() => {
            setFlagOnly(false);
            load(false);
          }}
        >
          All checks
        </Button>
        <Button size="sm" variant="ghost" onClick={() => load()}>
          ↻ Refresh
        </Button>
      </Card>

      <Card>
        {loading ? (
          <Spinner />
        ) : (
          <Table columns={columns} rows={rows} onRowClick={setSelected} />
        )}
      </Card>

      {/* Detail panel */}
      {selected && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "#00000088",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
          onClick={() => setSelected(null)}
        >
          <Card
            style={{ width: "520px", maxWidth: "90vw" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3
              style={{
                fontWeight: 700,
                fontSize: "16px",
                color: "#f1f5f9",
                marginBottom: "16px",
              }}
            >
              AML Detail - {selected.transaction_id}
            </h3>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "10px",
                fontSize: "13px",
                marginBottom: "16px",
              }}
            >
              <div>
                <span style={{ color: colors.muted }}>User:</span>{" "}
                {selected.user_id || "-"}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Status:</span>{" "}
                <Badge status={selected.status} />
              </div>
              <div>
                <span style={{ color: colors.muted }}>Amount:</span>{" "}
                {parseFloat(selected.amount).toLocaleString()}{" "}
                {selected.currency}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Risk Score:</span>{" "}
                <strong>{(selected.risk_score * 100).toFixed(1)}%</strong>
              </div>
              <div>
                <span style={{ color: colors.muted }}>Source:</span>{" "}
                {selected.source_country || "-"}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Dest:</span>{" "}
                {selected.destination_country || "-"}
              </div>
              <div>
                <span style={{ color: colors.muted }}>PEP Match:</span>{" "}
                {selected.pep_match ? (
                  <Badge status="high" label="YES" />
                ) : (
                  "No"
                )}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Checked:</span>{" "}
                {format(new Date(selected.checked_at), "dd MMM yyyy HH:mm")}
              </div>
            </div>

            {selected.flag_reasons?.length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                <p
                  style={{
                    fontSize: "12px",
                    color: colors.muted,
                    fontWeight: 600,
                    marginBottom: "6px",
                    textTransform: "uppercase",
                  }}
                >
                  Flag Reasons
                </p>
                {selected.flag_reasons.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: "12px",
                      background: "#2d0a0a",
                      border: "1px solid #ef444430",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      marginBottom: "4px",
                      color: "#fca5a5",
                    }}
                  >
                    {r}
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleStatusUpdate(selected.id, "under_review")}
                disabled={updating}
              >
                Mark Under Review
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleStatusUpdate(selected.id, "escalated")}
                disabled={updating}
                style={{ color: colors.yellow }}
              >
                Escalate
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleStatusUpdate(selected.id, "cleared")}
                disabled={updating}
                style={{ color: colors.green }}
              >
                Clear
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelected(null)}
              >
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
