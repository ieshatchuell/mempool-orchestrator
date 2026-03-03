"use client"

import { useState } from "react"
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
  AlertCircle,
  Trash2,
  Plus,
  Loader2,
} from "lucide-react"
import { useWatchlist, useAddWatchlistTx, useRemoveWatchlistTx } from "@/hooks/use-watchlist"
import type { WatchlistAdvisory, AdvisorAction } from "@/lib/types"

// ── Helpers ─────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const normalizedStatus = status.toLowerCase()
  let styles = "bg-muted text-muted-foreground"
  let label = status

  if (normalizedStatus === "stuck") {
    styles = "bg-destructive/10 text-destructive"
    label = "Stuck"
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

function AdvisorBadge({
  type,
  advisor,
}: {
  type: "RBF" | "CPFP"
  advisor: AdvisorAction | null
}) {
  if (!advisor) return <span className="text-xs text-muted-foreground">—</span>

  const typeStyles =
    type === "RBF"
      ? "bg-bitcoin-soft text-bitcoin"
      : "bg-info-soft text-info"

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${typeStyles}`}
        >
          {type}
        </span>
        <span className="text-xs text-foreground">{advisor.action}</span>
      </div>
      {advisor.cost_sats !== null && (
        <span className="pl-7 font-mono text-[11px] text-muted-foreground">
          {advisor.cost_sats.toLocaleString()} sats
        </span>
      )}
    </div>
  )
}

function truncateTxid(txid: string): string {
  if (txid.length <= 12) return txid
  return `${txid.slice(0, 6)}…${txid.slice(-6)}`
}

// ── Skeleton ────────────────────────────────────────────────────

function AdvisorsSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="h-4 w-24 rounded bg-muted animate-pulse" />
        <div className="h-4 w-32 rounded bg-muted animate-pulse" />
      </div>
      <div className="p-5">
        {Array.from({ length: 3 }).map((_, i) => (
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

// ── TXID Input ──────────────────────────────────────────────────

function TxidInput() {
  const [txid, setTxid] = useState("")
  const addMutation = useAddWatchlistTx()

  const isValid = /^[0-9a-fA-F]{64}$/.test(txid)

  function handleAdd() {
    if (!isValid) return
    addMutation.mutate(txid.toLowerCase(), {
      onSuccess: () => setTxid(""),
    })
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleAdd()
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={txid}
        onChange={(e) => setTxid(e.target.value.trim())}
        onKeyDown={handleKeyDown}
        placeholder="Paste TXID (64 hex chars)…"
        className="h-8 w-full max-w-xs rounded-lg border border-border bg-muted/50 px-3 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-bitcoin focus:outline-none focus:ring-1 focus:ring-bitcoin/30"
        maxLength={64}
      />
      <button
        onClick={handleAdd}
        disabled={!isValid || addMutation.isPending}
        className="flex h-8 items-center gap-1 rounded-lg bg-foreground px-3 text-xs font-medium text-primary-foreground transition-opacity disabled:opacity-40"
      >
        {addMutation.isPending ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Plus className="h-3 w-3" />
        )}
        Add
      </button>
    </div>
  )
}

// ── Delete Button ───────────────────────────────────────────────

function DeleteButton({ txid }: { txid: string }) {
  const removeMutation = useRemoveWatchlistTx()

  return (
    <button
      onClick={() => removeMutation.mutate(txid)}
      disabled={removeMutation.isPending}
      className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground/40 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
      aria-label={`Remove ${txid.slice(0, 8)}…`}
    >
      {removeMutation.isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Trash2 className="h-3.5 w-3.5" />
      )}
    </button>
  )
}

// ── Main Panel ──────────────────────────────────────────────────

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
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] animate-fade-in-up">
      {/* Panel Header */}
      <div className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Lightbulb className="h-4 w-4 text-bitcoin" />
          <h2 className="text-sm font-semibold text-foreground">
            Fee Advisors
          </h2>
          <div className="flex items-center gap-2">
            {stuck_count > 0 && (
              <span className="flex items-center gap-1.5 rounded-lg bg-destructive/10 px-2 py-1 text-xs font-medium text-destructive">
                {stuck_count} stuck
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              {total_count} tracked
            </span>
          </div>
        </div>
        <TxidInput />
      </div>

      {/* Table */}
      {advisories.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-muted-foreground">
          No tracked transactions. Paste a TXID above to start monitoring.
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
                  Status
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Fee Rate
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  RBF (Sender)
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  CPFP (Receiver)
                </TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {advisories.map((a: WatchlistAdvisory) => (
                <TableRow
                  key={a.txid}
                  className="border-border transition-colors hover:bg-muted/50"
                >
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-sm tabular-nums text-foreground">
                        {truncateTxid(a.txid)}
                      </span>
                      <a
                        href={`https://mempool.space/tx/${a.txid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground/40 transition-colors hover:text-muted-foreground"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={a.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      {a.current_fee_rate !== null
                        ? a.current_fee_rate.toFixed(1)
                        : "N/A"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {" "}sat/vB
                    </span>
                  </TableCell>
                  <TableCell>
                    <AdvisorBadge type="RBF" advisor={a.rbf} />
                  </TableCell>
                  <TableCell>
                    <AdvisorBadge type="CPFP" advisor={a.cpfp} />
                  </TableCell>
                  <TableCell>
                    <DeleteButton txid={a.txid} />
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
