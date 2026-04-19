import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import KYCPage from "./pages/KYCPage";
import AMLPage from "./pages/AMLPage";
import AuditPage from "./pages/AuditPage";
import WebhooksPage from "./pages/WebhooksPage";
import RulesPage from "./pages/RulesPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/kyc" element={<KYCPage />} />
        <Route path="/aml" element={<AMLPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/webhooks" element={<WebhooksPage />} />
        <Route path="/rules" element={<RulesPage />} />
      </Routes>
    </Layout>
  );
}
