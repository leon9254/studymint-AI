import type { ReactNode } from "react";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="app-shell-height overflow-hidden bg-[#f2f5f1] text-ink-950">
      <div className="flex h-full min-h-0 overflow-hidden">
        <Sidebar
          mobileOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <Topbar onOpenSidebar={() => setIsSidebarOpen(true)} />

          <main className="min-h-0 flex-1 overflow-y-auto overscroll-contain scroll-smooth">
            <div className="mx-auto w-full max-w-[1480px] px-3 py-3 sm:px-4 md:px-5 lg:px-8 lg:py-7">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
