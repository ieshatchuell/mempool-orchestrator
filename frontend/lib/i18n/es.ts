/**
 * Spanish dictionary — must match the shape of `en.ts` exactly.
 *
 * Uses `satisfies Dictionary` to guarantee structural parity
 * with the English source of truth at compile time.
 */

import type { Dictionary } from "./en";

export const es = {
  header: {
    title: "Mempool Orchestrator",
    subtitle: "Inteligencia de comisiones en tiempo real",
    connected: "Conectado",
    disconnected: "Desconectado",
    block: "Bloque",
    toggleTheme: "Cambiar tema",
  },
  sections: {
    liveMarket: "Dinámica del Mercado en Vivo",
    settlementHistory: "Historial de Liquidaciones",
  },
  kpi: {
    mempoolSize: "Tamaño del Mempool",
    medianFeeRate: "Comisión Mediana",
    pendingFees: "Comisiones Pendientes",
    blocksToClear: "Bloques para Vaciar",
    unableToLoad: "No se pudieron cargar las estadísticas del mempool",
    vsOneHourAgo: "vs hace 1h",
    tooltipMempoolSize:
      "Tamaño total de todas las transacciones sin confirmar esperando ser incluidas en un bloque. Mayor = más congestión.",
    tooltipMedianFee:
      "La comisión mediana (sat/vB) que las transacciones en el mempool están pagando. Es la 'tarifa vigente' para ser confirmado.",
    tooltipPendingFees:
      "Total de BTC en comisiones de todas las transacciones sin confirmar. Representa el incentivo económico para los mineros.",
    tooltipBlocksToClear:
      "Número estimado de bloques necesarios para confirmar todas las transacciones actuales del mempool a las tasas de comisión actuales.",
  },
  advisors: {
    title: "Asesores de Comisiones",
    liveScanning: "Escaneo en Vivo",
    stuck: "atascadas",
    tracked: "rastreadas",
    noStuckTx:
      "No se detectaron transacciones atascadas. El escáner está monitoreando el mempool.",
    unableToLoad: "No se pudieron cargar los asesores de comisiones",
    tooltipAdvisors:
      "Escáner automatizado que detecta transacciones atascadas en el mempool y calcula las comisiones óptimas de RBF (Replace-By-Fee) o CPFP (Child-Pays-For-Parent).",
    colTxid: "TXID",
    colStatus: "Estado",
    colFeeRate: "Comisión",
    colRbf: "RBF (Emisor)",
    colCpfp: "CPFP (Receptor)",
    statusStuck: "Atascada",
    statusConfirmed: "Confirmada",
    statusPending: "Pendiente",
    rbfAction: "Reemplazar con {fee} sat/vB",
    cpfpAction: "Hijo paga para alcanzar {fee} sat/vB",
  },
  strategy: {
    title: "Estrategia y Tendencia",
    patient: "Paciente",
    fast: "Rápida",
    confidence: "confianza",
    medianFeeTrend: "Tendencia de Comisión Mediana (últimos {count} bloques)",
    premium: "Prima",
    noBlockData: "Sin datos de bloques aún",
    unableToLoad: "No se pudieron cargar los datos de estrategia",
    tooltipStrategy:
      "Motor de lógica en tiempo real. Compara las comisiones actuales vs. el historial de 100 bloques. El modo 'Paciente' sugiere esperar durante picos; el modo 'Rápida' prioriza la velocidad de confirmación.",
    medianFee: "Comisión Mediana",
    actionWait: "ESPERAR",
    actionBroadcast: "ENVIAR",
    trendStable: "ESTABLE",
    trendRising: "AL ALZA",
    trendFalling: "A LA BAJA",
  },
  feeHistogram: {
    title: "Distribución de Comisiones",
    unableToLoad: "No se pudo cargar la distribución de comisiones",
    noData: "Sin datos de distribución de comisiones disponibles",
    block: "Bloque",
    tooltipFeeDistribution:
      'Distribución de comisiones en 7 bandas percentiles para el último bloque confirmado. La barra roja "Max" muestra la comisión más alta pagada — útil para detectar picos.',
    legendCheap: "Barata",
    legendMedian: "Mediana",
    legendPremium: "Premium",
  },
  blockWeight: {
    title: "Peso del Bloque",
    unableToLoad: "No se pudieron cargar los datos de bloques",
    noData: "Sin datos de bloques disponibles",
    tooltipBlockWeight:
      "Comparación visual de los tamaños de bloques recientes vs. el límite de 4MB SegWit. Bloques con más del 90% de capacidad indican alta demanda de red.",
    fullnessFull: "Lleno",
    fullnessHeavy: "Pesado",
    fullnessNormal: "Normal",
    fullnessLight: "Ligero",
    unknown: "Desconocido",
  },
  transactions: {
    recentBlocks: "Bloques Recientes",
    live: "En Vivo",
    blocks: "bloques",
    noBlocks: "Sin bloques confirmados aún. Esperando datos...",
    latest: "Último",
    unableToLoad: "No se pudieron cargar los bloques recientes",
    tooltipRecentBlocks:
      "Registro inmutable de los últimos 10 bloques confirmados. Muestra el 'precio de liquidación' realizado (comisión mediana) y el rango exacto de comisiones incluidas por los mineros.",
    colHeight: "Altura",
    colTime: "Hora",
    colTransactions: "Transacciones",
    colSize: "Tamaño",
    colFeeRange: "Rango de Comisión",
    colMedianFee: "Comisión Mediana",
    colTotalFees: "Comisiones Totales",
    colMiner: "Minero",
  },
  statusBar: {
    patient: "Paciente",
    fast: "Rápida",
    emaFee: "Comisión EMA",
    traffic: "Tráfico",
    apiOffline: "API fuera de línea",
    block: "Bloque",
    trafficLow: "BAJO",
    trafficNormal: "NORMAL",
    trafficHigh: "ALTO",
  },
  language: {
    toggle: "EN/ES",
  },
} as const satisfies Dictionary;
