"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Lightbulb,
  ExternalLink,
  ArrowRight,
  AlertCircle,
} from "lucide-react"
import { useWatchlist } from "@/hooks/use-watchlist"
import type { WatchlistAdvisory } from "@/lib/types"

function RoleBadge({ role }: { role: string }) {
  const styles =
    role === "SENDER"
      ? "bg-info-soft text-info"
      : "bg-bitcoin-soft text-bitcoin"
  const label = role === "SENDER" ? "Sender" : "Receiver"
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}
    >
      {label}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const normalizedStatus = status.toLowerCase()
  let styles = "bg-muted text-muted-foreground"
  let label = status

  if (normalizedStatus === "stuck") {
    styles = "bg-destructive/10 text-destructive"
    label = "Stuck"
  } else if (normalizedStatus === "at risk") {
    styles = "bg-warning-soft text-warning"
    label = "At Risk"
  } else if (normalizedStatus === "confirmed") {
    styles = "bg-success-soft text-success"
    label = "Confirmed"
  } else if (normalizedStatus === "pending") {
    styles = "bg-muted text-muted-foreground"
    label = "Pending"
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}
    >
      {label}
    </span>
  )
}

function ActionTypeBadge({ type }: { type: string }) {
  if (type === "None") return null
  const styles =
    type === "RBF"
      ? "bg-bitcoin-soft text-bitcoin"
      : "bg-info-soft text-info"
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${styles}`}
    >
      {type}
    </span>
  )
}

function truncateTxid(txid: string): string {
  if (txid.length <= 12) return txid
  return `${txid.slice(0, 4)}...${txid.slice(-4)}`
}

function AdvisorsSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="h-4 w-24 rounded bg-muted animate-pulse" />
        <div className="h-4 w-32 rounded bg-muted animate-pulse" />
      </div>
      <div className="p-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex gap-4 py-3">
            <div className="h-4 w-20 rounded bg-muted animate-pulse" />
            <div className="h-4 w-16 rounded bg-muted animate-pulse" />
            <div className="h-4 flex-1 rounded bg-muted animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function AdvisorsPanel() {
  const { data, isError } = useWatchlist()

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        <span>Unable to load fee advisors</span>
      </div>
    )
  }

  if (!data) return <AdvisorsSkeleton />

  const { advisories, stuck_count, total_count } = data

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Lightbulb className="h-4 w-4 text-bitcoin" />
          <h2 className="text-sm font-semibold text-foreground">
            Fee Advisors
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {stuck_count > 0 && (
            <span className="flex items-center gap-1.5 rounded-lg bg-destructive/10 px-2 py-1 text-xs font-medium text-destructive">
              {stuck_count} need attention
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            {total_count} transactions
          </span>
        </div>
      </div>

      {/* Table */}
      {advisories.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-muted-foreground">
          No tracked transactions. Add TXIDs to your watchlist to see advisories.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-xs font-medium text-muted-foreground">
                  TXID
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Role
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Current Fee
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Recommended Action
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Cost
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {advisories.map((advisory: WatchlistAdvisory) => (
                <TableRow
                  key={advisory.txid}
                  className="border-border transition-colors hover:bg-muted/50"
                >
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-sm tabular-nums text-foreground">
                        {truncateTxid(advisory.txid)}
                      </span>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/40 transition-colors hover:text-muted-foreground" />
                    </div>
                  </TableCell>
                  <TableCell>
                    <RoleBadge role={advisory.role} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={advisory.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      {advisory.current_fee_rate !== null
                        ? advisory.current_fee_rate.toFixed(1)
                        : "N/A"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {" "}sat/vB
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <ActionTypeBadge type={advisory.action_type} />
                      <div className="flex items-center gap-1 text-sm text-foreground">
                        {advisory.action_type !== "None" && (
                          <ArrowRight className="h-3 w-3 text-bitcoin" />
                        )}
                        <span
                          className={
                            advisory.action_type !== "None"
                              ? "font-medium"
                              : "text-muted-foreground"
                          }
                        >
                          {advisory.action}
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {advisory.cost_sats !== null ? (
                      <span className="font-mono text-sm tabular-nums text-foreground">
                        {advisory.cost_sats.toLocaleString()}
                        <span className="text-xs text-muted-foreground">
                          {" "}sats
                        </span>
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">--</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
