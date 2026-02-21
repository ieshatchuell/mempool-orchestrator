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
} from "lucide-react"

interface FeeAdvisory {
  id: string
  txid: string
  role: "Sender" | "Receiver"
  status: "Stuck" | "At Risk" | "Pending" | "Confirmed"
  currentFee: number
  action: string
  actionType: "RBF" | "CPFP" | "None"
  cost: number | null
}

const advisories: FeeAdvisory[] = [
  {
    id: "adv-001",
    txid: "4a8f...c3d1",
    role: "Sender",
    status: "Stuck",
    currentFee: 8,
    action: "RBF to 22.0 sat/vB",
    actionType: "RBF",
    cost: 4950,
  },
  {
    id: "adv-002",
    txid: "7b2e...9f41",
    role: "Receiver",
    status: "At Risk",
    currentFee: 4,
    action: "CPFP Child: 35.0 sat/vB",
    actionType: "CPFP",
    cost: 4935,
  },
  {
    id: "adv-003",
    txid: "f18e...2c87",
    role: "Sender",
    status: "Stuck",
    currentFee: 6,
    action: "RBF to 20.0 sat/vB",
    actionType: "RBF",
    cost: 4368,
  },
  {
    id: "adv-004",
    txid: "0c58...a1b7",
    role: "Receiver",
    status: "Pending",
    currentFee: 15,
    action: "Monitor only",
    actionType: "None",
    cost: null,
  },
  {
    id: "adv-005",
    txid: "e91c...a7f2",
    role: "Sender",
    status: "Confirmed",
    currentFee: 15,
    action: "No action needed",
    actionType: "None",
    cost: null,
  },
  {
    id: "adv-006",
    txid: "b67a...d9c5",
    role: "Sender",
    status: "At Risk",
    currentFee: 12,
    action: "RBF to 20.0 sat/vB",
    actionType: "RBF",
    cost: 5382,
  },
]

function RoleBadge({ role }: { role: FeeAdvisory["role"] }) {
  const styles =
    role === "Sender"
      ? "bg-info-soft text-info"
      : "bg-bitcoin-soft text-bitcoin"
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}
    >
      {role}
    </span>
  )
}

function StatusBadge({ status }: { status: FeeAdvisory["status"] }) {
  const styles = {
    Stuck: "bg-destructive/10 text-destructive",
    "At Risk": "bg-warning-soft text-warning",
    Pending: "bg-muted text-muted-foreground",
    Confirmed: "bg-success-soft text-success",
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  )
}

function ActionTypeBadge({ type }: { type: FeeAdvisory["actionType"] }) {
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

export function AdvisorsPanel() {
  const stuckCount = advisories.filter(
    (a) => a.status === "Stuck" || a.status === "At Risk"
  ).length

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
          {stuckCount > 0 && (
            <span className="flex items-center gap-1.5 rounded-lg bg-destructive/10 px-2 py-1 text-xs font-medium text-destructive">
              {stuckCount} need attention
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            {advisories.length} transactions
          </span>
        </div>
      </div>

      {/* Table */}
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
            {advisories.map((advisory) => (
              <TableRow
                key={advisory.id}
                className="border-border transition-colors hover:bg-muted/50"
              >
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      {advisory.txid}
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
                    {advisory.currentFee}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {" "}sat/vB
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <ActionTypeBadge type={advisory.actionType} />
                    <div className="flex items-center gap-1 text-sm text-foreground">
                      {advisory.actionType !== "None" && (
                        <ArrowRight className="h-3 w-3 text-bitcoin" />
                      )}
                      <span
                        className={
                          advisory.actionType !== "None"
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
                  {advisory.cost !== null ? (
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      {advisory.cost.toLocaleString()}
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
    </div>
  )
}
