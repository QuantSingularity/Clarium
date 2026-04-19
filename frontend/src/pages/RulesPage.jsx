import React, { useEffect, useState } from "react";
import { rules as rulesApi } from "../api";
import {
  Button,
  SectionHeader,
  Spinner,
  Alert,
  Card,
  colors,
} from "../components/UI";

export default function RulesPage() {
  const [jurisdictions, setJurisdictions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [ruleData, setRuleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    rulesApi
      .list()
      .then((r) => setJurisdictions(r.data.jurisdictions || []))
      .catch(() => setError("Failed to load jurisdictions"))
      .finally(() => setLoading(false));
  }, []);

  const selectJurisdiction = (code) => {
    setSelected(code);
    setRuleData(null);
    rulesApi
      .get(code)
      .then((r) => setRuleData(r.data))
      .catch(() => setError(`Failed to load rules for ${code}`));
  };

  const handleReload = async () => {
    setReloading(true);
    try {
      const r = await rulesApi.reload();
      setJurisdictions(r.data.jurisdictions || []);
      if (selected) selectJurisdiction(selected);
    } catch {
      setError("Failed to reload rules");
    } finally {
      setReloading(false);
    }
  };

  return (
    <div>
      <SectionHeader
        title="Jurisdiction Rules"
        subtitle="Per-country compliance rules: limits, disclosures, age gates, KYC tiers"
        action={
          <Button
            size="sm"
            variant="ghost"
            onClick={handleReload}
            disabled={reloading}
          >
            {reloading ? "Reloading…" : "↻ Hot-reload"}
          </Button>
        }
      />

      {error && <Alert type="error" message={error} />}

      <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
        {/* Jurisdiction list */}
        <Card style={{ width: "160px", minWidth: "160px" }}>
          <p
            style={{
              fontSize: "11px",
              color: colors.muted,
              fontWeight: 600,
              textTransform: "uppercase",
              marginBottom: "10px",
            }}
          >
            Jurisdictions
          </p>
          {loading ? (
            <Spinner />
          ) : (
            jurisdictions.map((code) => (
              <div
                key={code}
                onClick={() => selectJurisdiction(code)}
                style={{
                  padding: "8px 10px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: selected === code ? 700 : 400,
                  background: selected === code ? "#6366f120" : "transparent",
                  color: selected === code ? "#818cf8" : colors.text,
                  marginBottom: "2px",
                  transition: "all 0.1s",
                }}
              >
                🌍 {code}
              </div>
            ))
          )}
        </Card>

        {/* Rule detail */}
        <div style={{ flex: 1 }}>
          {!selected && (
            <Card>
              <p style={{ color: colors.muted, fontSize: "13px" }}>
                Select a jurisdiction to view its rules.
              </p>
            </Card>
          )}
          {selected && !ruleData && <Spinner />}
          {ruleData && (
            <div>
              <Card style={{ marginBottom: "16px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                  }}
                >
                  <h3
                    style={{
                      fontSize: "16px",
                      fontWeight: 700,
                      color: "#f1f5f9",
                    }}
                  >
                    {ruleData.jurisdiction}
                  </h3>
                  <div style={{ fontSize: "11px", color: colors.muted }}>
                    Effective: {ruleData.effective_date || "-"} · Updated:{" "}
                    {ruleData.last_updated || "-"}
                  </div>
                </div>
                <p style={{ fontSize: "12px", color: "#94a3b8" }}>
                  Authority: {ruleData.rules?.authority || "-"}
                </p>
              </Card>

              {/* Transaction limits */}
              {ruleData.rules?.transaction_limits && (
                <Card style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#f1f5f9",
                      marginBottom: "12px",
                    }}
                  >
                    Transaction Limits
                  </h4>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "8px",
                      fontSize: "13px",
                    }}
                  >
                    {Object.entries(ruleData.rules.transaction_limits).map(
                      ([k, v]) => (
                        <div
                          key={k}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            padding: "6px 10px",
                            background: "#0f1117",
                            borderRadius: "6px",
                          }}
                        >
                          <span style={{ color: colors.muted }}>
                            {k.replace(/_/g, " ")}
                          </span>
                          <span style={{ fontWeight: 600 }}>
                            {typeof v === "number" ? v.toLocaleString() : v}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </Card>
              )}

              {/* KYC tiers */}
              {ruleData.rules?.kyc_tiers && (
                <Card style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#f1f5f9",
                      marginBottom: "12px",
                    }}
                  >
                    KYC Tiers
                  </h4>
                  {ruleData.rules.kyc_tiers.map((tier, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px",
                        background: "#0f1117",
                        borderRadius: "8px",
                        marginBottom: "8px",
                        fontSize: "12px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "4px",
                        }}
                      >
                        <strong
                          style={{
                            color: "#a5b4fc",
                            textTransform: "capitalize",
                          }}
                        >
                          {tier.level}
                        </strong>
                        <span style={{ color: colors.muted }}>
                          ≥ {(tier.threshold || 0).toLocaleString()}
                        </span>
                      </div>
                      <div style={{ color: colors.muted }}>
                        {(tier.requirements || []).join(" · ")}
                      </div>
                    </div>
                  ))}
                </Card>
              )}

              {/* Disclosures */}
              {ruleData.rules?.required_disclosures?.length > 0 && (
                <Card>
                  <h4
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#f1f5f9",
                      marginBottom: "12px",
                    }}
                  >
                    Required Disclosures
                  </h4>
                  {ruleData.rules.required_disclosures.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        background: "#0c1a2e",
                        borderLeft: "3px solid #3b82f6",
                        borderRadius: "0 6px 6px 0",
                        marginBottom: "6px",
                        fontSize: "12px",
                        color: "#93c5fd",
                      }}
                    >
                      {d}
                    </div>
                  ))}
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
