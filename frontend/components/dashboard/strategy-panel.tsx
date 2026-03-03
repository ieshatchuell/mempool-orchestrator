"use client"

import {
    Clock,
    Zap,
    TrendingUp,
    TrendingDown,
    Minus,
    AlertCircle,
} from "lucide-react"
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
} from "recharts"
import { useOrchestratorStatus } from "@/hooks/use-orchestrator-status"
import { useRecentBlocks } from "@/hooks/use-recent-blocks"
import type { StrategyResult } from "@/lib/types"

// ── Strategy Card ───────────────────────────────────────────────

function StrategyCard({
    label,
    icon,
    result,
    accent,
}: {
    label: string
    icon: React.ReactNode
    result: StrategyResult | undefined
    accent: string
}) {
    if (!result) {
        return (
            <div className="flex flex-1 flex-col gap-3 rounded-xl border border-border bg-card/50 p-4 animate-pulse">
                <div className="h-4 w-20 rounded bg-muted" />
                <div className="h-8 w-28 rounded bg-muted" />
                <div className="h-3 w-16 rounded bg-muted" />
            </div>
        )
    }

    const isWait = result.action === "WAIT"
    const actionColor = isWait
        ? "text-bitcoin"
        : "text-success"

    return (
        <div className={`flex flex-1 flex-col gap-2.5 rounded-xl border p-4 ${accent}`}>
            <div className="flex items-center gap-2">
                {icon}
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {label}
                </span>
            </div>
            <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-bold tracking-tight ${actionColor}`}>
                    {result.action}
                </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="font-mono">
                    {result.recommended_fee} <span className="opacity-60">sat/vB</span>
                </span>
                <span className="h-3 w-px bg-border" />
                <span>
                    {(result.confidence * 100).toFixed(0)}% confidence
                </span>
            </div>
        </div>
    )
}

// ── Fee Sparkline ───────────────────────────────────────────────

interface SparklinePoint {
    label: string
    fee: number
}

function FeeSparkline({ data }: { data: SparklinePoint[] }) {
    if (data.length === 0) {
        return (
            <div className="flex h-[120px] items-center justify-center text-xs text-muted-foreground">
                No block data yet
            </div>
        )
    }

    return (
        <ResponsiveContainer width="100%" height={120}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <XAxis
                    dataKey="label"
                    tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                    minTickGap={40}
                />
                <YAxis
                    tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    width={36}
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => v.toFixed(1)}
                />
                <Tooltip
                    contentStyle={{
                        backgroundColor: "var(--card)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                    }}
                    formatter={(value: number) => [`${value.toFixed(2)} sat/vB`, "Median Fee"]}
                    labelStyle={{ color: "var(--muted-foreground)" }}
                />
                <Line
                    type="monotone"
                    dataKey="fee"
                    stroke="var(--bitcoin)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3, fill: "var(--bitcoin)" }}
                />
            </LineChart>
        </ResponsiveContainer>
    )
}

// ── Trend Badge ─────────────────────────────────────────────────

function TrendBadge({ trend }: { trend: string }) {
    const Icon =
        trend === "RISING"
            ? TrendingUp
            : trend === "FALLING"
                ? TrendingDown
                : Minus

    const color =
        trend === "RISING"
            ? "text-destructive"
            : trend === "FALLING"
                ? "text-success"
                : "text-muted-foreground"

    return (
        <div className={`flex items-center gap-1 ${color}`}>
            <Icon className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">{trend}</span>
        </div>
    )
}

// ── Main Panel ──────────────────────────────────────────────────

export function StrategyPanel() {
    const { data: status, isError: statusError } = useOrchestratorStatus()
    const { data: blocksData } = useRecentBlocks(50)

    // Build sparkline data from recent blocks (oldest first for time axis)
    const sparklineData: SparklinePoint[] = (blocksData?.blocks ?? [])
        .slice()
        .reverse()
        .map((b) => ({
            label: `#${b.height.toString().slice(-4)}`,
            fee: b.median_fee,
        }))

    if (statusError) {
        return (
            <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>Unable to load strategy data</span>
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none animate-fade-in-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground">
                    Strategy &amp; Trend
                </h2>
                <div className="flex items-center gap-3">
                    {status && <TrendBadge trend={status.ema_trend} />}
                    {status && (
                        <span className="rounded-lg bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
                            EMA {status.ema_fee.toFixed(1)}
                        </span>
                    )}
                </div>
            </div>

            {/* Strategy Cards Row */}
            <div className="flex gap-3">
                <StrategyCard
                    label="Patient"
                    icon={<Clock className="h-4 w-4 text-info" />}
                    result={status?.patient}
                    accent="border-info/30 bg-info/5"
                />
                <StrategyCard
                    label="Reliable"
                    icon={<Zap className="h-4 w-4 text-bitcoin" />}
                    result={status?.reliable}
                    accent="border-bitcoin/30 bg-bitcoin/5"
                />
            </div>

            {/* Fee Sparkline */}
            <div>
                <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                        Median Fee Trend (last {sparklineData.length} blocks)
                    </span>
                    {status && (
                        <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                            Premium {status.fee_premium_pct > 0 ? "+" : ""}{status.fee_premium_pct.toFixed(1)}%
                        </span>
                    )}
                </div>
                <FeeSparkline data={sparklineData} />
            </div>
        </div>
    )
}
