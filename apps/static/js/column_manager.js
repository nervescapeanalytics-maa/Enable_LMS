/**
 * Column Manager v5 — Show/hide & reorder columns across all Django admin tables.
 *
 * v5 changes (from v4):
 *   - Pointer-based drag-and-drop (replaces flaky HTML5 native DnD)
 *   - Searchable combobox at top of column list (filter as you type)
 *   - Auto-scroll while dragging near top/bottom of list
 *   - Stable per-model storage key in localStorage
 *   - Tested across browsers (Pointer Events Level 2)
 *
 * Storage key: "colmgr_<app>_<model>" (e.g. "colmgr_accounts_student")
 *   { hidden: [colIdx,...], order: [colIdx,...], _v: 5 }
 */
(function () {
  'use strict';

  var PREFS_VERSION = 5;

  // ── Storage helpers ─────────────────────────────────────────
  function getStorageKey() {
    var m = window.location.pathname.match(/\/admin\/([^/]+)\/([^/]+)\//);
    return m ? 'colmgr_' + m[1] + '_' + m[2] : null;
  }
  function savePrefs(key, prefs) {
    try { localStorage.setItem(key, JSON.stringify(prefs)); } catch (e) {}
  }
  function loadPrefs(key) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  // ── Column discovery ────────────────────────────────────────
  function discoverColumns(table) {
    var ths = table.querySelectorAll('thead th');
    var cols = [];
    ths.forEach(function (th, idx) {
      if (th.classList.contains('action-checkbox-column')) return;
      var textEl = th.querySelector('.text a') || th.querySelector('.text') || th;
      var text = textEl.textContent.trim().replace(/\s+/g, ' ');
      if (!text && idx === 0) return;
      cols.push({ idx: idx, text: text, id: 'col_' + idx });
    });
    return cols;
  }

  // Tag each cell with its original column index (run once)
  function tagCells(table) {
    table.querySelectorAll('tr').forEach(function (row) {
      Array.from(row.children).forEach(function (cell, i) {
        cell.setAttribute('data-orig-col', i);
      });
    });
  }

  // ── Apply preferences to the table ──────────────────────────
  function applyPrefs(table, prefs) {
    if (!prefs) return;

    var hiddenSet = {};
    if (prefs.hidden) prefs.hidden.forEach(function (i) { hiddenSet[i] = true; });

    table.querySelectorAll('tr').forEach(function (row) {
      var cells = Array.from(row.children);

      cells.forEach(function (cell) {
        var orig = parseInt(cell.getAttribute('data-orig-col'));
        if (isNaN(orig)) return;
        if (hiddenSet[orig]) cell.style.setProperty('display', 'none', 'important');
        else cell.style.removeProperty('display');
      });

      if (prefs.order && prefs.order.length > 0) {
        var byOrig = {};
        cells.forEach(function (c) {
          var o = parseInt(c.getAttribute('data-orig-col'));
          if (!isNaN(o)) byOrig[o] = c;
        });
        var managed = {};
        prefs.order.forEach(function (i) { managed[i] = true; });

        cells.forEach(function (c) {
          var o = parseInt(c.getAttribute('data-orig-col'));
          if (!managed[o]) row.appendChild(c);
        });
        prefs.order.forEach(function (o) {
          if (byOrig[o]) row.appendChild(byOrig[o]);
        });
      }
    });
  }

  // ── Build the picker panel ──────────────────────────────────
  function buildPanel(table, columns, storageKey) {
    var prefs = loadPrefs(storageKey) || { hidden: [], order: [] };

    var overlay = document.createElement('div');
    overlay.id = 'colmgr-overlay';
    overlay.style.cssText =
      'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.32);' +
      'backdrop-filter:blur(2px);z-index:10000;';

    var panel = document.createElement('div');
    panel.id = 'colmgr-panel';
    panel.style.cssText =
      'display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
      'z-index:10001;background:#fff;border:1px solid #e2e8f0;border-radius:12px;' +
      'box-shadow:0 12px 40px rgba(0,0,0,0.22);width:460px;max-width:92vw;' +
      'max-height:84vh;flex-direction:column;font-family:system-ui,sans-serif;';

    var header = document.createElement('div');
    header.style.cssText =
      'padding:14px 18px;border-bottom:1px solid #e2e8f0;display:flex;' +
      'align-items:center;justify-content:space-between;background:#f8fafc;' +
      'border-radius:12px 12px 0 0;';
    header.innerHTML =
      '<span style="font-weight:700;font-size:0.95rem;color:#1e293b;">' +
      '<i class="fas fa-columns" style="margin-right:8px;color:#844FC1;"></i>Column Settings</span>';
    var closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.style.cssText =
      'background:none;border:none;font-size:1.4rem;color:#64748b;cursor:pointer;line-height:1;padding:0 4px;';
    closeBtn.onclick = function () { closePanel(); };
    header.appendChild(closeBtn);
    panel.appendChild(header);

    var topBar = document.createElement('div');
    topBar.style.cssText =
      'padding:10px 18px;border-bottom:1px solid #e2e8f0;display:flex;flex-direction:column;gap:8px;background:#fff;';

    var help = document.createElement('div');
    help.style.cssText = 'font-size:0.76rem;color:#844FC1;line-height:1.4;background:rgba(132,79,193,0.06);border-radius:6px;padding:6px 10px;';
    help.innerHTML = 'Uncheck to hide. Drag <b>&#9776;</b> to reorder. Type to search columns. Saves automatically.';
    topBar.appendChild(help);

    var searchWrap = document.createElement('div');
    searchWrap.style.cssText = 'position:relative;';
    var searchIcon = document.createElement('i');
    searchIcon.className = 'fas fa-search';
    searchIcon.style.cssText = 'position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#94a3b8;font-size:0.75rem;pointer-events:none;';
    searchWrap.appendChild(searchIcon);
    var search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'Search columns…';
    search.autocomplete = 'off';
    search.spellcheck = false;
    search.style.cssText =
      'width:100%;box-sizing:border-box;padding:7px 10px 7px 28px;border:1px solid #cbd5e1;' +
      'border-radius:8px;font-size:0.83rem;outline:none;background:#fff;';
    search.addEventListener('focus', function () { search.style.borderColor = '#844FC1'; search.style.boxShadow = '0 0 0 3px rgba(132,79,193,0.18)'; });
    search.addEventListener('blur', function () { search.style.borderColor = '#cbd5e1'; search.style.boxShadow = 'none'; });
    searchWrap.appendChild(search);
    topBar.appendChild(searchWrap);

    var counter = document.createElement('div');
    counter.style.cssText = 'font-size:0.72rem;color:#94a3b8;';
    topBar.appendChild(counter);
    panel.appendChild(topBar);

    var listDiv = document.createElement('div');
    listDiv.style.cssText = 'padding:6px 0;overflow-y:auto;flex:1;min-height:120px;max-height:48vh;';
    listDiv.id = 'colmgr-list';

    var orderedCols = (prefs.order && prefs.order.length > 0)
      ? prefs.order.map(function (i) { return columns.find(function (c) { return c.idx === i; }); }).filter(Boolean)
      : columns.slice();
    columns.forEach(function (col) {
      if (!orderedCols.find(function (c) { return c.idx === col.idx; })) orderedCols.push(col);
    });

    var rows = [];
    orderedCols.forEach(function (col) {
      var row = document.createElement('div');
      row.dataset.colIdx = col.idx;
      row.dataset.colLabel = (col.text || '').toLowerCase();
      row.style.cssText =
        'display:flex;align-items:center;padding:8px 18px;gap:10px;' +
        'border-bottom:1px solid #f1f5f9;transition:background 0.12s;user-select:none;background:#fff;';

      var handle = document.createElement('span');
      handle.className = 'colmgr-handle';
      handle.textContent = '\u2630';
      handle.style.cssText = 'color:#94a3b8;font-size:1rem;cursor:grab;user-select:none;padding:2px 4px;touch-action:none;';
      handle.title = 'Drag to reorder';
      row.appendChild(handle);

      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = !(prefs.hidden && prefs.hidden.indexOf(col.idx) >= 0);
      cb.style.cssText = 'width:16px;height:16px;accent-color:#844FC1;cursor:pointer;flex-shrink:0;';
      cb.dataset.colIdx = col.idx;
      cb.addEventListener('change', function () { commit(); });
      row.appendChild(cb);

      var label = document.createElement('label');
      label.textContent = col.text || '(column ' + col.idx + ')';
      label.style.cssText = 'font-size:0.85rem;color:#334155;font-weight:500;flex:1;cursor:pointer;';
      label.addEventListener('click', function (e) { e.preventDefault(); cb.checked = !cb.checked; commit(); });
      row.appendChild(label);

      listDiv.appendChild(row);
      rows.push(row);
    });

    panel.appendChild(listDiv);

    var footer = document.createElement('div');
    footer.style.cssText =
      'padding:10px 18px;border-top:1px solid #e2e8f0;display:flex;' +
      'justify-content:space-between;align-items:center;background:#f8fafc;border-radius:0 0 12px 12px;';

    var resetBtn = document.createElement('button');
    resetBtn.textContent = 'Reset to Default';
    resetBtn.style.cssText =
      'background:rgba(220,38,38,0.08);color:#dc2626;border:1px solid rgba(220,38,38,0.2);' +
      'padding:6px 14px;border-radius:6px;font-size:0.78rem;font-weight:600;cursor:pointer;';
    resetBtn.onclick = function () {
      try { localStorage.removeItem(storageKey); } catch (e) {}
      window.location.reload();
    };
    footer.appendChild(resetBtn);

    var doneBtn = document.createElement('button');
    doneBtn.textContent = 'Done';
    doneBtn.style.cssText =
      'background:linear-gradient(135deg,#844FC1,#6D28D9);color:#fff;border:none;' +
      'padding:6px 18px;border-radius:6px;font-size:0.78rem;font-weight:600;cursor:pointer;';
    doneBtn.onclick = function () { closePanel(); };
    footer.appendChild(doneBtn);

    panel.appendChild(footer);

    overlay.onclick = function () { closePanel(); };
    document.body.appendChild(overlay);
    document.body.appendChild(panel);

    // ── Search filter ─────────────────────────────────────────
    function applyFilter() {
      var q = search.value.trim().toLowerCase();
      var shown = 0, total = rows.length;
      rows.forEach(function (r) {
        var match = !q || r.dataset.colLabel.indexOf(q) >= 0;
        r.style.display = match ? '' : 'none';
        if (match) shown++;
      });
      counter.textContent = q ? (shown + ' of ' + total + ' columns match') : (total + ' columns');
    }
    search.addEventListener('input', applyFilter);
    applyFilter();

    // ── Pointer-based drag and drop (handles only) ────────────
    var dragRow = null, placeholder = null;

    function onPointerDown(e) {
      var handle = e.target.closest('.colmgr-handle');
      if (!handle) return;
      var row = handle.closest('[data-col-idx]');
      if (!row) return;
      e.preventDefault();
      try { handle.setPointerCapture(e.pointerId); } catch (err) {}

      dragRow = row;
      var rect = row.getBoundingClientRect();
      row.style.opacity = '0.0';
      placeholder = document.createElement('div');
      placeholder.style.cssText =
        'height:' + rect.height + 'px;background:rgba(132,79,193,0.10);border:2px dashed #844FC1;' +
        'border-radius:6px;margin:0 12px;';
      row.parentNode.insertBefore(placeholder, row);

      var clone = row.cloneNode(true);
      clone.id = 'colmgr-drag-clone';
      clone.style.cssText =
        'position:fixed;left:' + rect.left + 'px;top:' + rect.top + 'px;width:' + rect.width + 'px;' +
        'pointer-events:none;background:#fff;box-shadow:0 8px 24px rgba(0,0,0,0.18);' +
        'border:1px solid #cbd5e1;border-radius:8px;z-index:10005;opacity:0.95;';
      document.body.appendChild(clone);
      dragRow._clone = clone;
      dragRow._offsetY = e.clientY - rect.top;

      window.addEventListener('pointermove', onPointerMove, { passive: false });
      window.addEventListener('pointerup', onPointerUp, { once: true });
      window.addEventListener('pointercancel', onPointerUp, { once: true });
    }

    function onPointerMove(e) {
      if (!dragRow) return;
      e.preventDefault();
      var clone = dragRow._clone;
      if (clone) clone.style.top = (e.clientY - dragRow._offsetY) + 'px';

      var y = e.clientY;
      var target = null;
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        if (r === dragRow || r.style.display === 'none') continue;
        var rb = r.getBoundingClientRect();
        if (y >= rb.top && y <= rb.bottom) { target = r; break; }
      }
      if (target) {
        var rb2 = target.getBoundingClientRect();
        var mid = rb2.top + rb2.height / 2;
        if (y < mid) target.parentNode.insertBefore(placeholder, target);
        else target.parentNode.insertBefore(placeholder, target.nextSibling);
      }

      var listRect = listDiv.getBoundingClientRect();
      if (y < listRect.top + 30) listDiv.scrollTop -= 8;
      else if (y > listRect.bottom - 30) listDiv.scrollTop += 8;
    }

    function onPointerUp() {
      window.removeEventListener('pointermove', onPointerMove);
      if (!dragRow) return;
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.insertBefore(dragRow, placeholder);
        placeholder.parentNode.removeChild(placeholder);
      }
      dragRow.style.opacity = '';
      if (dragRow._clone) {
        dragRow._clone.parentNode && dragRow._clone.parentNode.removeChild(dragRow._clone);
        dragRow._clone = null;
      }
      rows = Array.from(listDiv.querySelectorAll('[data-col-idx]'));
      dragRow = null;
      placeholder = null;
      commit();
    }

    listDiv.addEventListener('pointerdown', onPointerDown);

    // Keyboard reorder (Up/Down on focused row)
    listDiv.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
      var row = e.target.closest('[data-col-idx]');
      if (!row) return;
      e.preventDefault();
      if (e.key === 'ArrowUp' && row.previousSibling) row.parentNode.insertBefore(row, row.previousSibling);
      if (e.key === 'ArrowDown' && row.nextSibling) row.parentNode.insertBefore(row.nextSibling, row);
      rows = Array.from(listDiv.querySelectorAll('[data-col-idx]'));
      commit();
    });

    function commit() {
      var hidden = [], order = [];
      Array.from(listDiv.querySelectorAll('[data-col-idx]')).forEach(function (r) {
        var idx = parseInt(r.dataset.colIdx);
        var cb = r.querySelector('input[type="checkbox"]');
        order.push(idx);
        if (cb && !cb.checked) hidden.push(idx);
      });
      var p = { hidden: hidden, order: order, _v: PREFS_VERSION };
      savePrefs(storageKey, p);
      applyPrefs(table, p);
    }

    function openPanel() {
      overlay.style.display = 'block';
      panel.style.display = 'flex';
      setTimeout(function () { search.focus(); }, 50);
    }
    function closePanel() {
      overlay.style.display = 'none';
      panel.style.display = 'none';
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.style.display !== 'none') closePanel();
    });

    return { panel: panel, overlay: overlay, open: openPanel, close: closePanel };
  }

  function addColumnButton(table, columns, storageKey) {
    var ui = buildPanel(table, columns, storageKey);
    var toolbarUl = document.querySelector('.object-tools');

    var btn = document.createElement('a');
    btn.href = '#';
    btn.className = 'enf-action-btn secondary';
    btn.innerHTML = '<i class="fas fa-columns"></i> Columns';
    btn.onclick = function (e) { e.preventDefault(); ui.open(); };

    if (toolbarUl) {
      var li = document.createElement('li');
      li.appendChild(btn);
      toolbarUl.appendChild(li);
    }
  }

  function init() {
    var storageKey = getStorageKey();
    if (!storageKey) return;
    var table = document.querySelector('#result_list');
    if (!table) return;
    var columns = discoverColumns(table);
    if (columns.length === 0) return;

    tagCells(table);

    var prefs = loadPrefs(storageKey);
    if (prefs && prefs._v !== PREFS_VERSION) {
      try { localStorage.removeItem(storageKey); } catch (e) {}
      prefs = null;
    }
    if (prefs) applyPrefs(table, prefs);

    addColumnButton(table, columns, storageKey);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
