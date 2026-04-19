import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { admin } from "../api";
import { Card, StatCard, Spinner, Alert, colors } from "../components/UI";

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#3b82f6"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    admin
      .stats()
      .then((r) => setStats(r.data))
      .catch(() =>
        setError("Could not load dashboard stats. Is the API running?"),
      );
  }, []);

  if (error) return <Alert type="error" message={error} />;
  if (!stats) return <Spinner />;

  const kycChartData = Object.entries(stats.kyc.by_status || {}).map(
    ([k, v]) => ({ name: k, count: v }),
  );

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#f1f5f9" }}>
          Dashboard
        </h1>
        <p style={{ color: colors.muted, fontSize: "13px", marginTop: "4px" }}>
          {new Date().toLocaleDateString("en-GB", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
      </div>

      {/* KYC stat row */}
      <div style={{ marginBottom: "12px" }}>
        <p
          style={{
            fontSize: "11px",
            fontWeight: 600,
            color: colors.muted,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "10px",
          }}
        >
          KYC
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <StatCard
            label="Total Submissions"
            value={stats.kyc.total}
            color={colors.accent}
          />
          <StatCard label="Pending" value={stats.kyc.pending} color="#60a5fa" />
          <StatCard
            label="In Review"
            value={stats.kyc.review}
            color={colors.yellow}
          />
          <StatCard
            label="Verified"
            value={stats.kyc.verified}
            color={colors.green}
          />
          <StatCard
            label="Rejected"
            value={stats.kyc.rejected}
            color={colors.red}
          />
        </div>
      </div>

      {/* AML + audit row */}
      <div style={{ marginBottom: "24px" }}>
        <p
          style={{
            fontSize: "11px",
            fontWeight: 600,
            color: colors.muted,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "10px",
          }}
        >
          AML & Audit
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <StatCard
            label="AML Checks Total"
            value={stats.aml.total}
            color={colors.accent}
          />
          <StatCard
            label="Flagged"
            value={stats.aml.flagged}
            color={colors.red}
          />
          <StatCard
            label="PEP Matches"
            value={stats.aml.pep_matches}
            color="#c084fc"
          />
          <StatCard
            label="Audit Events (24h)"
            value={stats.audit.events_last_24h}
            color={colors.blue}
          />
        </div>
      </div>

      {/* KYC by status chart */}
      <Card>
        <h3
          style={{
            fontSize: "14px",
            fontWeight: 600,
            color: "#f1f5f9",
            marginBottom: "16px",
          }}
        >
          KYC Status Breakdown
        </h3>
        {kycChartData.length === 0 ? (
          <p style={{ color: colors.muted, fontSize: "13px" }}>
            No KYC data yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={kycChartData}
              margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
            >
              <XAxis
                dataKey="name"
                tick={{ fill: colors.muted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: colors.muted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1f2e",
                  border: "1px solid #2a3248",
                  borderRadius: "8px",
                  color: "#e2e8f0",
                  fontSize: 12,
                }}
                cursor={{ fill: "#2a324820" }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {kycChartData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    </div>
  );
}
