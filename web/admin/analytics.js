const form = document.querySelector('#analytics-report');
const status = document.querySelector('#analytics-status');
const results = document.querySelector('#analytics-results');
const labels = {
  view: 'Просмотры страниц',
  master: 'Вызвать мастера',
  phone: 'Нажатия на телефон',
  link: 'Другие ссылки',
};

function renderRows(id, rows) {
  const body = document.getElementById(id);
  body.replaceChildren();
  for (const values of rows) {
    const row = body.insertRow();
    for (const value of values) row.insertCell().textContent = value;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  results.hidden = true;
  status.textContent = 'Загружаем статистику…';
  const data = new FormData(form);
  try {
    const response = await fetch('/api/analytics/report?days=' + data.get('days'), {
      redirect: 'error',
      cache: 'no-store',
    });
    if (!response.ok) throw new Error('Сервис аналитики сейчас недоступен.');
    const report = await response.json();
    const totals = new Map(report.totals.map(row => [row.kind, row]));
    renderRows('analytics-totals', Object.entries(labels).map(([kind, label]) => {
      const row = totals.get(kind);
      return [label, row?.total ?? 0, row?.visitors ?? 0];
    }));
    renderRows('analytics-details', report.details.map(row => [
      (row.kind === 'view' ? 'Страница: ' : 'Ссылка: ') + row.label,
      row.total, row.visitors,
    ]));
    status.textContent = report.totals.length ? '' : 'За выбранный период событий пока нет.';
    results.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
