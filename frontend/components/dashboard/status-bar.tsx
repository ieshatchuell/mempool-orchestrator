"use client"

import { useEffect, useState } from "react"
import { Activity, Gauge, AlertCircle } from "lucide-react"
import { useOrchestratorStatus } from "@/hooks/use-orchestrator-status"

export function StatusBar() {
  const [time, setTime] = useState("")
  const { data, isError } = useOrchestratorStatus()

  useEffect(() => {
    const update = () =>
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false }))
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  const emaFee = data?.ema_fee?.toFixed(1) ?? "—"
  const trafficLevel = data?.traffic_level ?? "—"
  const latestHeight = data?.latest_block_height?.toLocaleString() ?? "—"

  const trafficColor =
    trafficLevel === "HIGH"
      ? "text-destructive"
      : trafficLevel === "NORMAL"
        ? "text-foreground"
        : "text-success"

  // Show patient action in status bar as primary strategy indicator
  const patientAction = data?.patient?.action ?? "—"
  const reliableAction = data?.reliable?.action ?? "—"

  return (
    <footer className="border-t border-border bg-card px-6 py-3 lg:px-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="text-xs">Patient</span>
            <span className={`font-mono text-xs font-medium ${patientAction === "WAIT" ? "text-bitcoin" : "text-success"}`}>
              {patientAction}
            </span>
            <span className="mx-1 h-3 w-px bg-border" />
            <span className="text-xs">Reliable</span>
            <span className={`font-mono text-xs font-medium ${reliableAction === "WAIT" ? "text-bitcoin" : "text-success"}`}>
              {reliableAction}
            </span>
          </div>
          <div className="hidden items-center gap-1.5 text-muted-foreground sm:flex">
            <Activity className="h-3.5 w-3.5" />
            <span className="text-xs">EMA Fee</span>
            <span className="font-mono text-xs font-medium text-foreground">
              {emaFee}
              {data ? " sat/vB" : ""}
            </span>
          </div>
          <div className="hidden items-center gap-1.5 text-muted-foreground md:flex">
            <Gauge className="h-3.5 w-3.5" />
            <span className="text-xs">Traffic</span>
            <span className={`font-mono text-xs font-medium ${trafficColor}`}>
              {trafficLevel}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-5">
          {isError && (
            <div className="flex items-center gap-1 text-destructive">
              <AlertCircle className="h-3 w-3" />
              <span className="text-xs">API offline</span>
            </div>
          )}
          <div className="hidden items-center gap-1.5 text-muted-foreground sm:flex">
            <span className="text-xs">Block</span>
            <span className="font-mono text-xs font-medium text-foreground">
              #{latestHeight}
            </span>
          </div>
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            {time} UTC
          </span>
        </div>
      </div>
    </footer>
  )
}
