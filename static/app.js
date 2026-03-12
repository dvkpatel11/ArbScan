const body = document.getElementById('opportunity-body');
const status = document.getElementById('status');
const refreshBtn = document.getElementById('refresh');
const summary = document.getElementById('summary');
const configView = document.getElementById('config-view');
const configForm = document.getElementById('config-form');
const bankrollInput = document.getElementById('bankroll-input');
const marginInput = document.getElementById('margin-input');
const refreshInput = document.getElementById('refresh-input');

let timerId = null;

function legMarkup(leg) {
  return `<div class="leg"><strong>${leg.side}</strong> @ ${leg.decimal_odds} (${leg.source}) | Stake: $${leg.recommended_stake} | Liq: $${Math.round(leg.liquidity_usd)}</div>`;
}

function rowMarkup(item) {
  return `<tr>
      <td>${item.market}</td>
      <td class="edge">${item.expected_edge_pct.toFixed(2)}%</td>
      <td>${item.implied_probability.toFixed(4)}</td>
      <td>${item.confidence_score.toFixed(1)}</td>
      <td>$${item.expected_profit_usd.toFixed(2)}</td>
      <td>${item.legs.map(legMarkup).join('')}</td>
    </tr>`;
}

function renderConfig(cfg) {
  configView.innerHTML = `
    <div><span>Sport</span><strong>${cfg.sport}</strong></div>
    <div><span>Odds API Key</span><strong>${cfg.keys.odds_api_key}</strong></div>
    <div><span>Polymarket Key</span><strong>${cfg.keys.polymarket_api_key}</strong></div>
    <div><span>Min Gross Margin</span><strong>${cfg.min_gross_margin_pct}%</strong></div>
  `;
  bankrollInput.value = cfg.bankroll;
  marginInput.value = cfg.min_gross_margin_pct;
  refreshInput.value = cfg.refresh_interval_seconds;
}

async function loadConfig() {
  const response = await fetch('/api/config');
  const config = await response.json();
  renderConfig(config);
}

async function saveConfig(event) {
  event.preventDefault();
  status.textContent = 'Saving config…';
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bankroll: Number(bankrollInput.value),
      min_gross_margin_pct: Number(marginInput.value),
      refresh_interval_seconds: Number(refreshInput.value),
    }),
  });
  await loadConfig();
  await loadOpportunities();
}

function setAutoRefresh(intervalSeconds) {
  if (timerId) {
    clearInterval(timerId);
  }
  timerId = setInterval(loadOpportunities, intervalSeconds * 1000);
}

async function loadOpportunities() {
  status.textContent = 'Loading…';
  try {
    const response = await fetch('/api/opportunities');
    const data = await response.json();
    const opportunities = data.opportunities || [];

    summary.textContent = `Coverage(ESPN/TheSportsDB): ${data.meta.coverage.espn_events}/${data.meta.coverage.thesportsdb_events} | Avg Edge: ${data.meta.algorithm_effectiveness.avg_edge_pct}% | Min Margin Filter: ${data.meta.min_gross_margin_pct}%`;
    setAutoRefresh(data.meta.refresh_interval_seconds || 30);

    if (opportunities.length === 0) {
      body.innerHTML = '<tr><td colspan="6">No current opportunities matching your min gross margin filter.</td></tr>';
      status.textContent = 'No opportunities';
      return;
    }

    body.innerHTML = opportunities.map(rowMarkup).join('');
    status.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    console.error(error);
    status.textContent = 'Failed to load';
    body.innerHTML = '<tr><td colspan="6">Error loading opportunities.</td></tr>';
  }
}

refreshBtn.addEventListener('click', loadOpportunities);
configForm.addEventListener('submit', saveConfig);

(async () => {
  await loadConfig();
  await loadOpportunities();
})();
