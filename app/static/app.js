const strategiesListEl = document.getElementById('strategiesList');
const selectAllBtn = document.getElementById('selectAll');
const clearAllBtn = document.getElementById('clearAll');
const form = document.getElementById('tournamentForm');
const statusMessageEl = document.getElementById('statusMessage');
const resultsWrapper = document.getElementById('results');
const standingsBody = document.querySelector('#standingsTable tbody');
const matchesBody = document.querySelector('#matchesTable tbody');
const matchHintEl = document.getElementById('matchHint');
const runButton = document.getElementById('runButton');
const summaryStrategies = document.getElementById('summaryStrategies');
const summaryRounds = document.getElementById('summaryRounds');
const summaryRepeats = document.getElementById('summaryRepeats');
const summaryTopStrategy = document.getElementById('summaryTopStrategy');
const standingsChart = document.getElementById('standingsChart');
const strategyCounter = document.getElementById('strategyCounter');
const strategyTotal = document.getElementById('strategyTotal');
const startFormCta = document.getElementById('startFormCta');
const mediaOutletsContainer = document.getElementById('mediaOutlets');
const mediaLimitNote = document.getElementById('mediaLimitNote');
const mediaSubscriptionsBody = document.querySelector('#mediaSubscriptionsTable tbody');
const mediaTableBody = document.querySelector('#mediaTable tbody');
const mediaHintEl = document.getElementById('mediaHint');
const summaryMediaReports = document.getElementById('summaryMediaReports');

const MAX_MATCH_ROWS = 100;
const MAX_MEDIA_ROWS = 150;

const mediaState = {
  ready: false,
  outlets: [],
  enabledOutlets: new Set(),
  defaults: {},
  enrollments: {},
  limit: null,
  baseNote: '',
};

let mediaWarningTimeout = null;

function toNumber(value, fallback) {
  if (value === null || value === '' || Number.isNaN(Number(value))) {
    return fallback;
  }
  return Number(value);
}

function clamp01(value) {
  const num = Number(value);
  if (Number.isNaN(num)) {
    return 0;
  }
  if (num < 0) {
    return 0;
  }
  if (num > 1) {
    return 1;
  }
  return num;
}

async function loadStrategies() {
  try {
    const response = await fetch('/api/strategies');
    if (!response.ok) {
      throw new Error(`Failed to load strategies (${response.status})`);
    }
    const data = await response.json();
    renderStrategies(data.strategies || []);
    setupMediaConfig(data.media || {});
  } catch (err) {
    strategiesListEl.innerHTML = '';
    const error = document.createElement('p');
    error.className = 'status';
    error.textContent = `Error loading strategies: ${err.message}`;
    strategiesListEl.appendChild(error);
    selectAllBtn.disabled = true;
    clearAllBtn.disabled = true;
    if (strategyCounter) {
      strategyCounter.textContent = '0';
    }
    if (strategyTotal) {
      strategyTotal.textContent = '0';
    }
    if (mediaOutletsContainer) {
      mediaOutletsContainer.innerHTML = '';
      const mediaError = document.createElement('p');
      mediaError.className = 'status';
      mediaError.textContent = 'Media configuration could not be loaded.';
      mediaOutletsContainer.appendChild(mediaError);
    }
    if (mediaLimitNote) {
      mediaLimitNote.textContent = 'Media configuration unavailable.';
    }
  }
}

function renderStrategies(strategies) {
  strategiesListEl.innerHTML = '';
  if (!strategies.length) {
    const empty = document.createElement('p');
    empty.className = 'status';
    empty.textContent = 'No strategies available.';
    strategiesListEl.appendChild(empty);
    updateStrategyCounter();
    return;
  }

  const sorted = [...strategies].sort((a, b) => a.name.localeCompare(b.name));
  for (const strategy of sorted) {
    const label = document.createElement('label');
    label.className = 'strategy-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'strategies';
    checkbox.value = strategy.name;
    checkbox.checked = true;
    checkbox.addEventListener('change', updateStrategyCounter);

    const nameSpan = document.createElement('span');
    nameSpan.className = 'strategy-name';
    nameSpan.textContent = strategy.name;

    const description = document.createElement('span');
    description.className = 'strategy-description';
    description.textContent = strategy.description || 'No description provided.';

    label.appendChild(checkbox);
    label.appendChild(nameSpan);
    label.appendChild(description);
    strategiesListEl.appendChild(label);
  }

  if (strategyTotal) {
    strategyTotal.textContent = String(sorted.length);
  }
  updateStrategyCounter();
}

