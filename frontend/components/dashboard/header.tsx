"use client"

import { useState, useEffect } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon } from "lucide-react"
import { useOrchestratorStatus } from "@/hooks/use-orchestrator-status"

export function DashboardHeader() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const { data: status, isError } = useOrchestratorStatus()

  useEffect(() => setMounted(true), [])

  const isDark = mounted && theme === "dark"
  const isConnected = !isError && !!status

  return (
    <header className="border-b border-border bg-card px-6 py-4 lg:px-10">
      <div className="flex items-center justify-between">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-foreground">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-primary-foreground"
            >
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
            </svg>
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-foreground">
              Mempool Orchestrator
            </h1>
            <p className="text-xs text-muted-foreground">
              Real-time fee intelligence
            </p>
          </div>
        </div>

        {/* Right: Theme Switch + Connection Status + Block Height */}
        <div className="flex items-center gap-4">
          {/* Theme Switch (binary Dark/Light) */}
          <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="relative flex h-7 w-12 items-center rounded-full border border-border bg-muted p-0.5 transition-colors"
            aria-label="Toggle theme"
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full bg-card shadow-sm transition-transform duration-200 ${isDark ? "translate-x-5" : "translate-x-0"
                }`}
            >
              {isDark ? (
                <Moon className="h-3 w-3 text-foreground" />
              ) : (
                <Sun className="h-3 w-3 text-foreground" />
              )}
            </span>
          </button>

          <div className="hidden h-5 w-px bg-border sm:block" />

          {/* Connection Status (driven by useOrchestratorStatus isError) */}
          <div className="flex items-center gap-1.5">
            {isConnected ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                </span>
                <span className="text-xs font-medium text-success">Connected</span>
              </>
            ) : (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-destructive" />
                </span>
                <span className="text-xs font-medium text-destructive">Disconnected</span>
              </>
            )}
          </div>

          <div className="hidden h-5 w-px bg-border sm:block" />

          {/* Block Height */}
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="text-xs text-muted-foreground">Block</span>
            <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
              {status?.latest_block_height?.toLocaleString() ?? "—"}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
