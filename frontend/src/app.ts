import type { IChartApi, ISeriesApi } from "lightweight-charts";
import { 
  candleOHLCVtoAreaData,
  candleOHLCVtoCandlestickData,
} from "./chartAdapters";
import {
  createChartContainer,
  addCandlestickSeries,
  addLineSeries,
  linePoint,
  addAreaSeries,
} from "./chart";
import { API_BASE, yfinanceUrl, smaUrl, wsStreamUrl } from "./config";
import type { OHLCVCandle } from "./types";
import { WSClient } from "./ws";
import type { ConnectionStatus } from "./ws";

type DataSource = "yfinance" | "csv";

export function initApp(): void {
  const header = document.createElement("div");
  header.className = "header";

  const symbolInput = document.createElement("input");
  symbolInput.type = "text";
  symbolInput.placeholder = "Symbol (e.g. AAPL)";
  symbolInput.value = "AAPL";

  const timeframeSelect = document.createElement("select");
  timeframeSelect.innerHTML = `
    <option value="1d">1D</option>
    <option value="5d">5D</option>
    <option value="1mo" selected>1M</option>
    <option value="3mo">3M</option>
    <option value="6mo">6M</option>
    <option value="1y">1Y</option>
  `;

  const intervalSelect = document.createElement("select");
  intervalSelect.innerHTML = `
    <option value="1d" selected>1d</option>
    <option value="1h">1h</option>
    <option value="5m">5m</option>
  `;

  const sourceSelect = document.createElement("select");
  sourceSelect.id = "source";
  sourceSelect.innerHTML = `
    <option value="yfinance">yfinance</option>
    <option value="csv">CSV</option>
  `;

  const loadBtn = document.createElement("button");
  loadBtn.textContent = "Load";

  const streamBtn = document.createElement("button");
  streamBtn.textContent = "Stream WS";
  streamBtn.className = "secondary";

  const smaBtn = document.createElement("button");
  smaBtn.textContent = "SMA(20)";
  smaBtn.className = "secondary";

  const refreshLabel = document.createElement("label");
  refreshLabel.style.display = "inline-flex";
  refreshLabel.style.alignItems = "center";
  refreshLabel.style.gap = "0.35rem";
  refreshLabel.style.fontSize = "0.9rem";
  refreshLabel.style.color = "var(--text-muted)";
  const refreshCheck = document.createElement("input");
  refreshCheck.type = "checkbox";
  refreshCheck.title = "Re-fetch yfinance every 60s when using yfinance";
  refreshLabel.append(refreshCheck, document.createTextNode("Auto-refresh 60s"));

  const csvWrap = document.createElement("div");
  csvWrap.className = "file-input-wrap";
  csvWrap.style.display = "none";
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = ".csv";
  const fileLabel = document.createElement("span");
  fileLabel.className = "file-label";
  fileLabel.textContent = "Choose CSV";
  csvWrap.append(fileInput, fileLabel);

  const statusEl = document.createElement("span");
  statusEl.className = "status";
  const statusDot = document.createElement("span");
  statusDot.className = "status-dot";
  statusEl.append(statusDot, document.createTextNode("Disconnected"));

  const chartContainer = document.createElement("div");
  chartContainer.className = "chart-container";

  const errorEl = document.createElement("div");
  errorEl.className = "error-message";
  errorEl.style.display = "none";

  header.append(
    symbolInput,
    timeframeSelect,
    intervalSelect,
    sourceSelect,
    csvWrap,
    loadBtn,
    streamBtn,
    smaBtn,
    refreshLabel,
    statusEl
  );

  document.getElementById("app")!.append(header, errorEl, chartContainer);

  let chart: IChartApi | null = null;
  let candleSeries: ISeriesApi<"Candlestick"> | null = null;
  let areaSeries: ISeriesApi<"Area"> | null = null;
  let smaSeries: ISeriesApi<"Line"> | null = null;
  let wsClient: WSClient | null = null;
  let lastCandles: OHLCVCandle[] = [];
  let refreshIntervalId: ReturnType<typeof setInterval> | null = null;

  function setError(msg: string | null): void {
    errorEl.textContent = msg ?? "";
    errorEl.style.display = msg ? "block" : "none";
  }

  function setStatus(status: ConnectionStatus): void {
    statusDot.className = "status-dot " + (status === "connected" ? "connected" : status === "error" ? "error" : "");
    const labels: Record<ConnectionStatus, string> = {
      connecting: "Connecting…",
      connected: "Connected",
      disconnected: "Disconnected",
      error: "Error",
    };
    statusEl.childNodes[1].textContent = labels[status];
  }

  function getPeriodInterval(): { period: string; interval: string } {
    const period = (timeframeSelect as HTMLSelectElement).value;
    const interval = (intervalSelect as HTMLSelectElement).value;
    return { period, interval };
  }

  function renderChart(candles: OHLCVCandle[], smaValues?: (number | null)[]): void {
    if (!chart) {
      chart = createChartContainer(chartContainer);
      areaSeries = addAreaSeries(chart);
      candleSeries = addCandlestickSeries(chart);
    }

    if (candles.length >= 20) {
        areaSeries!.setData(candles.map(candleOHLCVtoAreaData));
    } else {
        areaSeries!.setData([]);
    }

    candleSeries!.setData(candles.map(candleOHLCVtoCandlestickData));

    if (smaValues && smaValues.some((v) => v != null)) {
      if (!smaSeries) {
        smaSeries = addLineSeries(chart!, "#2962ff");
      }
      const lineData = candles
        .map((c, i) => (smaValues[i] != null ? linePoint(c.timestamp, smaValues[i]!) : null))
        .filter((x): x is { time: ReturnType<typeof linePoint>["time"]; value: number } => x != null);
      smaSeries.setData(lineData);
    } else if (smaSeries) {
      smaSeries.setData([]);
    }

    chart!.timeScale().fitContent();
  }

  async function loadYfinance(): Promise<void> {
    const symbol = (symbolInput as HTMLInputElement).value.trim();
    if (!symbol) {
      setError("Enter a symbol");
      return;
    }
    setError(null);
    const { period, interval } = getPeriodInterval();
    try {
      const res = await fetch(yfinanceUrl(symbol, period, interval));
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      lastCandles = data.candles ?? [];
      renderChart(lastCandles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  async function loadWithSma(): Promise<void> {
    const symbol = (symbolInput as HTMLInputElement).value.trim();
    if (!symbol) {
      setError("Enter a symbol");
      return;
    }
    setError(null);
    try {
      const res = await fetch(smaUrl(symbol, "20"));
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      lastCandles = data.candles ?? [];
      renderChart(lastCandles, data.sma ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load SMA");
    }
  }

  function startStream(): void {
    const symbol = (symbolInput as HTMLInputElement).value.trim();
    if (!symbol) {
      setError("Enter a symbol");
      return;
    }
    setError(null);
    if (wsClient) wsClient.disconnect();
    const candles: OHLCVCandle[] = [];
    wsClient = new WSClient({
      symbol,
      onCandle: (c) => {
        candles.push(c);
        lastCandles = candles;
        renderChart(candles);
      },
      onStatus: setStatus,
      reconnectDelayMs: 3000,
      maxReconnectAttempts: 10,
    });
    wsClient.connect();
  }

  sourceSelect.addEventListener("change", () => {
    const src = (sourceSelect as HTMLSelectElement).value as DataSource;
    (csvWrap as HTMLElement).style.display = src === "csv" ? "inline-block" : "none";
  });

  loadBtn.addEventListener("click", async () => {
    const src = (sourceSelect as HTMLSelectElement).value as DataSource;
    if (src === "yfinance") {
      await loadYfinance();
    } else {
      // CSV: user must select file first; we trigger load via file input
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", async () => {
    const file = (fileInput as HTMLInputElement).files?.[0];
    if (!file) return;
    const symbol = (symbolInput as HTMLInputElement).value.trim() || "CSV";
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/data/csv?symbol=${encodeURIComponent(symbol)}`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      // After upload, fetch data via stream or reuse: backend caches. We can open WS or call an endpoint that returns candles.
      // Backend doesn't have GET /data/csv/{symbol}; we have WS that uses cache. So start stream to get cached CSV data.
      lastCandles = [];
      if (wsClient) wsClient.disconnect();
      wsClient = new WSClient({
        symbol,
        onCandle: (c) => {
          lastCandles.push(c);
          renderChart(lastCandles);
        },
        onStatus: setStatus,
      });
      wsClient.connect();
      fileLabel.textContent = file.name;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  });

  streamBtn.addEventListener("click", () => {
    startStream();
  });

  smaBtn.addEventListener("click", () => {
    loadWithSma();
  });

  refreshCheck.addEventListener("change", () => {
    if (refreshIntervalId) {
      clearInterval(refreshIntervalId);
      refreshIntervalId = null;
    }
    if ((refreshCheck as HTMLInputElement).checked) {
      refreshIntervalId = setInterval(() => {
        if ((sourceSelect as HTMLSelectElement).value === "yfinance") {
          loadYfinance().catch(() => {});
        }
      }, 60_000);
    }
  });

  // Initial load
  loadYfinance().catch(() => {});
}