function setupMediaConfig(mediaData) {
  if (!mediaOutletsContainer) {
    return;
  }
  const config = mediaData && typeof mediaData === 'object' ? (mediaData.config || mediaData) : {};
  const outlets = Array.isArray(config.outlets) ? config.outlets : [];
  const subscriptions = config.subscriptions || mediaData.subscriptions || {};

  mediaState.outlets = outlets.map((item) => normalizeOutlet(item));
  refreshEnabledOutlets();

  const limitValue = subscriptions.limit;
  if (typeof limitValue === 'number' && !Number.isNaN(limitValue)) {
    mediaState.limit = Math.max(0, Math.floor(limitValue));
  } else {
    mediaState.limit = null;
  }

  mediaState.defaults = {};
  if (subscriptions.defaults && typeof subscriptions.defaults === 'object') {
    Object.entries(subscriptions.defaults).forEach(([name, list]) => {
      if (Array.isArray(list)) {
        mediaState.defaults[name] = list.map((value) => String(value));
      }
    });
  }

  mediaState.enrollments = {};
  const enrollmentsSource = (subscriptions.enrollments && typeof subscriptions.enrollments === 'object' && Object.keys(subscriptions.enrollments).length)
    ? subscriptions.enrollments
    : mediaState.defaults;
  Object.entries(enrollmentsSource).forEach(([name, list]) => {
    mediaState.enrollments[name] = new Set(Array.isArray(list) ? list.map((value) => String(value)) : []);
  });

  mediaState.ready = true;
  pruneEnrollments();
  if (mediaLimitNote) {
    mediaLimitNote.dataset.status = '';
  }
  updateMediaLimitNote();
  renderMediaOutlets();
  renderMediaSubscriptions();
}

function normalizeOutlet(outlet) {
  const item = outlet || {};
  const normalized = {
    name: String(item.name || 'Outlet'),
    coverage: clamp01(item.coverage ?? 1),
    accuracy: clamp01(item.accuracy ?? 1),
    delay: item.delay !== undefined ? item.delay : 0,
    avoid_duplicates: item.avoid_duplicates !== undefined ? Boolean(item.avoid_duplicates) : true,
    enabled: item.enabled !== false,
  };
  return normalized;
}

function refreshEnabledOutlets() {
  mediaState.enabledOutlets = new Set(
    mediaState.outlets.filter((outlet) => outlet.enabled !== false).map((outlet) => outlet.name)
  );
}

function pruneEnrollments() {
  const enabled = mediaState.enabledOutlets;
  Object.keys(mediaState.enrollments).forEach((name) => {
    let set = mediaState.enrollments[name];
    if (!(set instanceof Set)) {
      set = new Set(Array.isArray(set) ? set : []);
      mediaState.enrollments[name] = set;
    }
    [...set].forEach((outletName) => {
      if (!enabled.has(outletName)) {
        set.delete(outletName);
      }
    });
  });
}

