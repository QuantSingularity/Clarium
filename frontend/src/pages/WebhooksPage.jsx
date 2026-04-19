import React, { useEffect, useState } from "react";
import { webhooks as wbApi } from "../api";
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

const EVENT_OPTIONS = [
  "*",
  "kyc.submitted",
  "kyc.verified",
  "kyc.rejected",
  "kyc.review",
  "aml.flagged",
  "aml.cleared",
];

export default function WebhooksPage() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ url: "", secret: "", events: ["*"] });
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    setLoading(true);
    wbApi
      .list()
      .then((r) => setList(r.data))
      .catch(() => setError("Failed to load webhooks"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const toggleEvent = (evt) => {
    if (evt === "*") {
      setForm((f) => ({ ...f, events: ["*"] }));
      return;
    }
    setForm((f) => {
      const evts = f.events.filter((e) => e !== "*");
      return {
        ...f,
        events: evts.includes(evt)
          ? evts.filter((e) => e !== evt)
          : [...evts, evt],
      };
    });
  };

  const handleCreate = async () => {
    if (!form.url) return;
    setSaving(true);
    try {
      await wbApi.create({
        url: form.url,
        secret: form.secret || null,
        events: form.events,
      });
      setForm({ url: "", secret: "", events: ["*"] });
      setShowForm(false);
      load();
    } catch (e) {
      setError(
        "Failed to create webhook: " + (e.response?.data?.detail || e.message),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this webhook?")) return;
    try {
      await wbApi.remove(id);
      load();
    } catch {
      setError("Failed to delete webhook");
    }
  };

  const columns = [
    { key: "id", label: "#" },
    {
      key: "url",
      label: "Endpoint URL",
      render: (v) => <code style={{ fontSize: "12px" }}>{v}</code>,
    },
    { key: "events", label: "Events", render: (v) => (v || []).join(", ") },
    {
      key: "is_active",
      label: "Active",
      render: (v) => (
        <Badge
          status={v ? "verified" : "rejected"}
          label={v ? "Active" : "Inactive"}
        />
      ),
    },
    {
      key: "created_at",
      label: "Created",
      render: (v) => format(new Date(v), "dd MMM yyyy"),
    },
    {
      key: "id",
      label: "",
      render: (v) => (
        <Button size="sm" variant="danger" onClick={() => handleDelete(v)}>
          Delete
        </Button>
      ),
    },
  ];

  return (
    <div>
      <SectionHeader
        title="Webhooks"
        subtitle="Register endpoints to receive real-time compliance events"
        action={
          <Button onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ Register Webhook"}
          </Button>
        }
      />

      {error && <Alert type="error" message={error} />}

      {showForm && (
        <Card style={{ marginBottom: "20px" }}>
          <h3
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "#f1f5f9",
              marginBottom: "16px",
            }}
          >
            New Webhook
          </h3>
          <Input
            label="Endpoint URL *"
            placeholder="https://yourapp.example.com/hooks/clarium"
            value={form.url}
            onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
          />
          <Input
            label="HMAC Secret (optional)"
            placeholder="Used to sign payloads with X-Clarium-Signature"
            value={form.secret}
            onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))}
          />
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
              Events to subscribe
            </label>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {EVENT_OPTIONS.map((evt) => (
                <Button
                  key={evt}
                  size="sm"
                  variant={form.events.includes(evt) ? "primary" : "ghost"}
                  onClick={() => toggleEvent(evt)}
                >
                  {evt}
                </Button>
              ))}
            </div>
          </div>
          <div
            style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}
          >
            <Button variant="ghost" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={!form.url || saving}>
              {saving ? "Saving…" : "Register"}
            </Button>
          </div>
        </Card>
      )}

      <Card>
        {loading ? <Spinner /> : <Table columns={columns} rows={list} />}
      </Card>
    </div>
  );
}
