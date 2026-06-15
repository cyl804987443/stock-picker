const state = {
  currentDate: '',
  results: [],
  dates: [],
  strategies: [],
  activeStrategy: '',
  summary: null,
  dataStatus: null,
  activeJobId: localStorage.getItem('activeScreeningJob') || '',
  jobPollTimer: null,
};

async function api(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error('API Error:', e);
    return null;
  }
}

async function loadData() {
  const availableDates = await api("/api/dates");
  if (availableDates && availableDates.length) {
    state.dates = availableDates;
    if (!state.currentDate || !availableDates.includes(state.currentDate)) {
      state.currentDate = availableDates[0];
    }
  }
  const date = state.currentDate || getToday();
  state.currentDate = date;

  const loading = document.getElementById('loading');
  if (loading) loading.textContent = '加载中...';

  const [results, strategies, summary, dates, dataStatus] = await Promise.all([
    api(`/api/results?date=${date}&limit=10000`),
    api('/api/strategies'),
    api(`/api/summary?date=${date}`),
    api('/api/dates'),
    api('/api/data-status'),
  ]);

  state.results = results || [];
  state.strategies = strategies || [];
  state.summary = summary;
  state.dataStatus = dataStatus;
  if (dates && dates.length) state.dates = availableDates;

  renderDateNav();
  renderFilters();
  renderContent();
  updateDateDisplay();
  updateCountdown();
  renderDataStatus();
}

function getToday() {
  return new Date().toISOString().split('T')[0];
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return `${d.getMonth()+1}/${d.getDate()}`;
}

function renderDateNav() {
  const sel = document.getElementById('dateSelect');
  const current = state.currentDate;

  let options = '';
  if (state.dates.length) {
    state.dates.forEach(d => {
      options += `<option value="${d}"${d===current?' selected':''}>${formatDate(d)}</option>`;
    });
  }
  // Always add today
  if (!state.dates.includes(getToday())) {
    options = `<option value="${getToday()}"${getToday()===current?' selected':''}>今天</option>` + options;
  }
  sel.innerHTML = options;

  const status = document.getElementById('navStatus');
  if (state.summary) {
    status.textContent =
      `筛选 ${state.summary.screened_stocks || 0} 只，` +
      `入选 ${state.summary.total_stocks || 0} 只，` +
      `命中 ${state.summary.total_hits || 0} 条策略`;
  } else {
    status.textContent = state.currentDate === getToday() ? '今日尚未选股' : '该日暂无数据';
  }
}

function renderFilters() {
  const bar = document.getElementById('filterBar');
  const descMap = {};
  state.strategies.forEach(s => { descMap[s.name] = s.description; });
  const counts = {};
  state.results.forEach(r => {
    counts[r.strategy_name] = (counts[r.strategy_name] || 0) + 1;
  });

  const total = state.results.length;
  let html = `<span class="filter-pill${!state.activeStrategy?' active':''}" onclick="setFilter('')">全部 <span class="count">${total}</span></span>`;

  // Category order for display
  // Sort strategies by count descending
  const ranked = state.strategies.map(s => ({
    name: s.name,
    count: counts[s.name] || 0,
    desc: descMap[s.name] || ''
  }));
  ranked.sort((a, b) => b.count - a.count);

  for (const s of ranked) {
    const active = state.activeStrategy === s.name;
    html += `<span class="filter-pill${active?' active':''}" onclick="setFilter('${s.name}')" title="${s.desc}">${s.name} <span class="count">${s.count}</span></span>`;
  }

  bar.innerHTML = html;
}

function setFilter(strategy) {
  state.activeStrategy = strategy;
  renderFilters();
  renderContent();
}