function describeDelay(delay) {
  if (Array.isArray(delay)) {
    if (!delay.length) {
      return 'instant delivery';
    }
    const numbers = delay
      .map((value) => Number(value))
      .filter((value) => !Number.isNaN(value));
    if (!numbers.length) {
      return 'variable delay';
    }
    if (numbers.length === 2 && delay.length === 2) {
      const [first, second] = numbers;
      if (first === second) {
        return first <= 0 ? 'instant delivery' : `${first} round${first === 1 ? '' : 's'} delay`;
      }
      const low = Math.min(first, second);
      const high = Math.max(first, second);
      return `${low}–${high} round delay`;
    }
    return `${numbers.join(', ')} round options`;
  }
  if (delay && typeof delay === 'object') {
    const min = Number(delay.min);
    const max = Number(delay.max);
    if (!Number.isNaN(min) && !Number.isNaN(max)) {
      if (min === max) {
        return min <= 0 ? 'instant delivery' : `${min} round${min === 1 ? '' : 's'} delay`;
      }
      const low = Math.min(min, max);
      const high = Math.max(min, max);
      return `${low}–${high} round delay`;
    }
    return 'variable delay';
  }
  const numeric = Number(delay);
  if (Number.isNaN(numeric) || numeric <= 0) {
    return 'instant delivery';
  }
  return `${numeric} round${numeric === 1 ? '' : 's'} delay`;
}

function renderMediaOutlets() {
  if (!mediaOutletsContainer) {
    return;
  }
  mediaOutletsContainer.innerHTML = '';
  if (!mediaState.ready) {
    const loading = document.createElement('p');
    loading.className = 'loading';
    loading.textContent = 'Loading media configuration…';
    mediaOutletsContainer.appendChild(loading);
    return;
  }
  if (!mediaState.outlets.length) {
    const empty = document.createElement('p');
    empty.className = 'hint';
    empty.textContent = 'No media outlets configured.';
    mediaOutletsContainer.appendChild(empty);
    return;
  }
  mediaState.outlets.forEach((outlet) => {
    const label = document.createElement('label');
    label.className = 'media-outlet-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = outlet.enabled !== false;
    checkbox.addEventListener('change', () => {
      outlet.enabled = checkbox.checked;
      refreshEnabledOutlets();
      pruneEnrollments();
      if (mediaLimitNote) {
        mediaLimitNote.dataset.status = '';
      }
      updateMediaLimitNote();
      renderMediaSubscriptions();
    });

    const textWrapper = document.createElement('div');
    const nameSpan = document.createElement('span');
    nameSpan.className = 'media-outlet-name';
    nameSpan.textContent = outlet.name;

    const metaSpan = document.createElement('span');
    metaSpan.className = 'media-outlet-meta';
    const coverage = Math.round(clamp01(outlet.coverage) * 100);
    const accuracy = Math.round(clamp01(outlet.accuracy) * 100);
    const parts = [`${coverage}% coverage`, `${accuracy}% accuracy`, describeDelay(outlet.delay)];
    metaSpan.textContent = parts.join(' • ');

    textWrapper.appendChild(nameSpan);
    textWrapper.appendChild(metaSpan);
    label.appendChild(checkbox);
    label.appendChild(textWrapper);
    mediaOutletsContainer.appendChild(label);
  });
}

function getSelectedStrategyNames() {
  return Array.from(
    strategiesListEl.querySelectorAll('input[type="checkbox"]:checked')
  ).map((input) => input.value);
}

function ensureEnrollmentSet(name) {
  if (!(mediaState.enrollments[name] instanceof Set)) {
    mediaState.enrollments[name] = new Set();
  }
  const set = mediaState.enrollments[name];
  [...set].forEach((outletName) => {
    if (!mediaState.enabledOutlets.has(outletName)) {
      set.delete(outletName);
    }
  });
  return set;
}

