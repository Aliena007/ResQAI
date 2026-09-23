const authView = document.querySelector('#auth-view');
const deskView = document.querySelector('#desk-view');
const authMessage = document.querySelector('#auth-message');
const weatherMessage = document.querySelector('#weather-message');

function showMessage(element, message, success = false) {
  element.textContent = message;
  element.classList.toggle('success', success);
}

async function send(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function showDesk() {
  authView.classList.add('hidden');
  deskView.classList.remove('hidden');
}

function showAuth() {
  deskView.classList.add('hidden');
  authView.classList.remove('hidden');
}

document.querySelectorAll('[data-auth]').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
  tab.classList.add('active');
  document.querySelector('#login-form').classList.toggle('hidden', tab.dataset.auth !== 'login');
  document.querySelector('#register-form').classList.toggle('hidden', tab.dataset.auth !== 'register');
  showMessage(authMessage, '');
}));

document.querySelector('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try { await send('/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(formData(event.target)) }); showDesk(); }
  catch (error) { showMessage(authMessage, error.message); }
});

document.querySelector('#register-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try { await send('/auth/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(formData(event.target)) }); showDesk(); }
  catch (error) { showMessage(authMessage, error.message); }
});

document.querySelector('#logout-button').addEventListener('click', async () => { await send('/auth/logout', {method: 'POST'}); showAuth(); });
document.querySelector('#weather-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = event.target.querySelector('button');
  button.disabled = true;
  button.firstChild.textContent = 'Agent is analyzing... ';
  showMessage(weatherMessage, 'Resolving location and reading the five-day forecast...');
  try {
    const result = await send('/weather/analyze', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(formData(event.target)) });
    renderWeather(result);
    showMessage(weatherMessage, 'Analysis complete. Use the readiness actions before the peak risk day.', true);
  } catch (error) { showMessage(weatherMessage, error.message); }
  finally { button.disabled = false; button.firstChild.textContent = 'Run preventive analysis '; }
});

function renderWeather(result) {
  const target = document.querySelector('#weather-result');
  target.className = `weather-result risk-${result.risk_level}`;
  target.innerHTML = `<div class="weather-overview"><div><span class="risk-label">${escapeHtml(result.risk_level)} RISK</span><h3>${escapeHtml(result.location)}</h3><p>${escapeHtml(result.headline)}</p></div><strong>${result.risk_score}<small>/ 10</small></strong></div><div class="weather-agent-note"><b>Agent reasoning</b><span>${escapeHtml(result.reasoning)}</span></div><div class="weather-columns"><div><b>Detected signals</b><div class="signal-list">${result.hazards.map((hazard) => `<span>${escapeHtml(hazard)}</span>`).join('')}</div><b>Recommended readiness</b><ul>${result.recommended_actions.map((action) => `<li>${escapeHtml(action)}</li>`).join('')}</ul></div><div><b>Five-day forecast</b><div class="forecast-list">${result.forecast.map((day) => `<div class="forecast-day"><span>${escapeHtml(day.date.slice(5))}</span><span>${escapeHtml(day.condition)}</span><b>${day.temperature_max}° / ${day.temperature_min}°</b><i class="mini-risk ${day.risk_level}">${day.risk_level}</i></div>`).join('')}</div></div></div><small class="source-note">${escapeHtml(result.source)}</small>`;
}

function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value; return div.innerHTML; }
