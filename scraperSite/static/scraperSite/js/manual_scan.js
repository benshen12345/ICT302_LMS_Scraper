// Use injected data from template (see manual_scan.html)
const injectedCourseManagers = window.courseManagers || {};
const hasScanResultPopup = !!window.hasScanResultPopup;

// ===== Pagination globals =====
const ROWS_PER_PAGE = 10;
let currentPage = 1;
let allCourseRows = [];
let filteredCourseRows = [];
let selectedCourseId = null;

// ===== Helper: render scan result into nice UI =====
function renderScanResultFromRaw() {
  const pre = document.getElementById('scanResultRaw');
  if (!pre) return;

  const text = (pre.innerText || pre.textContent || '').trim();
  if (!text) return;

  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);

  const summaryEls = {
    reportId: document.getElementById('summaryReportId'),
    reportDate: document.getElementById('summaryReportDate'),
    totalLinks: document.getElementById('summaryTotalLinks'),
    safeLinks: document.getElementById('summarySafeLinks'),
    suspicious: document.getElementById('summarySuspicious'),
    malicious: document.getElementById('summaryMalicious'),
  };

  const unsafeListEl = document.getElementById('unsafeUrlList');
  const noUnsafeMsgEl = document.getElementById('noUnsafeUrlsMsg');

  let inUnsafeSection = false;

  lines.forEach(line => {
    if (line.startsWith('--- Report')) {
      // Example: --- Report 46 (2025-11-07) ---
      const m = /Report\s+(\S+)\s+\(([^)]+)\)/.exec(line);
      if (m) {
        if (summaryEls.reportId) summaryEls.reportId.textContent = m[1];
        if (summaryEls.reportDate) summaryEls.reportDate.textContent = m[2];
      }
    } else if (line.startsWith('Total Links:')) {
      const val = line.split(':')[1]?.trim() || '';
      if (summaryEls.totalLinks) summaryEls.totalLinks.textContent = val;
    } else if (line.startsWith('Safe Links:')) {
      const val = line.split(':')[1]?.trim() || '';
      if (summaryEls.safeLinks) summaryEls.safeLinks.textContent = val;
    } else if (line.startsWith('Suspicious:')) {
      // Example: Suspicious: 0, Malicious: 1
      const m = /Suspicious:\s*([^,]+),\s*Malicious:\s*(.+)/.exec(line);
      if (m) {
        if (summaryEls.suspicious) summaryEls.suspicious.textContent = m[1].trim();
        if (summaryEls.malicious) summaryEls.malicious.textContent = m[2].trim();
      }
    } else if (line.startsWith('Unsafe URLs:')) {
      inUnsafeSection = true;
    } else if (inUnsafeSection && line.startsWith('- ')) {
      const urlText = line.substring(2).trim();
      if (unsafeListEl) {
        const li = document.createElement('li');
        li.textContent = urlText;
        unsafeListEl.appendChild(li);
      }
    }
  });

  if (unsafeListEl && noUnsafeMsgEl) {
    const hasItems = unsafeListEl.children.length > 0;
    noUnsafeMsgEl.style.display = hasItems ? 'none' : 'block';
    unsafeListEl.style.display = hasItems ? 'block' : 'none';
  }
}

// ===== Pagination helpers =====
function highlightSelectedRow() {
  allCourseRows.forEach(row => {
    if (row.getAttribute('data-course-id') === selectedCourseId) {
      row.classList.add('selected');
    } else {
      row.classList.remove('selected');
    }
  });
}

function updatePaginationAndTable() {
  const noResultsRow  = document.getElementById('noResultsRow');
  const pagination    = document.getElementById('coursePaginationWrapper');
  const info          = document.getElementById('coursePaginationInfo');
  const prevBtn       = document.getElementById('coursePrevPage');
  const nextBtn       = document.getElementById('courseNextPage');

  // hide all rows first
  allCourseRows.forEach(row => {
    row.style.display = 'none';
  });

  const total = filteredCourseRows.length;

  if (!total) {
    if (noResultsRow) noResultsRow.style.display = '';
    if (pagination)  pagination.style.display = 'none';
    if (info)        info.textContent = '';
    return;
  }

  if (noResultsRow) noResultsRow.style.display = 'none';
  if (pagination)   pagination.style.display = 'flex';

  const totalPages = Math.max(1, Math.ceil(total / ROWS_PER_PAGE));
  if (currentPage > totalPages) currentPage = totalPages;

  const startIdx = (currentPage - 1) * ROWS_PER_PAGE;
  const endIdx   = Math.min(startIdx + ROWS_PER_PAGE, total);

  // show only rows for this page
  for (let i = startIdx; i < endIdx; i++) {
    filteredCourseRows[i].style.display = '';
  }

  // keep selected row highlighted
  highlightSelectedRow();

  if (info) {
    info.textContent =
      `Page ${currentPage} of ${totalPages} • ` +
      `Showing ${endIdx - startIdx} of ${total} rows`;
  }

  // 🔒 disable / enable buttons correctly
  if (prevBtn) prevBtn.disabled = currentPage === 1;
  if (nextBtn) nextBtn.disabled = currentPage === totalPages;
}

