/**
 * English dictionary — source of truth for all Dashboard UI strings.
 *
 * The `Dictionary` type is exported from this file and reused
 * by all locale files to guarantee structural parity.
 */

export const en = {
  header: {
    title: "Mempool Orchestrator",
    subtitle: "Real-time fee intelligence",
    connected: "Connected",
    disconnected: "Disconnected",
    block: "Block",
    toggleTheme: "Toggle theme",
  },
  sections: {
    liveMarket: "Live Market Dynamics",
    settlementHistory: "Settlement History",
  },
  kpi: {
    mempoolSize: "Mempool Size",
    medianFeeRate: "Median Fee Rate",
    pendingFees: "Pending Fees",
    blocksToClear: "Blocks to Clear",
    unableToLoad: "Unable to load mempool stats",
    vsOneHourAgo: "vs 1h ago",
    tooltipMempoolSize:
      "Total size of all unconfirmed transactions waiting to be included in a block. Higher = more congestion.",
    tooltipMedianFee:
      "The median fee rate (sat/vB) that transactions in the mempool are paying. This is the 'going rate' to get confirmed.",
    tooltipPendingFees:
      "Total BTC in fees across all unconfirmed transactions. Represents the economic incentive for miners.",
    tooltipBlocksToClear:
      "Estimated number of blocks needed to confirm all current mempool transactions at current fee rates.",
  },
  advisors: {
    title: "Fee Advisors",
    liveScanning: "Live Scanning",
    stuck: "stuck",
    tracked: "tracked",
    noStuckTx:
      "No stuck transactions detected. The scanner is monitoring the mempool.",
    unableToLoad: "Unable to load fee advisors",
    tooltipAdvisors:
      "Automated scanner that detects transactions stuck in the mempool and calculates optimal RBF (Replace-By-Fee) or CPFP (Child-Pays-For-Parent) top-up fees.",
    colTxid: "TXID",
    colStatus: "Status",
    colFeeRate: "Fee Rate",
    colRbf: "RBF (Sender)",
    colCpfp: "CPFP (Receiver)",
    statusStuck: "Stuck",
    statusConfirmed: "Confirmed",
    statusPending: "Pending",
    rbfAction: "Replace with {fee} sat/vB",
    cpfpAction: "Child pays to reach {fee} sat/vB",
  },
  strategy: {
    title: "Strategy & Trend",
    patient: "Patient",
    fast: "Fast",
    confidence: "confidence",
    medianFeeTrend: "Median Fee Trend (last {count} blocks)",
    premium: "Premium",
    noBlockData: "No block data yet",
    unableToLoad: "Unable to load strategy data",
    tooltipStrategy:
      "Real-time logic engine. Compares current fees vs. 100-block history. 'Patient' mode suggests waiting during spikes; 'Fast' mode prioritizes confirmation speed.",
    medianFee: "Median Fee",
    actionWait: "WAIT",
    actionBroadcast: "BROADCAST",
    trendStable: "STABLE",
    trendRising: "RISING",
    trendFalling: "FALLING",
  },
  feeHistogram: {
    title: "Fee Distribution",
    unableToLoad: "Unable to load fee distribution",
    noData: "No fee distribution data available",
    block: "Block",
    tooltipFeeDistribution:
      'Fee distribution across 7 percentile bands for the latest confirmed block. The red "Max" bar shows the highest fee paid — useful for detecting fee spikes.',
    legendCheap: "Cheap",
    legendMedian: "Median",
    legendPremium: "Premium",
  },
  blockWeight: {
    title: "Block Weight",
    unableToLoad: "Unable to load block data",
    noData: "No block data available",
    tooltipBlockWeight:
      "Visual comparison of recent block sizes vs the 4MB SegWit limit. Blocks over 90% capacity indicate high network demand. Pool badges show which mining pool found each block.",
    fullnessFull: "Full",
    fullnessHeavy: "Heavy",
    fullnessNormal: "Normal",
    fullnessLight: "Light",
    unknown: "Unknown",
  },
  transactions: {
    recentBlocks: "Recent Blocks",
    live: "Live",
    blocks: "blocks",
    noBlocks: "No confirmed blocks yet. Waiting for data...",
    latest: "Latest",
    unableToLoad: "Unable to load recent blocks",
    tooltipRecentBlocks:
      "Immutable ledger of the last 10 confirmed blocks. Shows the realized 'clearing price' (median fee) and the exact fee range of transactions included by miners.",
    colHeight: "Height",
    colTime: "Time",
    colTransactions: "Transactions",
    colSize: "Size",
    colFeeRange: "Fee Range",
    colMedianFee: "Median Fee",
    colTotalFees: "Total Fees",
    colMiner: "Miner",
  },
  statusBar: {
    patient: "Patient",
    fast: "Fast",
    emaFee: "EMA Fee",
    traffic: "Traffic",
    apiOffline: "API offline",
    block: "Block",
    trafficLow: "LOW",
    trafficNormal: "NORMAL",
    trafficHigh: "HIGH",
  },
  language: {
    toggle: "EN/ES",
  },
} as const;

/** Recursively widen all string literals to `string` so locale files can use different values. */
type DeepStringify<T> = {
  [K in keyof T]: T[K] extends string ? string : DeepStringify<T[K]>;
};

export type Dictionary = DeepStringify<typeof en>;
