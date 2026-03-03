"use client"

import {
  Database,
  TrendingDown,
  Coins,
  Layers,
  ArrowUp,
  ArrowDown,
  Minus,
  AlertCircle,
} from "lucide-react"
import { useMempoolStats } from "@/hooks/use-mempool-stats"

interface KpiCardProps {
  label: string
  value: string
  unit: string
  delta: string
  deltaDirection: "up" | "down" | "flat"
  icon: React.ReactNode
  iconBg: string
}

function KpiCard({
  label,
  value,
  unit,
  delta,
  deltaDirection,
  icon,
  iconBg,
}: KpiCardProps) {
  const DeltaIcon =
    deltaDirection === "up"
      ? ArrowUp
      : deltaDirection === "down"
        ? ArrowDown
        : Minus

  const deltaColor =
    deltaDirection === "up"
      ? "text-destructive"
      : deltaDirection === "down"
        ? "text-success"
        : "text-muted-foreground"

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          {label}
        </span>
        <div className={`flex h-8 w-8 items-center justify-center rounded-xl ${iconBg}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-3xl font-semibold tabular-nums tracking-tight text-foreground">
          {value}
        </span>
        <span className="text-sm text-muted-foreground">{unit}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className={`flex items-center gap-0.5 ${deltaColor}`}>
          <DeltaIcon className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">{delta}</span>
        </div>
        <span className="text-xs text-muted-foreground">vs 1h ago</span>
      </div>
    </div>
  )
}

function KpiSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-24 rounded bg-muted" />
        <div className="h-8 w-8 rounded-xl bg-muted" />
      </div>
      <div className="h-9 w-20 rounded bg-muted" />
      <div className="h-4 w-16 rounded bg-muted" />
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)}`
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)}`
  return `${bytes}`
}

function formatBtc(sats: number): string {
  return (sats / 100_000_000).toFixed(3)
}

function getDeltaDirection(pct: number | null): "up" | "down" | "flat" {
  if (pct === null || pct === 0) return "flat"
  return pct > 0 ? "up" : "down"
}

function formatDelta(pct: number | null): string {
  if (pct === null) return "N/A"
  const sign = pct > 0 ? "+" : ""
  return `${sign}${pct.toFixed(1)}%`
}

export function KpiCards() {
  const { data, isError } = useMempoolStats()

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        <span>Unable to load mempool stats</span>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiSkeleton />
        <KpiSkeleton />
        <KpiSkeleton />
        <KpiSkeleton />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="animate-fade-in-up stagger-1 hover-lift">
        <KpiCard
          label="Mempool Size"
          value={formatBytes(data.mempool_bytes)}
          unit="MB"
          delta={formatDelta(data.delta_size_pct)}
          deltaDirection={getDeltaDirection(data.delta_size_pct)}
          icon={<Database className="h-4 w-4 text-info" />}
          iconBg="bg-info-soft"
        />
      </div>
      <div className="animate-fade-in-up stagger-2 hover-lift">
        <KpiCard
          label="Median Fee Rate"
          value={data.median_fee.toFixed(1)}
          unit="sat/vB"
          delta={formatDelta(data.delta_fee_pct)}
          deltaDirection={getDeltaDirection(data.delta_fee_pct)}
          icon={<TrendingDown className="h-4 w-4 text-bitcoin" />}
          iconBg="bg-bitcoin-soft"
        />
      </div>
      <div className="animate-fade-in-up stagger-3 hover-lift">
        <KpiCard
          label="Pending Fees"
          value={formatBtc(data.total_fee_sats)}
          unit="BTC"
          delta={formatDelta(data.delta_total_fee_pct)}
          deltaDirection={getDeltaDirection(data.delta_total_fee_pct)}
          icon={<Coins className="h-4 w-4 text-success" />}
          iconBg="bg-success-soft"
        />
      </div>
      <div className="animate-fade-in-up stagger-4 hover-lift">
        <KpiCard
          label="Blocks to Clear"
          value={`~${data.blocks_to_clear}`}
          unit="blocks"
          delta={formatDelta(data.delta_blocks_pct)}
          deltaDirection={getDeltaDirection(data.delta_blocks_pct)}
          icon={<Layers className="h-4 w-4 text-muted-foreground" />}
          iconBg="bg-muted"
        />
      </div>
    </div>
  )
}