function renderMediaSubscriptions() {
  if (!mediaSubscriptionsBody) {
    return;
  }
  mediaSubscriptionsBody.innerHTML = '';
  if (!mediaState.ready) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 2;
    cell.className = 'hint';
    cell.textContent = 'Media configuration loading…';
    row.appendChild(cell);
    mediaSubscriptionsBody.appendChild(row);
    return;
  }
  const selected = getSelectedStrategyNames();
  if (!selected.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 2;
    cell.className = 'hint';
    cell.textContent = 'Select strategies to configure subscriptions.';
    row.appendChild(cell);
    mediaSubscriptionsBody.appendChild(row);
    return;
  }
  const enabledOutlets = mediaState.outlets.filter((outlet) => outlet.enabled !== false);
  if (!enabledOutlets.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 2;
    cell.className = 'hint';
    cell.textContent = 'Enable at least one outlet to deliver media reports.';
    row.appendChild(cell);
    mediaSubscriptionsBody.appendChild(row);
    return;
  }

  selected.forEach((strategyName) => {
    const set = ensureEnrollmentSet(strategyName);
    if (!set.size && Array.isArray(mediaState.defaults[strategyName])) {
      mediaState.defaults[strategyName].forEach((outletName) => {
        if (!mediaState.enabledOutlets.has(outletName)) {
          return;
        }
        if (mediaState.limit === 0) {
          return;
        }
        if (mediaState.limit !== null && set.size >= mediaState.limit) {
          return;
        }
        set.add(outletName);
      });
    }

    const row = document.createElement('tr');
    const strategyCell = document.createElement('th');
    strategyCell.scope = 'row';
    strategyCell.textContent = strategyName;
    row.appendChild(strategyCell);

    const outletsCell = document.createElement('td');
    const wrapper = document.createElement('div');
    wrapper.className = 'media-subscription-options';

    enabledOutlets.forEach((outlet) => {
      const option = document.createElement('label');
      option.className = 'media-subscription-option';
      option.title = `${Math.round(clamp01(outlet.coverage) * 100)}% coverage, ${Math.round(clamp01(outlet.accuracy) * 100)}% accuracy`;
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = set.has(outlet.name);
      checkbox.addEventListener('change', () => {
        if (!checkbox.checked) {
          set.delete(outlet.name);
          if (mediaLimitNote) {
            mediaLimitNote.dataset.status = '';
          }
          updateMediaLimitNote();
          return;
        }
        if (mediaState.limit === 0) {
          checkbox.checked = false;
          showMediaLimitWarning('Media delivery is disabled (subscription limit is 0).');
          return;
        }
        if (mediaState.limit !== null && set.size >= mediaState.limit) {
          checkbox.checked = false;
          showMediaLimitWarning(`${strategyName} has reached the limit of ${mediaState.limit} outlet${mediaState.limit === 1 ? '' : 's'}.`);
          return;
        }
        set.add(outlet.name);
        if (mediaLimitNote) {
          mediaLimitNote.dataset.status = '';
        }
        updateMediaLimitNote();
      });
      const labelText = document.createElement('span');
      labelText.textContent = outlet.name;
      option.appendChild(checkbox);
      option.appendChild(labelText);
      wrapper.appendChild(option);
    });

    if (!wrapper.childElementCount) {
      const empty = document.createElement('span');
      empty.className = 'hint';
      empty.textContent = 'No outlets available.';
      outletsCell.appendChild(empty);
    } else {
      outletsCell.appendChild(wrapper);
    }

    row.appendChild(outletsCell);
    mediaSubscriptionsBody.appendChild(row);
  });
}

function updateMediaLimitNote() {
  if (!mediaLimitNote) {
    return;
  }
  let note;
  if (!mediaState.outlets.length) {
    note = 'No media outlets configured.';
  } else if (!mediaState.enabledOutlets.size) {
    note = 'Enable at least one outlet to deliver media reports.';
  } else if (mediaState.limit === null) {
    note = 'No subscription limit: strategies may follow any enabled outlet.';
  } else if (mediaState.limit === 0) {
    note = 'Media delivery is disabled (subscription limit is 0).';
  } else {
    note = `Limit: choose up to ${mediaState.limit} outlet${mediaState.limit === 1 ? '' : 's'} per strategy.`;
  }
  mediaState.baseNote = note;
  if (!mediaLimitNote.dataset.status) {
    mediaLimitNote.textContent = note;
  }
}

function showMediaLimitWarning(message) {
  if (!mediaLimitNote) {
    return;
  }
  if (mediaWarningTimeout) {
    clearTimeout(mediaWarningTimeout);
  }
  const base = mediaState.baseNote ? `${mediaState.baseNote} — ${message}` : message;
  mediaLimitNote.dataset.status = 'warning';
  mediaLimitNote.textContent = base;
  mediaWarningTimeout = window.setTimeout(() => {
    mediaWarningTimeout = null;
    mediaLimitNote.dataset.status = '';
    updateMediaLimitNote();
  }, 3500);
}

