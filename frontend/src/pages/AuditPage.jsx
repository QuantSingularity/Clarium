import React, { useEffect, useState } from "react";
import { audit as auditApi } from "../api";
import {
  Table,
  Button,
  SectionHeader,
  Spinner,
  Alert,
  Card,
  Badge,
  Input,
  colors,
} from "../components/UI";
import { format } from "date-fns";

export default function AuditPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [entityId, setEntityId] = useState("");
  const [chainOk, setChainOk] = useState(null);
  const [checking, setChecking] = useState(false);

  const loadRecent = () => {
    setLoading(true);
    auditApi
      .recent({ limit: 100 })
      .then((r) => setRows(r.data))
      .catch(() => setError("Failed to load audit events"))
      .finally(() => setLoading(false));
  };

  const searchEntity = () => {
    if (!entityId.trim()) return loadRecent();
    setLoading(true);
    auditApi
      .trail(entityId.trim())
      .then((r) => setRows(r.data))
      .catch(() => setError("No audit trail found for this entity"))
      .finally(() => setLoading(false));
  };

  const verifyChain = async () => {
    setChecking(true);
    try {
      const r = await auditApi.verify();
      setChainOk(r.data);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    loadRecent();
  }, []);

  const columns = [
    {
      key: "id",
      label: "#",
      render: (v) => (
        <span style={{ color: colors.muted, fontSize: "11px" }}>#{v}</span>
      ),
    },
    {
      key: "event_type",
      label: "Event",
      render: (v) => (
        <code
          style={{
            fontSize: "11px",
            background: "#1e2538",
            padding: "2px 6px",
            borderRadius: "4px",
            color: "#a5b4fc",
          }}
        >
          {v}
        </code>
      ),
    },
    {
      key: "entity_type",
      label: "Type",
      render: (v) => (
        <Badge
          status={v === "kyc" ? "pending" : v === "aml" ? "flagged" : "review"}
          label={v}
        />
      ),
    },
    { key: "entity_id", label: "Entity ID" },
    { key: "actor_id", label: "Actor" },
    {
      key: "this_hash",
      label: "Hash",
      render: (v) => (
        <code style={{ fontSize: "10px", color: colors.muted }}>
          {v?.slice(0, 12)}…
        </code>
      ),
    },
    {
      key: "created_at",
      label: "Timestamp",
      render: (v) => format(new Date(v), "dd MMM yyyy HH:mm:ss"),
    },
  ];

  return (
    <div>
      <SectionHeader
        title="Audit Log"
        subtitle="Immutable, hash-chained compliance event log"
        action={
          <Button
            size="sm"
            variant="ghost"
            onClick={verifyChain}
            disabled={checking}
          >
            {checking ? "Verifying…" : "🔐 Verify Chain"}
          </Button>
        }
      />

      {error && <Alert type="error" message={error} />}
      {chainOk && (
        <Alert
          type={chainOk.valid ? "success" : "error"}
          message={
            chainOk.valid
              ? `✓ Chain integrity verified - ${chainOk.checked} events checked, no tampering detected.`
              : `⚠ Chain integrity FAILED - ${chainOk.violations.length} violations detected! Evidence of tampering.`
          }
        />
      )}

      {/* Search */}
      <Card style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <Input
              label="Search by Entity ID (user_id, transaction_id, etc.)"
              placeholder="e.g. user_001 or txn_abc123"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchEntity()}
            />
          </div>
          <Button onClick={searchEntity} style={{ marginBottom: "12px" }}>
            Search
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              setEntityId("");
              loadRecent();
            }}
            style={{ marginBottom: "12px" }}
          >
            Clear
          </Button>
        </div>
      </Card>

      <Card>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "14px",
          }}
        >
          <span style={{ fontSize: "13px", color: colors.muted }}>
            {rows.length} events
          </span>
          <Button size="sm" variant="ghost" onClick={loadRecent}>
            ↻ Refresh
          </Button>
        </div>
        {loading ? <Spinner /> : <Table columns={columns} rows={rows} />}
      </Card>
    </div>
  );
}
