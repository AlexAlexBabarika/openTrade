import type {
  IChartApi,
  ISeriesApi,
  MouseEventParams,
  Time,
} from 'lightweight-charts';
import {
  candleOHLCVtoAreaData,
  candleOHLCVtoCandlestickData,
  candleOHLCVtoVolumeData,
} from './chartAdapters';
import {
  createChartContainer,
  addCandlestickSeries,
  addVolumeSeries,
  addAreaSeries,
} from './chart';
import { API_BASE, yfinanceUrl } from './config';
import type { OHLCVCandle } from './types';
import { WSClient } from './ws';
import type { ConnectionStatus } from './ws';

type DataSource = 'yfinance' | 'csv';

export function initApp(): void {
  const header = document.createElement('div');
  header.className = 'header';

  const symbolInput = document.createElement('input');
  symbolInput.type = 'text';
  symbolInput.placeholder = 'Symbol (e.g. AAPL)';
  symbolInput.value = 'AAPL';

  const timeframeSelect = document.createElement('select');
  timeframeSelect.innerHTML = `
    <option value="1d">1D</option>
    <option value="5d">5D</option>
    <option value="1mo" selected>1M</option>
    <option value="3mo">3M</option>
    <option value="6mo">6M</option>
    <option value="1y">1Y</option>
  `;

  const intervalSelect = document.createElement('select');
  intervalSelect.innerHTML = `
    <option value="1d" selected>1d</option>
    <option value="1h">1h</option>
    <option value="5m">5m</option>
  `;

  const sourceSelect = document.createElement('select');
  sourceSelect.id = 'source';
  sourceSelect.innerHTML = `
    <option value="yfinance">yfinance</option>
    <option value="csv">CSV</option>
  `;

  const loadBtn = document.createElement('button');
  loadBtn.textContent = 'Load';

  const streamBtn = document.createElement('button');
  streamBtn.textContent = 'Stream WS';
  streamBtn.className = 'secondary';

  const refreshLabel = document.createElement('label');
  refreshLabel.style.display = 'inline-flex';
  refreshLabel.style.alignItems = 'center';
  refreshLabel.style.gap = '0.35rem';
  refreshLabel.style.fontSize = '0.9rem';
  refreshLabel.style.color = 'var(--text-muted)';
  const refreshCheck = document.createElement('input');
  refreshCheck.type = 'checkbox';
  refreshCheck.title = 'Re-fetch yfinance every 60s when using yfinance';
  refreshLabel.append(
    refreshCheck,
    document.createTextNode('Auto-refresh 60s'),
  );

  const csvWrap = document.createElement('div');
  csvWrap.className = 'file-input-wrap';
  csvWrap.style.display = 'none';
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.csv';
  const fileLabel = document.createElement('span');
  fileLabel.className = 'file-label';
  fileLabel.textContent = 'Choose CSV';
  csvWrap.append(fileInput, fileLabel);

  const statusEl = document.createElement('span');
  statusEl.className = 'status';
  const statusDot = document.createElement('span');
  statusDot.className = 'status-dot';
  statusEl.append(statusDot, document.createTextNode('Disconnected'));

  const chartContainer = document.createElement('div');
  chartContainer.className = 'chart-container';

  const errorEl = document.createElement('div');
  errorEl.className = 'error-message';
  errorEl.style.display = 'none';

  header.append(
    symbolInput,
    timeframeSelect,
    intervalSelect,
    sourceSelect,
    csvWrap,
    loadBtn,
    streamBtn,
    refreshLabel,
    statusEl,
  );

  document.getElementById('app')!.append(header, errorEl, chartContainer);

  let chart: IChartApi | null = null;
  let candleSeries: ISeriesApi<'Candlestick'> | null = null;
  let areaSeries: ISeriesApi<'Area'> | null = null;
  let volumeSeries: ISeriesApi<'Histogram'> | null = null;
  let wsClient: WSClient | null = null;
  let lastCandles: OHLCVCandle[] = [];
  let refreshIntervalId: ReturnType<typeof setInterval> | null = null;

  function setError(msg: string | null): void {
    errorEl.textContent = msg ?? '';
    errorEl.style.display = msg ? 'block' : 'none';
  }

  function setStatus(status: ConnectionStatus): void {
    statusDot.className =
      'status-dot ' +
      (status === 'connected'
        ? 'connected'
        : status === 'error'
          ? 'error'
          : '');
    const labels: Record<ConnectionStatus, string> = {
      connecting: 'Connecting…',
      connected: 'Connected',
      disconnected: 'Disconnected',
      error: 'Error',
    };
    statusEl.childNodes[1].textContent = labels[status];
  }

  function getPeriodInterval(): { period: string; interval: string } {
    const period = (timeframeSelect as HTMLSelectElement).value;
    const interval = (intervalSelect as HTMLSelectElement).value;
    return { period, interval };
  }

  function createLegend(): void {
    if (!chart || !candleSeries) {
      return;
    }

    const legend = document.createElement('div');
    legend.style.position = 'absolute';
    legend.style.left = '12px';
    legend.style.top = '12px';
    legend.style.zIndex = '1';
    legend.style.fontSize = '14px';
    legend.style.fontFamily = 'sans-serif';
    legend.style.lineHeight = '18px';
    legend.style.fontWeight = '300';
    legend.style.color = 'white';
    chartContainer.appendChild(legend);

    const getLastBar = (series: ISeriesApi<any>) => {
      // Get the last bar by using a very high index with -1 offset
      return series.dataByIndex(Number.MAX_SAFE_INTEGER, -1);
    };

    const formatPrice = (price: number): string =>
      (Math.round(price * 100) / 100).toFixed(2);

    const formatDate = (time: Time): string => {
      let date: Date;
      if (typeof time === 'string') {
        // Handle "YYYY-MM-DD" format
        date = new Date(time);
      } else if (typeof time === 'number') {
        // Handle timestamp (seconds)
        date = new Date(time * 1000);
      } else {
        // Handle BusinessDay object (has year, month, day properties)
        date = new Date(time.year, time.month - 1, time.day);
      }

      const day = date.getDate();
      const months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
      ];
      const month = months[date.getMonth()];
      const year = date.getFullYear();

      return `${day} ${month} ${year}`;
    };

    const setTooltipHtml = (
      name: string,
      date: string,
      price: string,
      volume: string,
    ): void => {
      legend.textContent = '';

      const nameDiv = document.createElement('div');
      nameDiv.style.cssText = 'font-size: 24px; margin: 4px 0px;';
      nameDiv.textContent = name;

      const priceDiv = document.createElement('div');
      priceDiv.style.cssText = 'font-size: 22px; margin: 4px 0px;';
      priceDiv.textContent = price;

      const dateDiv = document.createElement('div');
      dateDiv.textContent = date;

      const volumeDiv = document.createElement('div');
      volumeDiv.textContent = `Volume: ${volume}`;

      legend.appendChild(nameDiv);
      legend.appendChild(priceDiv);
      legend.appendChild(dateDiv);
      legend.appendChild(volumeDiv);
    };

    const updateLegend = (param: MouseEventParams | undefined): void => {
      if (!candleSeries) return;

      const validCrosshairPoint = !(
        param === undefined ||
        param.time === undefined ||
        param.point === undefined ||
        param.point.x < 0 ||
        param.point.y < 0
      );

      const bar = validCrosshairPoint
        ? param.seriesData.get(candleSeries)
        : getLastBar(candleSeries);

      const volumeBar = volumeSeries
        ? validCrosshairPoint
          ? param.seriesData.get(volumeSeries)
          : getLastBar(volumeSeries)
        : null;

      if (!bar) return;

      const time = bar.time;
      let price: number | undefined;

      if ('value' in bar && typeof bar.value === 'number') {
        price = bar.value;
      } else if ('close' in bar && typeof bar.close === 'number') {
        price = bar.close;
      }

      if (price === undefined) return;

      let volume: number | undefined;
      if (
        volumeBar &&
        'value' in volumeBar &&
        typeof volumeBar.value === 'number'
      ) {
        volume = volumeBar.value;
      }

      const formattedPrice = formatPrice(price);
      const formattedDate = formatDate(time);
      const formattedVolume =
        volume !== undefined ? volume.toLocaleString() : '—';
      const currentSymbol =
        (symbolInput as HTMLInputElement).value.trim() || 'Unknown';
      setTooltipHtml(
        currentSymbol,
        formattedDate,
        formattedPrice,
        formattedVolume,
      );
    };

    chart.subscribeCrosshairMove(updateLegend);

    updateLegend(undefined);
  }

  function renderChart(candles: OHLCVCandle[]): void {
    if (!chart) {
      chart = createChartContainer(chartContainer);
      volumeSeries = addVolumeSeries(chart);
      areaSeries = addAreaSeries(chart);
      candleSeries = addCandlestickSeries(chart);
      createLegend();
    }

    if (candles.length >= 20) {
      areaSeries!.setData(candles.map(candleOHLCVtoAreaData));
    } else {
      areaSeries!.setData([]);
    }

    candleSeries!.setData(candles.map(candleOHLCVtoCandlestickData));
    volumeSeries!.setData(candles.map(candleOHLCVtoVolumeData));
    chart!.timeScale().fitContent();

    // Update legend after data is set so it reflects the latest data
    createLegend();
  }

  async function loadYfinance(): Promise<void> {
    const symbol = (symbolInput as HTMLInputElement).value.trim();
    if (!symbol) {
      setError('Enter a symbol');
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
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }

  function startStream(): void {
    const symbol = (symbolInput as HTMLInputElement).value.trim();
    if (!symbol) {
      setError('Enter a symbol');
      return;
    }
    setError(null);
    if (wsClient) wsClient.disconnect();
    const candles: OHLCVCandle[] = [];
    wsClient = new WSClient({
      symbol,
      onCandle: c => {
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

  sourceSelect.addEventListener('change', () => {
    const src = (sourceSelect as HTMLSelectElement).value as DataSource;
    (csvWrap as HTMLElement).style.display =
      src === 'csv' ? 'inline-block' : 'none';
  });

  loadBtn.addEventListener('click', async () => {
    const src = (sourceSelect as HTMLSelectElement).value as DataSource;
    if (src === 'yfinance') {
      await loadYfinance();
    } else {
      // CSV: user must select file first; we trigger load via file input
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', async () => {
    const file = (fileInput as HTMLInputElement).files?.[0];
    if (!file) return;
    const symbol = (symbolInput as HTMLInputElement).value.trim() || 'CSV';
    setError(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(
        `${API_BASE}/data/csv?symbol=${encodeURIComponent(symbol)}`,
        {
          method: 'POST',
          body: form,
        },
      );
      if (!res.ok) throw new Error(await res.text());
      await res.json();
      lastCandles = [];
      if (wsClient) wsClient.disconnect();
      wsClient = new WSClient({
        symbol,
        onCandle: c => {
          lastCandles.push(c);
          renderChart(lastCandles);
        },
        onStatus: setStatus,
      });
      wsClient.connect();
      fileLabel.textContent = file.name;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    }
  });

  streamBtn.addEventListener('click', () => {
    startStream();
  });

  refreshCheck.addEventListener('change', () => {
    if (refreshIntervalId) {
      clearInterval(refreshIntervalId);
      refreshIntervalId = null;
    }
    if ((refreshCheck as HTMLInputElement).checked) {
      refreshIntervalId = setInterval(() => {
        if ((sourceSelect as HTMLSelectElement).value === 'yfinance') {
          loadYfinance().catch(() => {});
        }
      }, 60_000);
    }
  });

  // Handle window resize to scale chart properly
  window.addEventListener('resize', () => {
    if (chart) {
      chart.applyOptions({
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
      });
    }
  });

  // Initial load
  loadYfinance().catch(() => {});
}