function buildMediaPayload(selectedStrategies) {
  if (!mediaState.ready) {
    return null;
  }
  pruneEnrollments();
  const enabledOutlets = mediaState.outlets.filter((outlet) => outlet.enabled !== false);
  const outletsPayload = enabledOutlets.map((outlet) => {
    const payload = {
      name: outlet.name,
      coverage: clamp01(outlet.coverage),
      accuracy: clamp01(outlet.accuracy),
    };
    if (outlet.delay !== undefined) {
      payload.delay = outlet.delay;
    }
    if (outlet.avoid_duplicates !== undefined) {
      payload.avoid_duplicates = outlet.avoid_duplicates;
    }
    return payload;
  });
  const enrollmentsPayload = {};
  selectedStrategies.forEach((name) => {
    const set = ensureEnrollmentSet(name);
    enrollmentsPayload[name] = Array.from(set);
  });
  const defaultsPayload = {};
  Object.entries(mediaState.defaults).forEach(([name, list]) => {
    defaultsPayload[name] = Array.isArray(list) ? [...list] : [];
  });
  return {
    outlets: outletsPayload,
    subscriptions: {
      limit: mediaState.limit,
      defaults: defaultsPayload,
      enrollments: enrollmentsPayload,
    },
  };
}

function formatMatchId(matchId) {
  if (Array.isArray(matchId)) {
    return matchId.join(' • ');
  }
  if (matchId && typeof matchId === 'object') {
    try {
      return JSON.stringify(matchId);
    } catch (err) {
      return '—';
    }
  }
  if (matchId === undefined || matchId === null) {
    return '—';
  }
  return String(matchId);
}

function renderMediaTable(reports) {
  if (!mediaTableBody) {
    return;
  }
  mediaTableBody.innerHTML = '';
  const rows = [];
  if (reports && typeof reports === 'object') {
    Object.entries(reports).forEach(([strategyName, entries]) => {
      if (!Array.isArray(entries)) {
        return;
      }
      entries.forEach((entry) => {
        if (!entry || typeof entry !== 'object') {
          return;
        }
        rows.push({
          strategy: strategyName,
          outlet: entry.outlet || '',
          rep: entry.rep ?? '',
          ordinal: entry.ordinal ?? '',
          matchId: entry.match_id,
          accurate: entry.accurate,
          rumor: entry.payload && entry.payload.rumor ? 'Yes' : 'No',
          delay: entry.delay ?? 0,
        });
      });
    });
  }
  rows.sort((a, b) => {
    const repA = Number(a.rep ?? 0);
    const repB = Number(b.rep ?? 0);
    if (repA === repB) {
      return Number(a.ordinal ?? 0) - Number(b.ordinal ?? 0);
    }
    return repA - repB;
  });
  const limited = rows.slice(0, MAX_MEDIA_ROWS);
  limited.forEach((row) => {
    const tr = document.createElement('tr');
    const accurateText = row.accurate === false ? 'No' : 'Yes';
    tr.innerHTML = `
      <td>${row.strategy}</td>
      <td>${row.outlet}</td>
      <td>${row.rep}</td>
      <td>${formatMatchId(row.matchId)}</td>
      <td>${accurateText}</td>
      <td>${row.rumor}</td>
      <td>${row.delay}</td>
    `;
    mediaTableBody.appendChild(tr);
  });
  if (mediaHintEl) {
    if (!rows.length) {
      mediaHintEl.textContent = 'No media reports were delivered.';
    } else if (rows.length > MAX_MEDIA_ROWS) {
      mediaHintEl.textContent = `Showing the first ${MAX_MEDIA_ROWS} of ${rows.length} media reports. Export via the CLI for the full log.`;
    } else {
      mediaHintEl.textContent = '';
    }
  }
}

