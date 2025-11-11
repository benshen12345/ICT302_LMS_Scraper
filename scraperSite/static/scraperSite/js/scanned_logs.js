(function () {
  const raw = document.getElementById('rawLog').value || '';
  const tbody = document.querySelector('#logsTable tbody');
  const emptyState = document.getElementById('emptyState');

  const courseSelect = document.getElementById('courseSelect');
  const labelFilter  = document.getElementById('labelFilter');
  const dateFrom     = document.getElementById('dateFrom');
  const dateTo       = document.getElementById('dateTo');
  const confMin      = document.getElementById('confMin');
  const urlFilter    = document.getElementById('urlFilter');

  const summaryRow   = document.getElementById('summaryRow');
  const sumBenign    = document.getElementById('sumBenign');
  const sumSuspicious= document.getElementById('sumSuspicious');
  const sumPhish     = document.getElementById('sumPhish');
  const sumMalware   = document.getElementById('sumMalware');
  const sumAdult     = document.getElementById('sumAdult');

  const paginationControls = document.getElementById('paginationControls');
  const paginationInfo     = document.getElementById('paginationInfo');
  const prevPageBtn        = document.getElementById('prevPageBtn');
  const nextPageBtn        = document.getElementById('nextPageBtn');

  const rowsPerPage = 20;
  let currentPage = 1;
  let filteredRowsCache = [];

  /* ---------- helpers: safe HTML + soft breaks ---------- */
  function escapeHtml(s) {
    return String(s ?? '')
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }
  // Insert optional breaks after _ and - (shown only when needed)
  function softBreak(s) {
    const e = escapeHtml(s);
    return e.replaceAll('_','_<wbr>').replaceAll('-','-<wbr>');
  }
  // Friendlier breaks for URLs (avoid breaking &amp;)
  function softBreakURL(s) {
    const e = escapeHtml(s);
    return e
      .replaceAll('/', '/<wbr>')
      .replaceAll('.', '.<wbr>')
      .replaceAll('?', '?<wbr>')
      // no & here — would split HTML entities
      .replaceAll('=', '=<wbr>')
      .replaceAll('_', '_<wbr>')
      .replaceAll('-', '-<wbr>')
      .replaceAll('#', '#<wbr>');
  }

  function toCSV(rows) {
    const headers = ["course","exported","url","label","confidence","source","author"];
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
  const rows = [];

  function normalizeToFive(obj) {
    const f = (obj.final_status || '').toLowerCase().trim();
    const vt = (obj.vt_result || '').toLowerCase().trim();
    const pred = (obj.pred_label || obj.label || '').toLowerCase().trim();

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
    if (!obj.pred_label && obj._rawParts && obj._rawParts.length >= 1) {
      const p = obj._rawParts.map(s => s.toLowerCase());
      const maybeLabel = p.find(x => /benign|safe|suspicious|phish|phishing|malware|malicious|adult/.test(x));
      const maybeConf  = p.slice().reverse().find(x => /^-?\d+(\.\d+)?$/.test(x)) || '';
      if (maybeLabel) obj.pred_label = maybeLabel;
      if (maybeConf)  obj.confidence = maybeConf;
    }

    const normalized = normalizeToFive(obj);
    const exportedTS = exportedOn ? new Date(exportedOn.replace(' ', 'T')) : new Date(0);

    rows.push({
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

    if (line.startsWith('Course Name:')) { currentCourse = line.replace('Course Name:', '').trim(); continue; }
    if (line.startsWith('Exported on:')) { exportedOn = line.replace('Exported on:', '').trim(); continue; }

    if (/^url,/.test(line)) {
      headerKeys = line.split(',').map(h => h.trim().toLowerCase());
      inCSV = true; continue;
    }

    if (inCSV) {
      if (line.startsWith('--- ') || /^Course Name:/.test(line) || /^Exported on:/.test(line)) {
        inCSV = false; i--; continue;
      }
      const vals = line.split(',').map(v => v.trim());
      const obj = {};
      headerKeys.forEach((h, idx) => obj[h] = vals[idx] || '');
      obj.author = obj.authorusername || obj.author || '';
      obj.authorName = obj.authorname || '';
      obj.authorusername = obj.authorusername || '';
      pushRow(obj);
      continue;
    }

    if (/^https?:\/\//i.test(line)) {
      const parts = line.split(',').map(s => s.trim());
      pushRow({ url: parts[0] || '', _rawParts: parts.slice(1) });
    }
  }

  // newest first
  rows.sort((a, b) => b.exportedTS - a.exportedTS);

  /* -------- Render rows -------- */
  if (!rows.length) {
    emptyState.textContent = "No logs available.";
    emptyState.classList.remove('d-none');
  } else {
    const frag = document.createDocumentFragment();

    rows.forEach(r => {
      const [dPart, tPart] = (r.exported || '').split(' ');
      let badgeClass = 'badge-benign';
      if (r.label === 'suspicious')      { badgeClass = 'badge-suspicious'; }
      else if (r.label === 'phish')     { badgeClass = 'badge-phish'; }
      else if (r.label === 'malware')   { badgeClass = 'badge-malware'; }
      else if (r.label === 'adult')     { badgeClass = 'badge-adult'; }

      const tr = document.createElement('tr');
      tr.setAttribute('data-label', r.label);
      tr.dataset.ts   = String(r.exportedTS.getTime());
      tr.dataset.conf = isNaN(parseFloat(r.confidence)) ? "" : String(parseFloat(r.confidence));
      tr.dataset.courseFull = r.course || '';

      tr.innerHTML = `
        <td>${softBreak(r.course)}</td>
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
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);

    // Populate course dropdown
    const set = new Set();
    Array.from(tbody.rows).forEach(r => set.add(r.dataset.courseFull));
    const courses = Array.from(set).filter(Boolean).sort((a,b)=>a.localeCompare(b));
    const fragOpts = document.createDocumentFragment();
    courses.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      fragOpts.appendChild(opt);
    });
    courseSelect.appendChild(fragOpts);

    // Initial filters + summary + pagination
    applyFilters(true);
  }

  /* -------- Summary update (uses filtered rows) -------- */
  function updateSummary(rowsList) {
    let cBen=0, cSus=0, cPhi=0, cMal=0, cAdult=0;

    rowsList.forEach(r => {
      const label = r.getAttribute('data-label');
      if (label === 'suspicious') cSus++;
      else if (label === 'phish') cPhi++;
      else if (label === 'malware') cMal++;
      else if (label === 'adult') cAdult++;
      else cBen++;
    });

    summaryRow.classList.remove('d-none');
    sumBenign.textContent     = cBen;
    sumSuspicious.textContent = cSus;
    sumPhish.textContent      = cPhi;
    sumMalware.textContent    = cMal;
    sumAdult.textContent      = cAdult;
  }

  /* -------- Filters + Pagination -------- */
  function applyFilters(resetPage) {
    if (resetPage) currentPage = 1;

    const selectedCourse = courseSelect.value; // 'all' or exact course name
    const lf = labelFilter.value;
    const fromVal = dateFrom.value ? new Date(dateFrom.value + 'T00:00:00').getTime() : null;
    const toVal   = dateTo.value   ? (new Date(dateTo.value + 'T00:00:00').getTime() + 86400000 - 1) : null;
    const minRaw  = confMin.value.trim();
    const minConf = minRaw ? parseFloat(minRaw) : null;
    const urlQuery = urlFilter.value.trim().toLowerCase();

    const allRowsDom = Array.from(tbody.rows);
    filteredRowsCache = [];

    allRowsDom.forEach(row => {
      const matchCourse = (selectedCourse === 'all') ? true : (row.dataset.courseFull === selectedCourse);
      const matchesLabel  = (lf === 'all') ? true : row.getAttribute('data-label') === lf;
      const rowTs         = parseInt(row.dataset.ts || '0', 10);
      const rowConf       = parseFloat(row.dataset.conf || 'NaN');

      const matchFrom = (fromVal === null) ? true : (rowTs >= fromVal);
      const matchTo   = (toVal   === null) ? true : (rowTs <= toVal);
      const matchConf = (minConf === null || isNaN(minConf)) ? true : (!isNaN(rowConf) && rowConf >= minConf);

      const urlText = (row.cells[2]?.innerText || '').toLowerCase();
      const matchUrl = urlQuery ? urlText.includes(urlQuery) : true;

      const matches = matchCourse && matchesLabel && matchFrom && matchTo && matchConf && matchUrl;

      row.style.display = 'none'; // hide first; we'll show selected after
      if (matches) filteredRowsCache.push(row);
    });

    const total = filteredRowsCache.length;

    // update top summary for CURRENT FILTERED rows
    updateSummary(filteredRowsCache);

    if (!total) {
      emptyState.textContent = "No logs match your filters.";
      emptyState.classList.remove('d-none');
      if (paginationControls) paginationControls.classList.add('d-none');
      return;
    } else {
      emptyState.classList.add('d-none');
    }

    const totalPages = Math.max(1, Math.ceil(total / rowsPerPage));
    if (currentPage > totalPages) currentPage = totalPages;

    const startIdx = (currentPage - 1) * rowsPerPage;
    const endIdx   = Math.min(startIdx + rowsPerPage, total);

    filteredRowsCache.slice(startIdx, endIdx).forEach(row => {
      row.style.display = '';
    });

    if (paginationControls) {
      paginationControls.classList.remove('d-none');
      paginationInfo.textContent = `Page ${currentPage} of ${totalPages} • Showing ${endIdx - startIdx} of ${total} rows`;
      prevPageBtn.disabled = currentPage <= 1;
      nextPageBtn.disabled = currentPage >= totalPages;
    }
  }

  [courseSelect, labelFilter, dateFrom, dateTo].forEach(el =>
    el.addEventListener('change', () => applyFilters(true))
  );
  confMin.addEventListener('input', () => applyFilters(true));
  urlFilter.addEventListener('input', () => applyFilters(true));

  if (prevPageBtn && nextPageBtn) {
    prevPageBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        applyFilters(false);
      }
    });
    nextPageBtn.addEventListener('click', () => {
      currentPage++;
      applyFilters(false);
    });
  }

  // CSV (all filtered rows, ignoring pagination)
  document.getElementById('downloadBtn').addEventListener('click', function () {
    const baseRows = filteredRowsCache.length ? filteredRowsCache : Array.from(tbody.rows);
    const data = baseRows.map(r => ({
      course: r.cells[0].innerText.trim(),
      exported: (r.querySelector('.exported-cell .date')?.innerText || '') + ' ' +
                (r.querySelector('.exported-cell .time')?.innerText || ''),
      url: r.cells[2].innerText.trim(),
      label: r.cells[3].innerText.trim(),
      confidence: r.cells[4].innerText.trim(),
      source: r.cells[5].innerText.trim(),
      author: r.cells[6].innerText.trim(),
    }));
    const stamp = new Date().toISOString().slice(0,10);
    download(`scanned_logs_${stamp}.csv`, toCSV(data));
  });
})();