// ===== Filtering (now tied to pagination) =====
function filterCourses() {
  const input = document.getElementById('courseFilter');
  if (!input) return;

  const query = input.value.toLowerCase().trim();

  filteredCourseRows = allCourseRows.filter(row => {
    const courseNameCell = row.cells[0];
    const courseName = (courseNameCell.textContent || courseNameCell.innerText).toLowerCase();
    return !query || courseName.includes(query);
  });

  currentPage = 1;
  updatePaginationAndTable();
}

// ===== Row selection & scan button =====
function selectCourse(courseId) {
  selectedCourseId = courseId || null;
  highlightSelectedRow();

  const hiddenInput = document.getElementById('courseIdInput');
  if (hiddenInput) hiddenInput.value = courseId || '';

  // Handle "View Scanned Log" URL
  const viewLogBtn = document.getElementById('viewLogBtn');
  if (viewLogBtn) {
    const baseUrl = viewLogBtn.dataset.baseUrl || viewLogBtn.getAttribute('href');
    if (courseId) {
      viewLogBtn.href = baseUrl + '?course_id=' + encodeURIComponent(courseId);
    } else {
      viewLogBtn.removeAttribute('href');
    }
  }

  toggleScanButton();
}

function toggleScanButton() {
  const hiddenInput = document.getElementById('courseIdInput');
  const scanBtn = document.getElementById('scanBtn');
  const viewLogBtn = document.getElementById('viewLogBtn');

  const hasSelection = !!(hiddenInput && hiddenInput.value);

  if (scanBtn) {
    scanBtn.disabled = !hasSelection;
  }

  if (viewLogBtn) {
    if (hasSelection) {
      viewLogBtn.classList.remove('disabled-link');
    } else {
      viewLogBtn.classList.add('disabled-link');
    }
  }
}

// ===== Popup close =====
function closeScanPopup() {
  const popup = document.getElementById('scanResultPopup');
  if (popup) popup.style.display = 'none';
}

// ===== Page initialisation =====
document.addEventListener('DOMContentLoaded', function () {
  // 1. Populate manager / email columns (ONLY real course rows)
  const courseRowsNodeList = document.querySelectorAll('#courseTableBody tr[data-course-id]');
  allCourseRows = Array.from(courseRowsNodeList);
  filteredCourseRows = allCourseRows.slice(); // initial: all rows

  allCourseRows.forEach(row => {
    const courseId = row.getAttribute('data-course-id');
    const managerCell = row.querySelector('.col-managers');
    const emailCell = row.querySelector('.col-emails');
    const managers = injectedCourseManagers[courseId] || [];

    if (!managers.length) {
      if (managerCell) managerCell.textContent = '—';
      if (emailCell) emailCell.textContent = '—';
    } else {
      if (managerCell) managerCell.innerHTML = managers.map(m => m.name).join('<br>');
      if (emailCell) emailCell.innerHTML = managers.map(m => m.email).join('<br>');
    }
  });

  // 2. Initially disable scan button (and keep log button faded)
  toggleScanButton();

  // 3. Attach submit handler to show scanning overlay
  const form = document.getElementById('manualScanForm');
  if (form) {
    form.addEventListener('submit', function () {
      const overlay = document.getElementById('scanningOverlay');
      if (overlay) overlay.style.display = 'flex';
    });
  }

  // Ensure overlay is hidden when page is loaded / reloaded
  const overlay = document.getElementById('scanningOverlay');
  if (overlay) overlay.style.display = 'none';

  // 4. Show popup if we have scan results
  if (hasScanResultPopup) {
    renderScanResultFromRaw();
    const popup = document.getElementById('scanResultPopup');
    if (popup) popup.style.display = 'flex';
  }

  // 5. Hide "no results" row initially (pagination will control it later)
  const noResultsRow = document.getElementById('noResultsRow');
  if (noResultsRow) noResultsRow.style.display = 'none';

  // 6. Pagination buttons
  const prevBtn = document.getElementById('coursePrevPage');
  const nextBtn = document.getElementById('courseNextPage');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        updatePaginationAndTable();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      currentPage++;
      updatePaginationAndTable();
    });
  }

  // 7. Initial render (page 1)
  updatePaginationAndTable();
});
