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
  CheckCircle2,
  Clock,
  ArrowUpDown,
  ExternalLink,
  Box,
  List,
} from "lucide-react"

// --- Recent Blocks Data ---
interface Block {
  height: number
  timestamp: string
  txCount: number
  size: string
  feeRange: string
  medianFee: string
  totalFees: string
  miner: string
}

const recentBlocks: Block[] = [
  {
    height: 881247,
    timestamp: "14:32:01",
    txCount: 3842,
    size: "1.98 MB",
    feeRange: "8 - 412",
    medianFee: "18.3",
    totalFees: "0.1847",
    miner: "Foundry USA",
  },
  {
    height: 881246,
    timestamp: "14:22:44",
    txCount: 2916,
    size: "1.74 MB",
    feeRange: "6 - 287",
    medianFee: "15.1",
    totalFees: "0.1324",
    miner: "AntPool",
  },
  {
    height: 881245,
    timestamp: "14:11:18",
    txCount: 4107,
    size: "1.99 MB",
    feeRange: "10 - 519",
    medianFee: "21.7",
    totalFees: "0.2103",
    miner: "F2Pool",
  },
  {
    height: 881244,
    timestamp: "14:02:55",
    txCount: 3241,
    size: "1.87 MB",
    feeRange: "7 - 345",
    medianFee: "16.8",
    totalFees: "0.1568",
    miner: "ViaBTC",
  },
  {
    height: 881243,
    timestamp: "13:49:12",
    txCount: 2694,
    size: "1.62 MB",
    feeRange: "5 - 198",
    medianFee: "12.4",
    totalFees: "0.0987",
    miner: "Foundry USA",
  },
  {
    height: 881242,
    timestamp: "13:41:37",
    txCount: 3578,
    size: "1.93 MB",
    feeRange: "9 - 401",
    medianFee: "19.6",
    totalFees: "0.1712",
    miner: "Binance Pool",
  },
]

// --- Pending Transactions Data ---
interface PendingTx {
  txid: string
  feeRate: number
  size: number
  value: string
  age: string
  status: "pending" | "rbf_signaled" | "low_fee"
  inputs: number
  outputs: number
}

const pendingTransactions: PendingTx[] = [
  {
    txid: "4a8f2c...c3d1",
    feeRate: 8,
    size: 225,
    value: "0.4521",
    age: "47 min",
    status: "low_fee",
    inputs: 1,
    outputs: 2,
  },
  {
    txid: "9e1b7a...f482",
    feeRate: 22,
    size: 141,
    value: "1.2000",
    age: "3 min",
    status: "pending",
    inputs: 1,
    outputs: 1,
  },
  {
    txid: "7b2e3f...9f41",
    feeRate: 4,
    size: 387,
    value: "0.0842",
    age: "1h 12m",
    status: "low_fee",
    inputs: 3,
    outputs: 2,
  },
  {
    txid: "d41f8c...7a29",
    feeRate: 35,
    size: 561,
    value: "5.7100",
    age: "< 1 min",
    status: "pending",
    inputs: 2,
    outputs: 12,
  },
  {
    txid: "a92c1e...b8f3",
    feeRate: 15,
    size: 448,
    value: "0.2210",
    age: "18 min",
    status: "rbf_signaled",
    inputs: 2,
    outputs: 3,
  },
  {
    txid: "c73d5b...e614",
    feeRate: 19,
    size: 226,
    value: "0.8340",
    age: "8 min",
    status: "pending",
    inputs: 1,
    outputs: 2,
  },
  {
    txid: "f18e4a...2c87",
    feeRate: 6,
    size: 312,
    value: "0.1105",
    age: "52 min",
    status: "low_fee",
    inputs: 2,
    outputs: 1,
  },
  {
    txid: "5c49d2...a1e8",
    feeRate: 42,
    size: 189,
    value: "3.1420",
    age: "< 1 min",
    status: "pending",
    inputs: 1,
    outputs: 2,
  },
  {
    txid: "b67a3e...d9c5",
    feeRate: 12,
    size: 673,
    value: "0.5678",
    age: "24 min",
    status: "rbf_signaled",
    inputs: 4,
    outputs: 5,
  },
  {
    txid: "8d2f1c...4b76",
    feeRate: 28,
    size: 254,
    value: "0.9800",
    age: "5 min",
    status: "pending",
    inputs: 1,
    outputs: 3,
  },
]