function renderContent() {
  const el = document.getElementById('mainContent');
  const descMap = {};
  state.strategies.forEach(s => { descMap[s.name] = s.description; });
  const filtered = state.activeStrategy
    ? state.results.filter(r => r.strategy_name === state.activeStrategy)
    : state.results;

  if (!filtered.length) {
    el.innerHTML = `<div class="empty-state"><div class="icon">📭</div><p>暂无选股结果</p></div>`;
    return;
  }

  // Group by strategy, then render sections
  const grouped = {};
  filtered.forEach(r => {
    if (!grouped[r.strategy_name]) grouped[r.strategy_name] = [];
    grouped[r.strategy_name].push(r);
  });

  let html = '';
  for (const [strategy, items] of Object.entries(grouped)) {
    const stratInfo = state.strategies.find(s => s.name === strategy);
    const cat = stratInfo ? stratInfo.category : '';
    html += `<div class="strategy-section">`;
    html += `<div class="strategy-header" title="${descMap[strategy] || ''}"><span>${strategy}</span><span class="count">${items.length}只</span><span class="category">${cat}</span></div>`;
    html += `<div class="card-grid">`;
    items.forEach(r => {
      const up = r.change_pct >= 0;
      const changeClass = up ? 'change-up' : 'change-down';
      const changeSign = up ? '+' : '';

      // Strategy tag colors
      const tagColors = {
        '三一模式': 'tag-sanyi', '竞价爆量': 'tag-baoliang', '竞价弱转强': 'tag-sanyi',
        '底部爆量': 'tag-baoliang', '量窒息': 'tag-baoliang',
        '放量突破': 'tag-baoliang',
        '反包': 'tag-fanbao', '缩量反包': 'tag-fanbao', '仙人指路': 'tag-fanbao',
        '多方炮': 'tag-fanbao', 'N字战法': 'tag-fanbao',
        '龙回头': 'tag-zhangting', '一进二': 'tag-zhangting',
        '二进三': 'tag-zhangting', '龙头战法': 'tag-zhangting',
      };

      // Show all strategy tags for this stock
      const allTags = state.results
        .filter(r2 => r2.stock_code === r.stock_code)
        .map(r2 => r2.strategy_name);
      const uniqueTags = [...new Set(allTags)];

      html += `<div class="stock-card">`;
      html += `<div class="card-top"><div><span class="stock-name">${r.stock_name}</span><span class="stock-code">${r.stock_code}</span></div>`;
      html += `<div><span class="stock-price">${r.price.toFixed(2)}</span><span class="stock-change ${changeClass}">${changeSign}${r.change_pct.toFixed(2)}%</span></div></div>`;
      html += `<div class="card-tags">`;
      uniqueTags.forEach(t => {
        const tc = tagColors[t] || '';
        html += `<span class="strategy-tag ${tc}" title="${descMap[t] || ''}">${t}</span>`;
      });
      html += `</div>`;
      html += `<div class="card-reason">📌 ${r.reason || '无'}</div>`;
      // Sector / concept tags
      // Industry / sector tags
      if (r.sector) {
        const tags = r.sector.split(',').filter(Boolean);
        if (tags.length) {
          html += `<div class="card-sector-tags">`;
          tags.forEach(t => { html += `<span class="sector-tag">${t.trim()}</span>`; });
          html += `</div>`;
        }
      }
      // Concept / theme tags
      if (r.concepts) {
        const conceptTags = r.concepts.split(',').filter(Boolean);
        if (conceptTags.length) {
          html += `<div class="card-concept-tags">`;
          // Show up to 5 concepts to avoid overflow
          conceptTags.slice(0, 5).forEach(t => { html += `<span class="concept-tag">${t.trim()}</span>`; });
          if (conceptTags.length > 5) {
            html += `<span class="concept-tag concept-tag-more">+${conceptTags.length - 5}</span>`;
          }
          html += `</div>`;
        }
      }
      if (r.volume_ratio > 0) {
        html += `<div class="card-indicators"><span>量比 ${r.volume_ratio.toFixed(2)}</span>`;
        if (r.market_cap > 0) html += `<span>市值 ${r.market_cap.toFixed(0)}亿</span>`;
        html += `</div>`;
      }
      html += `</div>`;
    });
    html += `</div></div>`;
  }

  el.innerHTML = html;
}

