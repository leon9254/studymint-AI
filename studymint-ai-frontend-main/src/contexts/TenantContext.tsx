import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import type { Tenant } from "../types";
import { useAuth } from "./AuthContext";

interface TenantContextValue {
  tenant: Tenant | null;
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

export function TenantProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  const value = useMemo<TenantContextValue>(
    () => ({
      tenant: user
        ? {
            id: user.tenant_id,
            name: "Mint Learning Studio",
            slug: "mint-learning-studio",
            plan: "Pro"
          }
        : null
    }),
    [user]
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error("useTenant must be used within TenantProvider");
  }
  return context;
}