function gatherFormData() {
  const formData = new FormData(form);
  const selectedStrategies = getSelectedStrategyNames();
  const mediaPayload = buildMediaPayload(selectedStrategies);

  const payload = {
    rounds: toNumber(formData.get('rounds'), 150),
    continuation: toNumber(formData.get('continuation'), 0),
    noise: toNumber(formData.get('noise'), 0),
    repeats: toNumber(formData.get('repeats'), 1),
    seed: formData.get('seed') || null,
    payoffs: {
      T: toNumber(formData.get('payoff_T'), 5),
      R: toNumber(formData.get('payoff_R'), 3),
      P: toNumber(formData.get('payoff_P'), 1),
      S: toNumber(formData.get('payoff_S'), 0),
    },
    strategies: selectedStrategies,
  };
  if (mediaPayload) {
    payload.media = mediaPayload;
  }
  return payload;
}

function validatePayload(payload) {
  if (payload.strategies.length < 2) {
    throw new Error('Select at least two strategies to compare.');
  }
  if (payload.rounds < 1) {
    throw new Error('Rounds must be at least 1.');
  }
  if (payload.repeats < 1) {
    throw new Error('Repeats must be at least 1.');
  }
  if (payload.continuation < 0 || payload.continuation > 1) {
    throw new Error('Continuation probability must be between 0 and 1.');
  }
  if (payload.noise < 0 || payload.noise > 1) {
    throw new Error('Noise probability must be between 0 and 1.');
  }
  return payload;
}

async function submitForm(event) {
  event.preventDefault();
  resultsWrapper.classList.add('hidden');
  statusMessageEl.textContent = 'Running tournament…';
  runButton.disabled = true;
  try {
    const payload = validatePayload(gatherFormData());
    const response = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const message = errorBody.error || `Request failed with status ${response.status}`;
      throw new Error(message);
    }

    const result = await response.json();
    renderResults(result);
  } catch (err) {
    statusMessageEl.textContent = err.message;
  } finally {
    runButton.disabled = false;
  }
}

