(function () {
  const selectedCourseName = window.selectedCourseName || "";

  const raw        = document.getElementById('rawLog').value || '';
  const tbody      = document.querySelector('#logsTable tbody');
  const emptyState = document.getElementById('emptyState');

  const labelFilter = document.getElementById('labelFilter');
  const dateFrom    = document.getElementById('dateFrom');
  const dateTo      = document.getElementById('dateTo');
  const urlFilter   = document.getElementById('urlFilter');
  const confMin     = document.getElementById('confMin');

  const summaryRow    = document.getElementById('summaryRow');
  const sumBenign     = document.getElementById('sumBenign');
  const sumSuspicious = document.getElementById('sumSuspicious');
  const sumPhish      = document.getElementById('sumPhish');
  const sumMalware    = document.getElementById('sumMalware');
  const sumAdult      = document.getElementById('sumAdult');

  const pagination    = document.getElementById('paginationControls');
  const paginationInfo= document.getElementById('paginationInfo');
  const prevBtn       = document.getElementById('prevPage');
  const nextBtn       = document.getElementById('nextPage');
  const ROWS_PER_PAGE = 20;   // limit 20 rows per page
  let currentPage = 1;

  /* ---------- helpers: safe HTML + soft breaks ---------- */
  function escapeHtml(s) {
    return String(s ?? '')
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }
  function softBreak(s) {
    const e = escapeHtml(s);
    return e.replaceAll('_','_<wbr>').replaceAll('-','-<wbr>');
  }
  function softBreakURL(s) {
    const e = escapeHtml(s);
    return e
      .replaceAll('/', '/<wbr>')
      .replaceAll('.', '.<wbr>')
      .replaceAll('?', '?<wbr>')
      .replaceAll('=', '=<wbr>')
      .replaceAll('_', '_<wbr>')
      .replaceAll('-', '-<wbr>')
      .replaceAll('#', '#<wbr>');
  }

  function toCSV(rows) {
    const headers = ["exported","url","label","confidence","source","author"];
    const esc = s => ('"'+(s??'').toString().replaceAll('"','""')+'"');
    return [headers.join(","), ...rows.map(r => headers.map(h => esc(r[h])).join(","))].join("\n");
  }
  function download(name, text) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], {type:'text/csv'}));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }

  /* -------- Parse log text -------- */
  const lines = raw.split(/\r?\n/);
  let currentCourse = '';
  let exportedOn = '';
  let headerKeys = [];
  let inCSV = false;
  const allRows = [];

  function normalizeToFive(obj) {
    const f   = (obj.final_status || '').toLowerCase().trim();
    const vt  = (obj.vt_result || '').toLowerCase().trim();
    const pred= (obj.pred_label || obj.label || '').toLowerCase().trim();

    if (f) {
      if (/\b(phish|phishing)\b/.test(f)) return 'phish';
      if (/\badult\b/.test(f)) return 'adult';
      if (/\b(malware|malicious|unsafe)\b/.test(f)) return 'malware';
      if (/\b(suspicious)\b/.test(f)) return 'suspicious';
      if (/\b(safe|benign|clean)\b/.test(f)) return 'benign';
    }
    if (vt) {
      if (/\b(phish|phishing)\b/.test(vt)) return 'phish';
      if (/\badult\b/.test(vt)) return 'adult';
      if (/\b(malware|malicious|unsafe)\b/.test(vt)) return 'malware';
      if (/\b(suspicious)\b/.test(vt)) return 'suspicious';
    }
    if (/\b(phish|phishing)\b/.test(pred)) return 'phish';
    if (/\badult\b/.test(pred)) return 'adult';
    if (/\b(malware|malicious|unsafe)\b/.test(pred)) return 'malware';
    if (/\b(suspicious|unknown)\b/.test(pred)) return 'suspicious';
    if (/\b(safe|benign|clean)\b/.test(pred)) return 'benign';
    return 'benign';
  }

  function pushRow(obj) {
    // Heuristic for simple lines (no CSV header)
    if (!obj.pred_label && obj._rawParts && obj._rawParts.length >= 1) {
      const p = obj._rawParts.map(s => s.toLowerCase());
      const maybeLabel = p.find(x => /benign|safe|suspicious|phish|phishing|malware|malicious|adult/.test(x));
      const maybeConf  = p.slice().reverse().find(x => /^-?\d+(\.\d+)?$/.test(x)) || '';
      if (maybeLabel) obj.pred_label = maybeLabel;
      if (maybeConf)  obj.confidence = maybeConf;
    }

    const normalized = normalizeToFive(obj);
    const exportedTS = exportedOn ? new Date(exportedOn.replace(' ', 'T')) : new Date(0);

    allRows.push({
      course: currentCourse,
      exported: exportedOn,
      exportedTS,
      url: obj.url || '',
      label: normalized,
      displayLabel: (obj.final_status || obj.vt_result || obj.pred_label || normalized).toUpperCase(),
      confidence: (obj.confidence || '').trim(),
      source: (obj.source || '').trim(),
      author: (obj.author || obj.authorName || obj.authorusername || '').trim()
    });
  }

  for (let i=0; i<lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith('Course Name:')) {
      currentCourse = line.replace('Course Name:', '').trim();
      continue;
    }
    if (line.startsWith('Exported on:')) {
      exportedOn = line.replace('Exported on:', '').trim();
      continue;
    }

    if (/^url,/.test(line)) {
      headerKeys = line.split(',').map(h => h.trim().toLowerCase());
      inCSV = true;
      continue;
    }

    if (inCSV) {
      if (line.startsWith('--- ') || /^Course Name:/.test(line) || /^Exported on:/.test(line)) {
        inCSV = false;
        i--;    // re-process this line
        continue;
      }
      const vals = line.split(',').map(v => v.trim());
      const obj = {};
      headerKeys.forEach((h, idx) => obj[h] = vals[idx] || '');
      obj.author         = obj.authorusername || obj.author || '';
      obj.authorName     = obj.authorname || '';
      obj.authorusername = obj.authorusername || '';
      pushRow(obj);
      continue;
    }

    // Fallback: "url, label, confidence, source, author"
    if (/^https?:\/\//i.test(line)) {
      const parts = line.split(',').map(s => s.trim());
      pushRow({ url: parts[0] || '', _rawParts: parts.slice(1) });
    }
  }

  // Only rows for this course
  const rows = allRows.filter(r => r.course === selectedCourseName);

  // Newest first
  rows.sort((a, b) => b.exportedTS - a.exportedTS);

  /* -------- No rows? -------- */
  if (!rows.length) {
    emptyState.textContent = "No logs found for this course.";
    emptyState.classList.remove('d-none');
    return;
  }

  /* -------- Summary counts (all rows) -------- */
  let cBen=0, cSus=0, cPhi=0, cMal=0, cAdult=0;
  rows.forEach(r => {
    if (r.label === 'suspicious') cSus++;
    else if (r.label === 'phish') cPhi++;
    else if (r.label === 'malware') cMal++;
    else if (r.label === 'adult') cAdult++;
    else cBen++;
  });
  summaryRow.classList.remove('d-none');
  sumBenign.textContent     = cBen;
  sumSuspicious.textContent = cSus;
  sumPhish.textContent      = cPhi;
  sumMalware.textContent    = cMal;
  sumAdult.textContent      = cAdult;

  /* -------- Filtering + pagination helpers -------- */
  function getFilteredRows() {
    const lf = labelFilter.value;
    const fromVal = dateFrom.value ? new Date(dateFrom.value + 'T00:00:00').getTime() : null;
    const toVal   = dateTo.value   ? (new Date(dateTo.value + 'T00:00:00').getTime() + 86400000 - 1) : null;
    const urlText = urlFilter.value.trim().toLowerCase();

    const minRaw  = confMin.value.trim();
    const minConf = minRaw ? parseFloat(minRaw) : null;

    return rows.filter(r => {
      const matchLabel = (lf === 'all') ? true : (r.label === lf);
      const ts = r.exportedTS ? r.exportedTS.getTime() : 0;
      const matchFrom  = (fromVal === null) ? true : (ts >= fromVal);
      const matchTo    = (toVal   === null) ? true : (ts <= toVal);
      const matchUrl   = urlText ? r.url.toLowerCase().includes(urlText) : true;

      const confVal    = parseFloat(r.confidence || 'NaN');
      const matchConf  = (minConf === null || isNaN(minConf))
        ? true
        : (!isNaN(confVal) && confVal >= minConf);

      return matchLabel && matchFrom && matchTo && matchUrl && matchConf;
    });
  }

  function renderTable() {
    const filtered = getFilteredRows();
    tbody.innerHTML = '';

    if (!filtered.length) {
      emptyState.textContent = (dateFrom.value || dateTo.value || urlFilter.value || confMin.value)
        ? "No logs found for the selected filters."
        : "No logs match your filters.";
      emptyState.classList.remove('d-none');
      pagination.classList.add('d-none');
      return;
    }

    emptyState.classList.add('d-none');
    pagination.classList.remove('d-none');

    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / ROWS_PER_PAGE));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * ROWS_PER_PAGE;
    const end   = Math.min(start + ROWS_PER_PAGE, total);

    for (let i = start; i < end; i++) {
      const r = filtered[i];
      const [dPart, tPart] = (r.exported || '').split(' ');
      let badgeClass = 'badge-benign';
      if (r.label === 'suspicious') badgeClass = 'badge-suspicious';
      else if (r.label === 'phish') badgeClass = 'badge-phish';
      else if (r.label === 'malware') badgeClass = 'badge-malware';
      else if (r.label === 'adult') badgeClass = 'badge-adult';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="exported-cell">
          <span class="date">${escapeHtml(dPart || '')}</span>
          <span class="time">${escapeHtml(tPart || '')}</span>
        </td>
        <td class="url-cell">${softBreakURL(r.url)}</td>
        <td><span class="badge ${badgeClass} text-uppercase">${escapeHtml(r.displayLabel)}</span></td>
        <td>${escapeHtml(r.confidence || '—')}</td>
        <td>${softBreak(r.source || '—')}</td>
        <td>${softBreak(r.author || '—')}</td>
      `;
      tbody.appendChild(tr);
    }

    const shownOnPage = end - start;
    paginationInfo.textContent =
      `Page ${currentPage} of ${totalPages} • Showing ${shownOnPage} of ${total} rows`;

    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
  }

  /* -------- Filter events -------- */
  function onFilterChange() {
    currentPage = 1;
    renderTable();
  }
  [labelFilter, dateFrom, dateTo].forEach(el => el.addEventListener('change', onFilterChange));
  urlFilter.addEventListener('input', onFilterChange);
  confMin.addEventListener('input', onFilterChange);

  /* -------- Pagination events -------- */
  prevBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderTable();
    }
  });
  nextBtn.addEventListener('click', () => {
    currentPage++;
    renderTable();
  });

  /* -------- CSV download (current page only) -------- */
  document.getElementById('downloadBtn').addEventListener('click', function () {
    const filtered = getFilteredRows();
    if (!filtered.length) return;

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * ROWS_PER_PAGE;
    const end   = Math.min(start + ROWS_PER_PAGE, filtered.length);
    const pageRows = filtered.slice(start, end);

    const visible = pageRows.map(r => ({
      exported: r.exported,
      url: r.url,
      label: r.displayLabel,
      confidence: r.confidence || '—',
      source: r.source || '—',
      author: r.author || '—',
    }));

    const stamp = new Date().toISOString().slice(0,10);
    download(`manual_scan_logs_${stamp}.csv`, toCSV(visible));
  });

  /* Initial render */
  renderTable();
})();
