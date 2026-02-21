"use client"

import { useEffect, useState } from "react"
import { Wifi, Activity, Gauge } from "lucide-react"

export function StatusBar() {
  const [time, setTime] = useState("")

  useEffect(() => {
    const update = () =>
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false }))
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <footer className="border-t border-border bg-card px-6 py-3 lg:px-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Wifi className="h-3.5 w-3.5" />
            <span className="text-xs">WebSocket</span>
            <span className="font-mono text-xs font-medium text-success">
              12ms
            </span>
          </div>
          <div className="hidden items-center gap-1.5 text-muted-foreground sm:flex">
            <Activity className="h-3.5 w-3.5" />
            <span className="text-xs">API</span>
            <span className="font-mono text-xs font-medium text-foreground">
              847/min
            </span>
          </div>
        </div>
        <div className="flex items-center gap-5">
          <div className="hidden items-center gap-1.5 text-muted-foreground sm:flex">
            <Gauge className="h-3.5 w-3.5" />
            <span className="text-xs">Memory</span>
            <span className="font-mono text-xs font-medium text-foreground">
              124 MB
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