function updateDateDisplay() {
  const el = document.getElementById('dateDisplay');
  el.textContent = `📅 ${state.currentDate}`;
}

function updateCountdown() {
  const el = document.getElementById('countdown');
  const now = new Date();
  const marketOpen = new Date(now);
  marketOpen.setHours(9, 30, 0, 0);
  const marketClose = new Date(now);
  marketClose.setHours(15, 0, 0, 0);

  const day = now.getDay();
  if (day === 0 || day === 6) {
    el.textContent = '📅 休市';
    return;
  }

  if (now < marketOpen) {
    const diff = marketOpen - now;
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    el.textContent = `⏰ 距开盘 ${h}h ${m}m`;
  } else if (now < marketClose) {
    el.textContent = '📊 交易中';
  } else {
    el.textContent = '✅ 已收盘';
  }
}

function changeDate(delta) {
  const current = new Date(state.currentDate + 'T00:00:00');
  current.setDate(current.getDate() + delta);
  const dateStr = current.toISOString().split('T')[0];
  state.currentDate = dateStr;
  document.getElementById('dateSelect').value = dateStr;
  loadData();
}

function onDateChange() {
  state.currentDate = document.getElementById('dateSelect').value;
  loadData();
}

async function triggerScreening() {
  const btn = document.getElementById('btnTrigger');
  btn.disabled = true;
  btn.textContent = '⏳ 创建任务...';
  try {
    const response = await fetch('/api/run-screening?run_type=pre_market', { method: 'POST' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    state.activeJobId = result.job_id;
    localStorage.setItem('activeScreeningJob', result.job_id);
    showJobProgress();
    pollJob();
  } catch (e) {
    alert(`选股任务创建失败：${e.message}`);
    btn.disabled = false;
    btn.textContent = '⚡ 手动选股';
  }
}

const stageNames = {
  queued: '等待执行',
  refreshing_universe: '更新沪深主板股票池',
  syncing_market_data: '同步真实日线行情',
  screening: '运行选股策略',
  completed: '选股完成',
  failed: '任务失败',
};

function renderDataStatus() {
  const el = document.getElementById('dataStatus');
  const info = state.dataStatus;
  if (!info) {
    el.classList.add('error');
    el.textContent = '无法读取行情数据状态';
    return;
  }
  el.classList.remove('error');
  el.innerHTML =
    `<span>股票池 <strong>${info.universe_stocks}</strong> 只</span>` +
    `<span>已有行情 <strong>${info.cached_stocks}</strong> 只</span>` +
    `<span>最新交易日 <strong>${info.latest_trade_date || '尚未同步'}</strong></span>` +
    `<span>最近成功同步 <strong>${info.last_successful_sync ? new Date(info.last_successful_sync).toLocaleString() : '尚无'}</strong></span>`;
}

function showJobProgress() {
  document.getElementById('jobProgress').classList.remove('hidden');
  const btn = document.getElementById('btnTrigger');
  btn.disabled = true;
  btn.textContent = '⏳ 全市场处理中...';
}

async function pollJob() {
  if (!state.activeJobId) return;
  showJobProgress();
  const job = await api(`/api/jobs/${state.activeJobId}`);
  if (!job) {
    finishJobPolling();
    return;
  }
  document.getElementById('jobStage').textContent = stageNames[job.stage] || job.stage;
  document.getElementById('progressBar').style.width = `${job.progress || 0}%`;
  document.getElementById('jobNumbers').textContent =
    job.total_stocks ? `${job.processed_stocks}/${job.total_stocks}` : '';
  const message = document.getElementById('jobMessage');
  message.classList.toggle('error', job.status === 'failed');
  if (job.status === 'failed') {
    message.textContent = job.error_message || '同步失败，旧的有效结果已保留';
    finishJobPolling(false);
    return;
  }
  message.textContent =
    job.stage === 'syncing_market_data'
      ? `成功 ${job.success_count}，失败 ${job.failed_count}`
      : job.status === 'completed'
        ? `筛选 ${job.screened_stocks} 只，入选 ${job.selected_stocks} 只，共 ${job.total_hits} 条策略命中`
        : '任务在后台运行，关闭页面不会中断';
  if (job.status === 'completed') {
    finishJobPolling(true);
    await loadData();
    return;
  }
  clearTimeout(state.jobPollTimer);
  state.jobPollTimer = setTimeout(pollJob, 1500);
}

function finishJobPolling(completed = false) {
  clearTimeout(state.jobPollTimer);
  state.activeJobId = '';
  localStorage.removeItem('activeScreeningJob');
  const btn = document.getElementById('btnTrigger');
  btn.disabled = false;
  btn.textContent = '⚡ 手动选股';
  if (!completed) loadData();
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  state.currentDate = getToday();
  loadData();
  setInterval(updateCountdown, 60000);
  if (state.activeJobId) pollJob();
});

/* ===== K-line Chart Modal ===== */

async function showChart(code, name) {
  const klineData = await api(`/api/stock/${code}/kline?days=60`);
  if (!klineData || !klineData.length) {
    alert(name + '暂无K线数据');
    return;
  }
  openChartModal(code, name, klineData);
}

function openChartModal(code, name, klineData) {
  // Remove existing modal
  const old = document.getElementById('kline-modal');
  if (old) old.remove();

  const modal = document.createElement('div');
  modal.id = 'kline-modal';
  modal.className = 'kline-modal-overlay';
  modal.innerHTML = `
    <div class="kline-modal-content">
      <div class="kline-modal-header">
        <span class="kline-stock-name">${name}<span class="kline-stock-code">${code}</span></span>
        <span class="kline-period">近60日K线</span>
        <button class="kline-close-btn" onclick="closeChart()">✕</button>
      </div>
      <canvas id="kline-canvas" width="900" height="480"></canvas>
      <div class="kline-legend">
        <span style="color:#ef4444">■ 阳线(涨)</span>
        <span style="color:#16a34a">■ 阴线(跌)</span>
        <span style="color:#3b82f6">— MA5</span>
        <span style="color:#f59e0b">— MA10</span>
        <span style="color:#8b5cf6">— MA20</span>
        <span style="color:#f59e0b">— K</span>
        <span style="color:#3b82f6">— D</span>
        <span style="color:#8b5cf6">— J</span>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeChart();
  });

  // Draw chart after DOM render
  setTimeout(() => drawCandlestickChart(klineData), 100);
}

function closeChart() {
  const modal = document.getElementById('kline-modal');
  if (modal) modal.remove();
}

function drawCandlestickChart(data) {
  const canvas = document.getElementById('kline-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  // Layout
  const padding = { top: 30, right: 20, bottom: 30, left: 60 };
  const chartH = H - padding.top - padding.bottom - 90; // Leave 90px for volume + KDJ
  const chartW = W - padding.left - padding.right;
  const volTop = chartH + padding.top + 10;
  const kdjTop = volTop + 35;

  // Ranges
  const highs = data.map(d => d.high);
  const lows = data.map(d => d.low);
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const priceRange = maxPrice - minPrice || 1;
  const maxVol = Math.max(...data.map(d => d.volume));

  const barWidth = Math.max(3, chartW / data.length * 0.7);
  const barGap = chartW / data.length;

  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartH / 4) * i;
    const price = maxPrice - (priceRange / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(W - padding.right, y);
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px system-ui';
    ctx.fillText(price.toFixed(2), padding.left - 55, y + 4);
  }

  // Draw candlesticks
  data.forEach((d, i) => {
    const x = padding.left + barGap * i + barGap / 2;
    const openY = padding.top + (maxPrice - d.open) / priceRange * chartH;
    const closeY = padding.top + (maxPrice - d.close) / priceRange * chartH;
    const highY = padding.top + (maxPrice - d.high) / priceRange * chartH;
    const lowY = padding.top + (maxPrice - d.low) / priceRange * chartH;

    const up = d.close >= d.open;
    ctx.strokeStyle = up ? '#ef4444' : '#16a34a';
    ctx.fillStyle = up ? '#ef4444' : '#16a34a';
    ctx.lineWidth = 1;

    // Wick
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();

    // Body
    const bodyH = Math.abs(closeY - openY) || 1;
    const bodyTop = Math.min(openY, closeY);
    ctx.fillRect(x - barWidth / 2, bodyTop, barWidth, bodyH);
  });

  // MA lines
  const drawMA = (key, color, width) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    let started = false;
    data.forEach((d, i) => {
      const v = d[key];
      if (!v || v === 0) { started = false; return; }
      const x = padding.left + barGap * i + barGap / 2;
      const y = padding.top + (maxPrice - v) / priceRange * chartH;
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };

  drawMA('ma5', '#3b82f6', 1.5);
  drawMA('ma10', '#f59e0b', 1.5);
  drawMA('ma20', '#8b5cf6', 1.5);

  // Volume bars (compact)
  const volH = 30;
  ctx.fillStyle = '#94a3b8';
  ctx.font = '9px system-ui';
  ctx.fillText('VOL', padding.left - 28, volTop + 14);
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  ctx.moveTo(padding.left, volTop);
  ctx.lineTo(W - padding.right, volTop);
  ctx.stroke();

  data.forEach((d, i) => {
    const x = padding.left + barGap * i + barGap / 2;
    const vh = (d.volume / maxVol) * volH;
    const up = d.close >= d.open;
    ctx.fillStyle = up ? 'rgba(239,68,68,0.4)' : 'rgba(22,163,74,0.4)';
    ctx.fillRect(x - barWidth / 2, volTop + volH - vh, barWidth, vh);
  });

  // KDJ indicator
  ctx.fillStyle = '#94a3b8';
  ctx.font = '9px system-ui';
  ctx.fillText('KDJ', padding.left - 28, kdjTop + 14);
  
  const kdjRange = 100; // KDJ values are 0-100
  const kdjH = 25;
  
  // KDJ grid line (80, 50, 20)
  [80, 50, 20].forEach(level => {
    const y = kdjTop + (1 - level / 100) * kdjH;
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 0.3;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(W - padding.right, y);
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(level, padding.left - 24, y + 3);
  });

  // Draw KDJ lines
  const drawKDJ = (key, color, width) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    let started = false;
    data.forEach((d, i) => {
      const v = d[key];
      if (!v || v === 0) { started = false; return; }
      const x = padding.left + barGap * i + barGap / 2;
      const y = kdjTop + (1 - v / 100) * kdjH;
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  drawKDJ('kdj_k', '#f59e0b', 1.2);
  drawKDJ('kdj_d', '#3b82f6', 1.2);
  drawKDJ('kdj_j', '#8b5cf6', 1.0);

  // Date labels
  ctx.fillStyle = '#94a3b8';
  ctx.font = '9px system-ui';
  const labelStep = Math.max(1, Math.floor(data.length / 6));
  data.forEach((d, i) => {
    if (i % labelStep === 0) {
      const x = padding.left + barGap * i + barGap / 2;
      const dateStr = d.trade_date.length > 10 ? d.trade_date : d.trade_date.slice(-5);
      ctx.fillText(dateStr, x - 15, H - padding.bottom + 14);
    }
  });
}

// Wire up click handlers on stock cards (delegation)
document.addEventListener('click', (e) => {
  const card = e.target.closest('.stock-card');
  if (card) {
    const name = card.querySelector('.stock-name')?.textContent;
    const code = card.querySelector('.stock-code')?.textContent;
    if (name && code) showChart(code, name);
  }
});