function StatusBadge({ status }: { status: PendingTx["status"] }) {
  const styles = {
    pending: "bg-muted text-muted-foreground",
    rbf_signaled: "bg-bitcoin-soft text-bitcoin",
    low_fee: "bg-destructive/10 text-destructive",
  }
  const labels = {
    pending: "Pending",
    rbf_signaled: "RBF Signaled",
    low_fee: "Low Fee",
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status === "pending" && <Clock className="h-3 w-3" />}
      {status === "rbf_signaled" && <ArrowUpDown className="h-3 w-3" />}
      {status === "low_fee" && <Clock className="h-3 w-3" />}
      {labels[status]}
    </span>
  )
}

function FeeRateCell({ rate }: { rate: number }) {
  let color = "text-foreground"
  if (rate < 10) color = "text-destructive"
  else if (rate < 18) color = "text-bitcoin"
  else color = "text-success"

  return (
    <span className={`font-mono text-sm tabular-nums ${color}`}>
      {rate}
    </span>
  )
}

export function TransactionsTable() {
  const [activeTab, setActiveTab] = useState<"blocks" | "pending">("blocks")

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
      {/* Table Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex overflow-hidden rounded-xl border border-border bg-muted p-0.5">
          <button
            onClick={() => setActiveTab("blocks")}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${
              activeTab === "blocks"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Box className="h-3.5 w-3.5" />
            Recent Blocks
          </button>
          <button
            onClick={() => setActiveTab("pending")}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${
              activeTab === "pending"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="h-3.5 w-3.5" />
            Pending TXs
          </button>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-xs text-muted-foreground">
            {activeTab === "blocks"
              ? `${recentBlocks.length} blocks`
              : `${pendingTransactions.length} transactions`}
          </span>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <span className="text-xs font-medium text-success">Live</span>
        </div>
      </div>

      {/* Blocks Table */}
      {activeTab === "blocks" && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Height
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Time
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Transactions
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Size
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Fee Range
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Median Fee
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Total Fees
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Miner
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentBlocks.map((block, i) => (
                <TableRow
                  key={block.height}
                  className="border-border transition-colors hover:bg-muted/50"
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                      <span className="font-mono text-sm font-medium tabular-nums text-foreground">
                        {block.height.toLocaleString()}
                      </span>
                      {i === 0 && (
                        <span className="rounded-full bg-success-soft px-2 py-0.5 text-[10px] font-semibold text-success">
                          Latest
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums text-muted-foreground">
                    {block.timestamp}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {block.txCount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {block.size}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
                    {block.feeRange}
                    <span className="text-muted-foreground/60"> sat/vB</span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-mono text-sm font-medium tabular-nums text-bitcoin">
                      {block.medianFee}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {" "}
                      sat/vB
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {block.totalFees}
                    <span className="text-muted-foreground"> BTC</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-foreground">
                        {block.miner}
                      </span>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/40 transition-colors hover:text-muted-foreground" />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pending Transactions Table */}
      {activeTab === "pending" && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-xs font-medium text-muted-foreground">
                  TXID
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Fee Rate
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  vSize
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Value
                </TableHead>
                <TableHead className="text-center text-xs font-medium text-muted-foreground">
                  In / Out
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Age
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pendingTransactions.map((tx) => (
                <TableRow
                  key={tx.txid}
                  className="border-border transition-colors hover:bg-muted/50"
                >
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-sm tabular-nums text-foreground">
                        {tx.txid}
                      </span>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/40 transition-colors hover:text-muted-foreground" />
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <FeeRateCell rate={tx.feeRate} />
                    <span className="text-xs text-muted-foreground">
                      {" "}
                      s/vB
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {tx.size}
                    <span className="text-muted-foreground"> vB</span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {tx.value}
                    <span className="text-muted-foreground"> BTC</span>
                  </TableCell>
                  <TableCell className="text-center font-mono text-sm tabular-nums text-muted-foreground">
                    {tx.inputs}
                    <span className="text-muted-foreground/40">{" / "}</span>
                    {tx.outputs}
                  </TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {tx.age}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={tx.status} />
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