function renderResults(result) {
  const standings = result.standings || [];
  const matches = result.matches || [];
  const params = result.params || {};
  const strategies = result.strategies || [];
  const media = result.media || {};
  const mediaReports = media.reports || {};
  const mediaCount = Object.values(mediaReports).reduce((total, entries) => {
    if (!Array.isArray(entries)) {
      return total;
    }
    return total + entries.length;
  }, 0);

  summaryStrategies.textContent = strategies.join(', ') || '—';
  summaryRounds.textContent = params.continuation && params.continuation > 0
    ? `${params.rounds ?? '—'} (continuation ${params.continuation})`
    : (params.rounds ?? '—');
  summaryRepeats.textContent = params.repeats ?? '—';
  if (standings.length && summaryTopStrategy) {
    const top = standings[0];
    const avg = Number(top.avg_per_round ?? 0);
    summaryTopStrategy.textContent = `${top.strategy} (${avg.toFixed(4)} avg / round)`;
  } else if (summaryTopStrategy) {
    summaryTopStrategy.textContent = '—';
  }
  if (summaryMediaReports) {
    summaryMediaReports.textContent = String(mediaCount);
  }

  standingsBody.innerHTML = '';
  standings.forEach((row, index) => {
    const tr = document.createElement('tr');
    const totalScore = Number(row.total_score ?? 0);
    const totalRounds = Number(row.total_rounds ?? 0);
    const average = Number(row.avg_per_round ?? 0);
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td>${row.strategy}</td>
      <td>${totalScore.toFixed(2)}</td>
      <td>${totalRounds}</td>
      <td>${average.toFixed(4)}</td>
    `;
    standingsBody.appendChild(tr);
  });

  matchesBody.innerHTML = '';
  const limitedMatches = matches.slice(0, MAX_MATCH_ROWS);
  limitedMatches.forEach((row) => {
    const tr = document.createElement('tr');
    const avgA = Number(row.avg_A ?? 0);
    const avgB = Number(row.avg_B ?? 0);
    tr.innerHTML = `
      <td>${row.rep}</td>
      <td>${row.A}</td>
      <td>${row.B}</td>
      <td>${row.score_A}</td>
      <td>${row.score_B}</td>
      <td>${avgA.toFixed(4)}</td>
      <td>${avgB.toFixed(4)}</td>
      <td>${row.rounds}</td>
    `;
    matchesBody.appendChild(tr);
  });

  if (matches.length > MAX_MATCH_ROWS) {
    matchHintEl.textContent = `Showing the first ${MAX_MATCH_ROWS} of ${matches.length} matches. Export the results via the CLI for the full dataset.`;
  } else if (!matches.length) {
    matchHintEl.textContent = 'No matches were played.';
  } else {
    matchHintEl.textContent = '';
  }

  renderStandingsChart(standings);
  renderMediaTable(mediaReports);

  statusMessageEl.textContent = `Tournament complete: ${matches.length} matches played, ${mediaCount} media reports delivered.`;
  resultsWrapper.classList.remove('hidden');
}

function setAllStrategies(checked) {
  const inputs = strategiesListEl.querySelectorAll('input[type="checkbox"]');
  inputs.forEach((input) => {
    input.checked = checked;
  });
  updateStrategyCounter();
  if (mediaState.ready) {
    renderMediaSubscriptions();
  }
}

function updateStrategyCounter() {
  if (!strategyCounter) {
    return;
  }
  const all = strategiesListEl.querySelectorAll('input[type="checkbox"]');
  const checked = strategiesListEl.querySelectorAll('input[type="checkbox"]:checked');
  strategyCounter.textContent = String(checked.length);
  if (strategyTotal) {
    strategyTotal.textContent = String(all.length);
  }
  if (mediaState.ready) {
    renderMediaSubscriptions();
  }
}

function renderStandingsChart(standings) {
  if (!standingsChart) {
    return;
  }

  standingsChart.innerHTML = '';
  if (!standings.length) {
    const empty = document.createElement('p');
    empty.className = 'status';
    empty.textContent = 'Run a tournament to see program performance.';
    standingsChart.appendChild(empty);
    return;
  }

  const maxAvg = Math.max(...standings.map((row) => Number(row.avg_per_round ?? 0)));
  standings.forEach((row, index) => {
    const avg = Number(row.avg_per_round ?? 0);
    const total = Number(row.total_score ?? 0);
    const wrapper = document.createElement('div');
    wrapper.className = 'chart-row';

    const label = document.createElement('div');
    label.className = 'chart-label';
    label.textContent = `${index + 1}. ${row.strategy}`;

    const bar = document.createElement('div');
    bar.className = 'chart-bar';

    const fill = document.createElement('div');
    fill.className = 'chart-bar-fill';
    const width = maxAvg > 0 ? Math.max((avg / maxAvg) * 100, 2) : 0;
    fill.style.width = `${width}%`;
    fill.setAttribute('aria-hidden', 'true');

    const score = document.createElement('span');
    score.className = 'chart-score';
    score.textContent = `${avg.toFixed(3)} avg`;

    const totalBadge = document.createElement('span');
    totalBadge.className = 'chart-total';
    totalBadge.textContent = `${total.toFixed(1)} pts`;

    bar.appendChild(fill);
    wrapper.appendChild(label);
    wrapper.appendChild(bar);
    wrapper.appendChild(score);
    wrapper.appendChild(totalBadge);
    standingsChart.appendChild(wrapper);
  });
}

selectAllBtn.addEventListener('click', () => setAllStrategies(true));
clearAllBtn.addEventListener('click', () => setAllStrategies(false));
form.addEventListener('submit', submitForm);

if (startFormCta) {
  startFormCta.addEventListener('click', () => {
    const card = document.getElementById('configCard');
    if (!card) {
      return;
    }
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const firstInput = card.querySelector('input, select, button');
    if (firstInput instanceof HTMLElement) {
      try {
        firstInput.focus({ preventScroll: true });
      } catch (err) {
        firstInput.focus();
      }
    }
  });
}

renderStandingsChart([]);
renderMediaTable({});
loadStrategies();
