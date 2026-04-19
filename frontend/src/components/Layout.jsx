import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Shield,
  Users,
  AlertTriangle,
  FileText,
  Webhook,
  Globe,
  Settings,
} from "lucide-react";
import { colors } from "./UI";

const NAV = [
  { to: "/", icon: Shield, label: "Dashboard" },
  { to: "/kyc", icon: Users, label: "KYC Queue" },
  { to: "/aml", icon: AlertTriangle, label: "AML Flags" },
  { to: "/audit", icon: FileText, label: "Audit Log" },
  { to: "/webhooks", icon: Webhook, label: "Webhooks" },
  { to: "/rules", icon: Globe, label: "Rules" },
];

export default function Layout({ children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: colors.bg }}>
      {/* Sidebar */}
      <aside
        style={{
          width: "220px",
          minWidth: "220px",
          background: colors.surface,
          borderRight: `1px solid ${colors.border}`,
          display: "flex",
          flexDirection: "column",
          padding: "0",
        }}
      >
        {/* Logo */}
        <div
          style={{
            padding: "24px 20px 20px",
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Shield size={18} color="#fff" />
            </div>
            <div>
              <div
                style={{ fontWeight: 700, fontSize: "15px", color: "#f1f5f9" }}
              >
                Clarium
              </div>
              <div style={{ fontSize: "11px", color: colors.muted }}>
                RegTech Platform
              </div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "12px 8px" }}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 12px",
                borderRadius: "8px",
                marginBottom: "2px",
                textDecoration: "none",
                fontSize: "13px",
                fontWeight: isActive ? 600 : 400,
                background: isActive ? "#6366f120" : "transparent",
                color: isActive ? "#818cf8" : colors.muted,
                transition: "all 0.15s",
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div
          style={{
            padding: "16px 20px",
            borderTop: `1px solid ${colors.border}`,
            fontSize: "11px",
            color: colors.muted,
          }}
        >
          v0.1.0 · {new Date().getFullYear()}
        </div>
      </aside>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          padding: "32px",
          overflowY: "auto",
          maxHeight: "100vh",
        }}
      >
        {children}
      </main>
    </div>
  );
}
