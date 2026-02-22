"use client"

import { useState, useEffect } from "react"
import { useTheme } from "next-themes"
import { Clock, Zap, Sun, Moon } from "lucide-react"
import { useOrchestratorStatus } from "@/hooks/use-orchestrator-status"

export function DashboardHeader() {
  const [mode, setMode] = useState<"PATIENT" | "RELIABLE">("PATIENT")
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const { data: status } = useOrchestratorStatus()

  useEffect(() => setMounted(true), [])

  const isDark = mounted && theme === "dark"

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

        {/* Center: Strategy Mode Toggle */}
        <div className="hidden items-center gap-3 md:flex">
          <span className="text-xs font-medium text-muted-foreground">
            Strategy
          </span>
          <div className="flex overflow-hidden rounded-xl border border-border bg-muted p-0.5">
            <button
              onClick={() => setMode("PATIENT")}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${mode === "PATIENT"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <Clock className="h-3.5 w-3.5" />
              Patient
            </button>
            <button
              onClick={() => setMode("RELIABLE")}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${mode === "RELIABLE"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <Zap className="h-3.5 w-3.5" />
              Reliable
            </button>
          </div>
          <p className="max-w-48 text-xs text-muted-foreground">
            {mode === "PATIENT"
              ? "Wait for low-fee windows"
              : "Prioritize confirmation speed"}
          </p>
        </div>

        {/* Right: Theme Toggle + Status */}
        <div className="flex items-center gap-4">
          {/* Theme Toggle (binary: Light/Dark) */}
          <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-muted transition-all hover:bg-card"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <Sun className="h-3.5 w-3.5 text-foreground" />
            ) : (
              <Moon className="h-3.5 w-3.5 text-foreground" />
            )}
          </button>

          <div className="hidden h-5 w-px bg-border sm:block" />

          {/* Connection Status */}
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            <span className="text-xs font-medium text-success">Connected</span>
          </div>
          <div className="hidden h-5 w-px bg-border sm:block" />
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
