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

const MAX_MATCH_ROWS = 100;

function toNumber(value, fallback) {
  if (value === null || value === '' || Number.isNaN(Number(value))) {
    return fallback;
  }
  return Number(value);
}

async function loadStrategies() {
  try {
    const response = await fetch('/api/strategies');
    if (!response.ok) {
      throw new Error(`Failed to load strategies (${response.status})`);
    }
    const data = await response.json();
    renderStrategies(data.strategies || []);
  } catch (err) {
    strategiesListEl.innerHTML = '';
    const error = document.createElement('p');
    error.className = 'status';
    error.textContent = `Error loading strategies: ${err.message}`;
    strategiesListEl.appendChild(error);
    selectAllBtn.disabled = true;
    clearAllBtn.disabled = true;
  }
}

function renderStrategies(strategies) {
  strategiesListEl.innerHTML = '';
  if (!strategies.length) {
    const empty = document.createElement('p');
    empty.className = 'status';
    empty.textContent = 'No strategies available.';
    strategiesListEl.appendChild(empty);
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
}

function gatherFormData() {
  const formData = new FormData(form);
  const selectedStrategies = Array.from(
    strategiesListEl.querySelectorAll('input[type="checkbox"]:checked')
  ).map((input) => input.value);

  return {
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

  summaryStrategies.textContent = strategies.join(', ') || '—';
  summaryRounds.textContent = params.continuation && params.continuation > 0
    ? `${params.rounds ?? '—'} (continuation ${params.continuation})`
    : (params.rounds ?? '—');
  summaryRepeats.textContent = params.repeats ?? '—';

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

  statusMessageEl.textContent = `Tournament complete: ${matches.length} matches played.`;
  resultsWrapper.classList.remove('hidden');
}

function setAllStrategies(checked) {
  const inputs = strategiesListEl.querySelectorAll('input[type="checkbox"]');
  inputs.forEach((input) => {
    input.checked = checked;
  });
}

selectAllBtn.addEventListener('click', () => setAllStrategies(true));
clearAllBtn.addEventListener('click', () => setAllStrategies(false));
form.addEventListener('submit', submitForm);

loadStrategies();
