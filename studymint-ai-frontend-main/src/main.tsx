import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./contexts/AuthContext";
import { DocumentStudioProvider } from "./contexts/DocumentStudioContext";
import { TenantProvider } from "./contexts/TenantContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <TenantProvider>
            <DocumentStudioProvider>
              <App />
            </DocumentStudioProvider>
          </TenantProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
