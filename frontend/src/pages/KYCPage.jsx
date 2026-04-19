import React, { useEffect, useState } from "react";
import { kyc as kycApi } from "../api";
import {
  Table,
  Badge,
  Button,
  SectionHeader,
  Spinner,
  Alert,
  Card,
  colors,
  Input,
} from "../components/UI";
import { format } from "date-fns";

const STATUS_OPTIONS = [
  "",
  "pending",
  "processing",
  "review",
  "verified",
  "rejected",
];

export default function KYCPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [reviewStatus, setReviewStatus] = useState("verified");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewing, setReviewing] = useState(false);

  const load = (status = filter) => {
    setLoading(true);
    const params = status ? { status } : {};
    kycApi
      .queue(params)
      .then((r) => setRows(r.data))
      .catch(() => setError("Failed to load KYC queue"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleReview = async () => {
    if (!selected) return;
    setReviewing(true);
    try {
      await kycApi.review(selected.user_id, {
        status: reviewStatus,
        reviewer_notes: reviewNotes,
      });
      setSelected(null);
      load();
    } catch (e) {
      setError("Review failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setReviewing(false);
    }
  };

  const columns = [
    { key: "user_id", label: "User ID" },
    { key: "full_name", label: "Full Name" },
    { key: "status", label: "Status", render: (v) => <Badge status={v} /> },
    {
      key: "identity_score",
      label: "ID Score",
      render: (v) => (v != null ? (v * 100).toFixed(1) + "%" : "-"),
    },
    {
      key: "submitted_at",
      label: "Submitted",
      render: (v) => (v ? format(new Date(v), "dd MMM yyyy HH:mm") : "-"),
    },
    {
      key: "updated_at",
      label: "Updated",
      render: (v) => (v ? format(new Date(v), "dd MMM yyyy HH:mm") : "-"),
    },
  ];

  return (
    <div>
      <SectionHeader
        title="KYC Queue"
        subtitle="Identity verification submissions and status management"
      />

      {error && <Alert type="error" message={error} />}

      {/* Filters */}
      <Card
        style={{
          marginBottom: "20px",
          display: "flex",
          gap: "12px",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontSize: "13px", color: colors.muted }}>
          Filter by status:
        </span>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {STATUS_OPTIONS.map((s) => (
            <Button
              key={s}
              size="sm"
              variant={filter === s ? "primary" : "ghost"}
              onClick={() => {
                setFilter(s);
                load(s);
              }}
            >
              {s || "All"}
            </Button>
          ))}
        </div>
        <Button size="sm" variant="ghost" onClick={() => load()}>
          ↻ Refresh
        </Button>
      </Card>

      {/* Table */}
      <Card>
        {loading ? (
          <Spinner />
        ) : (
          <Table
            columns={columns}
            rows={rows}
            onRowClick={(row) => {
              setSelected(row);
              setReviewStatus("verified");
              setReviewNotes("");
            }}
          />
        )}
      </Card>

      {/* Review panel */}
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
            style={{ width: "440px", maxWidth: "90vw" }}
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
              Review KYC - {selected.user_id}
            </h3>

            <div
              style={{
                marginBottom: "16px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
                fontSize: "13px",
              }}
            >
              <div>
                <span style={{ color: colors.muted }}>Name:</span>{" "}
                {selected.full_name || "-"}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Current:</span>{" "}
                <Badge status={selected.status} />
              </div>
              <div>
                <span style={{ color: colors.muted }}>Score:</span>{" "}
                {selected.identity_score != null
                  ? (selected.identity_score * 100).toFixed(1) + "%"
                  : "-"}
              </div>
              <div>
                <span style={{ color: colors.muted }}>Submitted:</span>{" "}
                {selected.submitted_at
                  ? format(new Date(selected.submitted_at), "dd MMM yyyy")
                  : "-"}
              </div>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label
                style={{
                  fontSize: "12px",
                  color: colors.muted,
                  fontWeight: 500,
                  display: "block",
                  marginBottom: "6px",
                }}
              >
                Decision
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                {["verified", "rejected", "review"].map((s) => (
                  <Button
                    key={s}
                    size="sm"
                    variant={reviewStatus === s ? "primary" : "ghost"}
                    onClick={() => setReviewStatus(s)}
                  >
                    {s}
                  </Button>
                ))}
              </div>
            </div>

            <Input
              label="Reviewer Notes"
              placeholder="Optional notes for this decision…"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
            />

            <div
              style={{
                display: "flex",
                gap: "8px",
                justifyContent: "flex-end",
                marginTop: "8px",
              }}
            >
              <Button variant="ghost" onClick={() => setSelected(null)}>
                Cancel
              </Button>
              <Button onClick={handleReview} disabled={reviewing}>
                {reviewing ? "Saving…" : "Submit Decision"}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
