import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { ReportsPage } from "./reports/ReportsPage";
import { AppStateProvider } from "./state/appStore";

// Minimal client-side route split, no router dependency (phase-2 execution
// plan §5.4): "/" = phase-1 dark workbench, "/reports" = phase-2 light
// report dashboard. FastAPI's SPA fallback (server.py) serves index.html for
// both paths already.
const isReportsRoute = window.location.pathname.startsWith("/reports");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isReportsRoute ? (
      <ReportsPage />
    ) : (
      <AppStateProvider>
        <App />
      </AppStateProvider>
    )}
  </React.StrictMode>,
);
