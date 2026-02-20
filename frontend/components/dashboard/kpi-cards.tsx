"use client"

import {
  Database,
  TrendingDown,
  Coins,
  Layers,
  ArrowUp,
  ArrowDown,
  Minus,
} from "lucide-react"

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

export function KpiCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="Mempool Size"
        value="142.8"
        unit="MB"
        delta="-12.4%"
        deltaDirection="down"
        icon={<Database className="h-4 w-4 text-info" />}
        iconBg="bg-info-soft"
      />
      <KpiCard
        label="Median Fee Rate"
        value="18.3"
        unit="sat/vB"
        delta="+3.1%"
        deltaDirection="up"
        icon={<TrendingDown className="h-4 w-4 text-bitcoin" />}
        iconBg="bg-bitcoin-soft"
      />
      <KpiCard
        label="Pending Fees"
        value="2.847"
        unit="BTC"
        delta="-8.2%"
        deltaDirection="down"
        icon={<Coins className="h-4 w-4 text-success" />}
        iconBg="bg-success-soft"
      />
      <KpiCard
        label="Blocks to Clear"
        value="~6"
        unit="blocks"
        delta="stable"
        deltaDirection="flat"
        icon={<Layers className="h-4 w-4 text-muted-foreground" />}
        iconBg="bg-muted"
      />
    </div>
  )
}
