/* ══════════════════════════════════════════════════════════════════
   ENF ADMIN ENHANCEMENTS v4.0 — PURPLE EDITION
   ══════════════════════════════════════════════════════════════════ */
(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════
  // 1. SMOOTH PAGE TRANSITIONS
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    document.body.style.opacity = '0';
    requestAnimationFrame(function() {
      document.body.style.transition = 'opacity 0.3s ease';
      document.body.style.opacity = '1';
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 2. THEME SELECTOR — Light / Dark / Auto with localStorage
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var saved = localStorage.getItem('enf-theme') || 'light';

    function applyTheme(theme) {
      if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else if (theme === 'auto') {
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
          document.documentElement.setAttribute('data-theme', 'dark');
        } else {
          document.documentElement.removeAttribute('data-theme');
        }
      } else {
        document.documentElement.removeAttribute('data-theme');
      }
    }

    function updateThemeButtons(activeTheme) {
      var options = document.querySelectorAll('.enf-theme-option');
      options.forEach(function(opt) {
        var val = opt.getAttribute('data-theme-value');
        if (val === activeTheme) {
          opt.classList.add('active');
        } else {
          opt.classList.remove('active');
        }
      });
    }

    // Apply saved theme on load
    applyTheme(saved);

    // Wait for DOM to set active button
    updateThemeButtons(saved);

    // Listen for clicks on theme options
    var optionsContainer = document.getElementById('enf-theme-options');
    if (optionsContainer) {
      optionsContainer.addEventListener('click', function(e) {
        var option = e.target.closest('.enf-theme-option');
        if (!option) return;
        var theme = option.getAttribute('data-theme-value');
        localStorage.setItem('enf-theme', theme);
        applyTheme(theme);
        updateThemeButtons(theme);
      });
    }

    // Listen for system theme changes when "auto" is selected
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
      if (localStorage.getItem('enf-theme') === 'auto') {
        applyTheme('auto');
      }
    });

    // Also support legacy toggle checkbox if present
    var toggle = document.getElementById('enf-theme-toggle');
    if (toggle) {
      toggle.checked = (saved === 'dark');
      toggle.addEventListener('change', function() {
        var theme = this.checked ? 'dark' : 'light';
        localStorage.setItem('enf-theme', theme);
        applyTheme(theme);
        updateThemeButtons(theme);
      });
    }
  });

  // ═══════════════════════════════════════════════════════════════════
  // 3. ADMIN PROFILE DROPDOWN
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('enf-profile-toggle');
    var dropdown = document.getElementById('enf-profile-dropdown');
    if (!btn || !dropdown) return;

    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      dropdown.classList.toggle('active');
    });

    document.addEventListener('click', function(e) {
      if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 4. SIDEBAR EXPAND/COLLAPSE — APP GROUP LEVEL ONLY (caption)
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.getElementById('nav-sidebar');
    if (!sidebar) return;

    // Only target caption elements (app group headers), NOT th (individual models)
    var captions = sidebar.querySelectorAll('.module caption');
    captions.forEach(function(caption) {
      // Add collapse icon
      var icon = document.createElement('i');
      icon.className = 'fas fa-chevron-down enf-collapse-icon';
      caption.appendChild(icon);

      // Get the table containing this caption — hide/show all tr (model rows)
      var table = caption.closest('table');
      if (!table) return;
      var rows = table.querySelectorAll('tr');

      // Load saved state
      var key = 'enf-sidebar-' + (caption.textContent || '').trim().replace(/\s+/g, '-').toLowerCase();
      var savedState = localStorage.getItem(key);
      if (savedState === 'collapsed') {
        caption.classList.add('collapsed');
        rows.forEach(function(r) { r.style.display = 'none'; });
      }

      caption.addEventListener('click', function(e) {
        e.preventDefault();
        var isCollapsed = caption.classList.contains('collapsed');
        if (isCollapsed) {
          caption.classList.remove('collapsed');
          rows.forEach(function(r) { r.style.display = ''; });
          localStorage.setItem(key, 'expanded');
        } else {
          caption.classList.add('collapsed');
          rows.forEach(function(r) { r.style.display = 'none'; });
          localStorage.setItem(key, 'collapsed');
        }
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 5. ENHANCED CHECKBOX — Row highlighting
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var selectAll = document.getElementById('action-toggle');
    if (!selectAll) return;

    function highlightRows() {
      document.querySelectorAll('#result_list tbody tr').forEach(function(row) {
        var cb = row.querySelector('input[type="checkbox"]');
        if (cb && cb.checked) {
          row.style.background = 'rgba(132, 79, 193, 0.08)';
        } else {
          row.style.background = '';
        }
      });
    }

    selectAll.addEventListener('change', function() {
      setTimeout(highlightRows, 50);
    });

    document.querySelectorAll('#result_list input[type="checkbox"]').forEach(function(cb) {
      cb.addEventListener('change', highlightRows);
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 6. ANIMATED STAT COUNTERS
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.enf-stat-value').forEach(function(el) {
      var target = parseInt(el.textContent, 10);
      if (isNaN(target) || target === 0) return;
      var duration = 800;
      var start = 0;
      var startTime = null;

      function animate(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(animate);
      }
      el.textContent = '0';
      requestAnimationFrame(animate);
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 7. SEARCH ENHANCEMENT (Ctrl+K)
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var searchBar = document.getElementById('searchbar');
    if (searchBar) {
      searchBar.style.minWidth = '300px';
      searchBar.setAttribute('placeholder', 'Search... (Ctrl+K)');
    }

    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (searchBar) searchBar.focus();
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 8. TABLE ROW CLICK-TO-EDIT
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('#result_list tbody tr').forEach(function(row) {
      row.style.cursor = 'pointer';
      row.addEventListener('click', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'A' || e.target.tagName === 'SELECT') return;
        var link = row.querySelector('th a, td a');
        if (link) window.location = link.href;
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 9. FIX ACTION DROPDOWN SELECTION
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var actionSelects = document.querySelectorAll('.actions select, select[name="action"]');
    actionSelects.forEach(function(sel) {
      sel.style.pointerEvents = 'auto';
      sel.style.position = 'relative';
      sel.style.zIndex = '30';
      sel.style.opacity = '1';
      sel.style.cursor = 'pointer';

      // Remove any overlay that might block
      var parent = sel.parentElement;
      if (parent) {
        parent.style.position = 'relative';
        parent.style.zIndex = '30';
        parent.style.overflow = 'visible';
      }

      // Force enable
      sel.disabled = false;
      sel.removeAttribute('disabled');
    });

    // Also fix the Go button
    var goButtons = document.querySelectorAll('.actions .button, .actions button[type="submit"]');
    goButtons.forEach(function(btn) {
      btn.style.pointerEvents = 'auto';
      btn.style.position = 'relative';
      btn.style.zIndex = '30';
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 10. COLUMN-LEVEL DROPDOWN FILTERING
  //     Uses data-orig-col attribute (set by column_manager.js) so
  //     filters work correctly even after column reorder / hide.
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var resultList = document.getElementById('result_list');
    if (!resultList) return;

    var headerCells = resultList.querySelectorAll('thead th');
    var bodyRows = resultList.querySelectorAll('tbody tr');
    if (!headerCells.length || !bodyRows.length) return;

    // Helper: find cell in a row by its original column index (data-orig-col).
    // Falls back to positional index if tags haven't been set yet.
    function getCellByOrigCol(row, origCol) {
      var cell = row.querySelector('[data-orig-col="' + origCol + '"]');
      if (cell) return cell;
      // Fallback: positional index
      var cells = row.querySelectorAll('td, th');
      return cells[origCol] || null;
    }

    // Track active filters keyed by *original* column index (string)
    var activeFilters = {};

    // ── Server-side column filter (Excel-style, applies to ALL records) ──
    // Builds an icon + popover that fetches distinct values via AJAX from
    // <changelist-url>_filter-choices/?field=<fieldName>, then navigates the
    // browser to ?<fieldName>=<value> so Django list_filter does the filtering.
    function buildServerFilter(th, fieldName) {
      var url = new URL(window.location.href);
      var currentVal = url.searchParams.get(fieldName) || '';

      var wrapper = document.createElement('span');
      wrapper.className = 'enf-col-filter-wrapper';

      var trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'enf-col-filter-trigger';
      trigger.innerHTML = '<i class="fas fa-filter"></i>';
      trigger.title = 'Filter all records by this column';
      if (currentVal) {
        trigger.classList.add('has-filter', 'active');
        var badge = document.createElement('span');
        badge.className = 'enf-col-filter-count';
        badge.textContent = '1';
        trigger.appendChild(badge);
      }

      var dropdown = document.createElement('div');
      dropdown.className = 'enf-col-filter-dropdown';

      var search = document.createElement('input');
      search.type = 'text';
      search.className = 'enf-col-filter-search';
      search.placeholder = 'Search…';
      dropdown.appendChild(search);

      var optionsContainer = document.createElement('div');
      optionsContainer.className = 'enf-col-filter-options';
      optionsContainer.innerHTML = '<div style="padding:18px;text-align:center;color:#94a3b8;font-size:0.78rem;">Loading…</div>';
      dropdown.appendChild(optionsContainer);

      var loaded = false;
      function navigate(value) {
        var u = new URL(window.location.href);
        if (value === null || value === '') u.searchParams.delete(fieldName);
        else u.searchParams.set(fieldName, value);
        u.searchParams.delete('p');
        window.location.href = u.toString();
      }

      function loadChoices() {
        if (loaded) return;
        loaded = true;
        var endpoint = window.location.pathname.replace(/\/$/, '') + '/_filter-choices/?field=' + encodeURIComponent(fieldName)
          + '&' + window.location.search.replace(/^\?/, '');
        fetch(endpoint, { credentials: 'same-origin' })
          .then(function(r) { return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function(data) {
            optionsContainer.innerHTML = '';
            var allOpt = document.createElement('button');
            allOpt.type = 'button';
            allOpt.className = 'enf-col-filter-option' + (currentVal === '' ? ' selected' : '');
            allOpt.innerHTML = '<input type="checkbox" tabindex="-1"' + (currentVal === '' ? ' checked' : '') + '> <span>(All)</span>';
            allOpt.addEventListener('click', function(e) { e.stopPropagation(); navigate(''); });
            optionsContainer.appendChild(allOpt);
            (data.choices || []).forEach(function(c) {
              var label = c.label || c.value;
              var opt = document.createElement('button');
              opt.type = 'button';
              opt.className = 'enf-col-filter-option' + (currentVal === c.value ? ' selected' : '');
              opt.setAttribute('data-value', c.value);
              opt.innerHTML = '<input type="checkbox" tabindex="-1"' + (currentVal === c.value ? ' checked' : '') + '> '
                + '<span>' + escapeHtml(label) + '</span>'
                + '<span style="margin-left:auto;font-size:0.72rem;color:var(--text-muted);">' + c.count + '</span>';
              opt.addEventListener('click', function(e) { e.stopPropagation(); navigate(c.value); });
              optionsContainer.appendChild(opt);
            });
            if (!(data.choices || []).length) {
              optionsContainer.innerHTML = '<div style="padding:18px;text-align:center;color:#94a3b8;font-size:0.78rem;">No values available.</div>';
            }
          })
          .catch(function() {
            optionsContainer.innerHTML = '<div style="padding:18px;text-align:center;color:#dc2626;font-size:0.78rem;">Failed to load values.</div>';
          });
      }

      search.addEventListener('input', function() {
        var q = search.value.toLowerCase();
        optionsContainer.querySelectorAll('.enf-col-filter-option').forEach(function(opt) {
          var t = (opt.textContent || '').toLowerCase();
          opt.style.display = t.indexOf(q) >= 0 ? '' : 'none';
        });
      });
      search.addEventListener('click', function(e) { e.stopPropagation(); });

      trigger.addEventListener('click', function(e) {
        e.stopPropagation(); e.preventDefault();
        document.querySelectorAll('.enf-col-filter-dropdown.active').forEach(function(d) {
          if (d !== dropdown) {
            d.classList.remove('active');
            if (d._enfTrigger && !d._enfTrigger.classList.contains('has-filter')) d._enfTrigger.classList.remove('active');
          }
        });
        dropdown.classList.toggle('active');
        if (dropdown.classList.contains('active')) {
          var rect = trigger.getBoundingClientRect();
          var dropW = 280;
          var left = rect.right - dropW;
          if (left < 8) left = 8;
          if (left + dropW > window.innerWidth - 8) left = window.innerWidth - dropW - 8;
          dropdown.style.top = (rect.bottom + 4) + 'px';
          dropdown.style.left = left + 'px';
          trigger.classList.add('active');
          setTimeout(function() { search.focus(); }, 50);
          loadChoices();
        } else if (!trigger.classList.contains('has-filter')) {
          trigger.classList.remove('active');
        }
      });

      dropdown._enfTrigger = trigger;
      wrapper.appendChild(trigger);
      document.body.appendChild(dropdown);

      var thContent = document.createElement('span');
      thContent.className = 'enf-th-content';
      while (th.firstChild) thContent.appendChild(th.firstChild);
      thContent.appendChild(wrapper);
      th.appendChild(thContent);
    }

    // Build column data for each filterable column (skip checkbox column)
    headerCells.forEach(function(th, colIndex) {
      // Skip the checkbox column (first column)
      if (colIndex === 0) return;

      // Determine the stable original column index — set by column_manager.js
      // before any reorder/hide is applied. Falls back to the visible position
      // when not yet tagged.
      var origCol = th.getAttribute('data-orig-col');
      if (origCol === null || origCol === undefined) origCol = String(colIndex);
      else origCol = String(origCol);

      // Server-side filter (Django list_filter backed) — preferred when available.
      // ENF_FILTER_FIELDS is injected by enhanced_change_list.html and is keyed
      // by the *original* list_display index, so we must look it up by origCol
      // (not by the current visible position which may have been reordered).
      var fieldMap = window.ENF_FILTER_FIELDS || {};
      var serverField = fieldMap[origCol] || fieldMap[String(colIndex)];
      if (serverField) {
        buildServerFilter(th, serverField);
        return;
      }

      // Collect unique values for this column using data-orig-col lookup
      var values = [];
      var valueCounts = {};
      bodyRows.forEach(function(row) {
        var cell = getCellByOrigCol(row, origCol);
        if (cell) {
          var text = cell.textContent.trim();
          if (text && text !== '-' && text !== '') {
            if (!valueCounts[text]) {
              valueCounts[text] = 0;
              values.push(text);
            }
            valueCounts[text]++;
          }
        }
      });

      // Sort values alphabetically
      values.sort(function(a, b) { return a.localeCompare(b); });

      // Only add filter if there are 1+ unique values but less than 200
      if (values.length < 1 || values.length > 200) return;

      // Create filter wrapper
      var wrapper = document.createElement('span');
      wrapper.className = 'enf-col-filter-wrapper';

      // Create trigger button
      var trigger = document.createElement('button');
      trigger.className = 'enf-col-filter-trigger';
      trigger.type = 'button';
      trigger.innerHTML = '<i class="fas fa-filter"></i>';
      trigger.title = 'Filter this column';

      // Create dropdown
      var dropdown = document.createElement('div');
      dropdown.className = 'enf-col-filter-dropdown';

      // Search input
      var searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'enf-col-filter-search';
      searchInput.placeholder = 'Search...';
      dropdown.appendChild(searchInput);

      // Options container
      var optionsContainer = document.createElement('div');
      optionsContainer.className = 'enf-col-filter-options';

      values.forEach(function(val) {
        var option = document.createElement('button');
        option.type = 'button';
        option.className = 'enf-col-filter-option';
        option.setAttribute('data-value', val);
        option.innerHTML = '<input type="checkbox" tabindex="-1"> <span>' + escapeHtml(val) + '</span> <span style="margin-left:auto;font-size:0.72rem;color:var(--text-muted);">' + valueCounts[val] + '</span>';
        option.addEventListener('click', function(e) {
          e.stopPropagation();
          var cb = option.querySelector('input[type="checkbox"]');
          cb.checked = !cb.checked;
          option.classList.toggle('selected', cb.checked);

          // Update active filters (keyed by origCol string)
          if (!activeFilters[origCol]) activeFilters[origCol] = new Set();
          if (cb.checked) {
            activeFilters[origCol].add(val);
          } else {
            activeFilters[origCol].delete(val);
          }
          applyFilters();
          updateTriggerState(trigger, origCol);
        });
        optionsContainer.appendChild(option);
      });
      dropdown.appendChild(optionsContainer);

      // Footer with clear/apply
      var footer = document.createElement('div');
      footer.className = 'enf-col-filter-footer';

      var clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'enf-col-filter-clear';
      clearBtn.textContent = 'Clear';
      clearBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (activeFilters[origCol]) activeFilters[origCol].clear();
        optionsContainer.querySelectorAll('.enf-col-filter-option').forEach(function(opt) {
          opt.classList.remove('selected');
          opt.querySelector('input[type="checkbox"]').checked = false;
        });
        applyFilters();
        updateTriggerState(trigger, origCol);
      });

      var applyBtn = document.createElement('button');
      applyBtn.type = 'button';
      applyBtn.className = 'enf-col-filter-apply';
      applyBtn.textContent = 'Done';
      applyBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.remove('active');
        trigger.classList.remove('active');
      });

      footer.appendChild(clearBtn);
      footer.appendChild(applyBtn);
      dropdown.appendChild(footer);

      // Search filtering
      searchInput.addEventListener('input', function() {
        var term = searchInput.value.toLowerCase();
        optionsContainer.querySelectorAll('.enf-col-filter-option').forEach(function(opt) {
          var val = opt.getAttribute('data-value').toLowerCase();
          opt.style.display = val.indexOf(term) >= 0 ? '' : 'none';
        });
      });
      searchInput.addEventListener('click', function(e) { e.stopPropagation(); });

      // Toggle dropdown — uses fixed positioning on body for z-index safety
      trigger.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        // Close all other open dropdowns
        document.querySelectorAll('.enf-col-filter-dropdown.active').forEach(function(d) {
          if (d !== dropdown) {
            d.classList.remove('active');
            if (d._enfTrigger && !d._enfTrigger.classList.contains('has-filter')) {
              d._enfTrigger.classList.remove('active');
            }
          }
        });
        dropdown.classList.toggle('active');
        if (dropdown.classList.contains('active')) {
          // Position dropdown using fixed coords from trigger's bounding rect
          var rect = trigger.getBoundingClientRect();
          var dropW = 280;
          var left = rect.right - dropW;
          if (left < 8) left = 8;
          if (left + dropW > window.innerWidth - 8) left = window.innerWidth - dropW - 8;
          dropdown.style.top = (rect.bottom + 4) + 'px';
          dropdown.style.left = left + 'px';
          trigger.classList.add('active');
          setTimeout(function() { searchInput.focus(); }, 50);
        } else {
          if (!trigger.classList.contains('has-filter')) {
            trigger.classList.remove('active');
          }
        }
      });

      // Store cross-references for outside-click handler
      dropdown._enfTrigger = trigger;

      wrapper.appendChild(trigger);
      // Append dropdown to body so it's not clipped by overflow:hidden
      document.body.appendChild(dropdown);

      // Wrap existing th content + filter in a single inline-flex line
      var thContent = document.createElement('span');
      thContent.className = 'enf-th-content';
      // Move existing children (text nodes, links, sort icons) into the wrapper
      while (th.firstChild) {
        thContent.appendChild(th.firstChild);
      }
      thContent.appendChild(wrapper);
      th.appendChild(thContent);
    });

    // Close all dropdowns when clicking outside
    document.addEventListener('click', function() {
      document.querySelectorAll('.enf-col-filter-dropdown.active').forEach(function(d) {
        d.classList.remove('active');
        if (d._enfTrigger && !d._enfTrigger.classList.contains('has-filter')) {
          d._enfTrigger.classList.remove('active');
        }
      });
    });

    // Reposition open dropdowns on scroll/resize
    function repositionOpenDropdowns() {
      document.querySelectorAll('.enf-col-filter-dropdown.active').forEach(function(d) {
        if (d._enfTrigger) {
          var rect = d._enfTrigger.getBoundingClientRect();
          var dropW = 280;
          var left = rect.right - dropW;
          if (left < 8) left = 8;
          if (left + dropW > window.innerWidth - 8) left = window.innerWidth - dropW - 8;
          d.style.top = (rect.bottom + 4) + 'px';
          d.style.left = left + 'px';
        }
      });
    }
    window.addEventListener('scroll', repositionOpenDropdowns, true);
    window.addEventListener('resize', repositionOpenDropdowns);

    function updateTriggerState(trigger, colIndex) {
      var count = activeFilters[colIndex] ? activeFilters[colIndex].size : 0;
      var badge = trigger.querySelector('.enf-col-filter-count');
      if (count > 0) {
        trigger.classList.add('has-filter');
        trigger.classList.add('active');
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'enf-col-filter-count';
          trigger.appendChild(badge);
        }
        badge.textContent = count;
      } else {
        trigger.classList.remove('has-filter');
        if (badge) badge.remove();
      }
    }

    function applyFilters() {
      bodyRows.forEach(function(row) {
        var visible = true;

        for (var origCol in activeFilters) {
          if (!activeFilters.hasOwnProperty(origCol)) continue;
          var filterSet = activeFilters[origCol];
          if (filterSet.size === 0) continue;

          var cell = getCellByOrigCol(row, origCol);
          var cellText = cell ? cell.textContent.trim() : '';
          if (!filterSet.has(cellText)) {
            visible = false;
            break;
          }
        }

        row.style.display = visible ? '' : 'none';
      });

      // Update result count in action bar
      var visibleCount = 0;
      bodyRows.forEach(function(row) {
        if (row.style.display !== 'none') visibleCount++;
      });
      var counter = document.querySelector('.actions .action-counter');
      if (counter) {
        var totalCount = bodyRows.length;
        var hasFilters = Object.keys(activeFilters).some(function(k) { return activeFilters[k].size > 0; });
        if (hasFilters) {
          counter.textContent = visibleCount + ' of ' + totalCount + ' shown (filtered)';
        }
      }
    }

    function escapeHtml(text) {
      var div = document.createElement('div');
      div.appendChild(document.createTextNode(text));
      return div.innerHTML;
    }
  });

  // ── EXTRACT ACTIVE FILTERS from hidden #changelist-filter ──
  document.addEventListener('DOMContentLoaded', function() {
    var changelistFilter = document.getElementById('changelist-filter');
    var hasActiveFilter = false;
    var pillsHtml = '<span class="enf-filter-label"><i class="fas fa-filter" style="margin-right:4px;"></i>Active Filters:</span>';

    // Check URL params for date hierarchy filters too
    var urlParams = new URLSearchParams(window.location.search);
    var dateFields = [];
    urlParams.forEach(function(val, key) {
      // Date hierarchy params: field__year, field__month, field__day
      if (key.match(/__(?:year|month|day)$/)) {
        dateFields.push({ key: key, val: val });
      }
    });
    if (dateFields.length > 0) {
      hasActiveFilter = true;
      var dateLabel = 'Date: ' + dateFields.map(function(d) { return d.val; }).join('/');
      var clearDateUrl = new URL(window.location.href);
      dateFields.forEach(function(d) { clearDateUrl.searchParams.delete(d.key); });
      pillsHtml += '<a href="' + clearDateUrl.pathname + (clearDateUrl.search || '') + '" class="enf-filter-pill">' + dateLabel + ' <i class="fas fa-times enf-pill-remove"></i></a>';
    }

    if (changelistFilter) {
      var selectedFilters = changelistFilter.querySelectorAll('li.selected');
      // Default "All" / "Any date" texts that indicate NO active filter
      var DEFAULT_TEXTS = ['All', 'Any date', 'Any time', 'Any status'];

      selectedFilters.forEach(function(li) {
        var a = li.querySelector('a');
        if (!a) return;
        var filterText = a.textContent.trim();
        // Skip default "unfiltered" selections
        if (DEFAULT_TEXTS.indexOf(filterText) >= 0) return;
        // Also skip if the link href is just "?" (reset link)
        var href = a.getAttribute('href') || '';
        if (href === '?') return;

        // Get filter category from Django 5.x <details data-filter-title> / <summary>
        var category = '';
        var details = li.closest('details[data-filter-title]');
        if (details) {
          category = (details.getAttribute('data-filter-title') || '').trim();
          // Capitalize first letter
          if (category) category = category.charAt(0).toUpperCase() + category.slice(1);
        }
        if (!category) {
          // Fallback: try <summary> sibling or <h3> sibling (Django 4.x)
          var parent = li.parentElement;
          if (parent) {
            var summary = parent.previousElementSibling;
            if (summary && summary.tagName === 'SUMMARY') {
              category = summary.textContent.replace(/^\s*By\s+/i, '').trim();
            } else {
              var prev = parent;
              while (prev && prev.previousElementSibling) {
                prev = prev.previousElementSibling;
                if (prev.tagName === 'H3') { category = prev.textContent.replace(/[^a-zA-Z0-9\s]/g, '').trim(); break; }
              }
            }
          }
        }
        var label = category ? category + ': ' + filterText : filterText;

        // Find the "All" link for this filter group to build removal URL
        var allLink = '?';
        var siblings = li.parentElement.querySelectorAll('li');
        siblings.forEach(function(sib) {
          var sibA = sib.querySelector('a');
          if (sibA) {
            var sibText = sibA.textContent.trim();
            if (sibText === 'All' || sibText === 'Any date') {
              allLink = sibA.href;
            }
          }
        });

        hasActiveFilter = true;
        pillsHtml += '<a href="' + allLink + '" class="enf-filter-pill">' + label + ' <i class="fas fa-times enf-pill-remove"></i></a>';
      });
    }

    if (hasActiveFilter) {
      // Clear All: strip ALL query params → go to clean changelist URL
      var cleanUrl = window.location.pathname;
      pillsHtml += '<a href="' + cleanUrl + '" class="enf-clear-all-filters"><i class="fas fa-times-circle"></i> Clear All</a>';
      var pillsContainer = document.createElement('div');
      pillsContainer.className = 'enf-active-filters';
      pillsContainer.innerHTML = pillsHtml;

      // Insert before results
      var results = document.querySelector('#changelist .results') || document.querySelector('#changelist form');
      if (results) {
        results.parentNode.insertBefore(pillsContainer, results);
      }
    }

    // ── Date Range Picker (replaces date hierarchy) ──
    // Django 5.x renders date hierarchy as <nav class="toplinks">, older as .xfull
    var dateHierarchy = document.querySelector('nav.toplinks') || document.querySelector('.xfull');
    var resultList = document.getElementById('result_list');
    if (resultList) {
      // Detect the date hierarchy field name from the nav links or URL params
      var dateFieldName = null;
      if (dateHierarchy) {
        // Hide the native date hierarchy
        dateHierarchy.style.display = 'none';
        // Parse the links to find the field name
        var dhLinks = dateHierarchy.querySelectorAll('a');
        dhLinks.forEach(function(a) {
          var href = a.getAttribute('href') || '';
          var m = href.match(/([a-z_]+)__(?:year|month|day|gte|lt)=/);
          if (m) dateFieldName = m[1];
        });
      }
      // Also check URL params
      if (!dateFieldName) {
        urlParams.forEach(function(val, key) {
          var m = key.match(/^([a-z_]+)__(?:year|month|day|gte|lt)$/);
          if (m) dateFieldName = m[1];
        });
      }
      // Fallback: check the filter sidebar for date-related filters
      if (!dateFieldName && changelistFilter) {
        var dateDetail = changelistFilter.querySelector('details[data-filter-title*="date"]');
        if (dateDetail) {
          var dateLink = dateDetail.querySelector('a[href*="__gte"]');
          if (dateLink) {
            var m2 = (dateLink.getAttribute('href') || '').match(/([a-z_]+)__gte=/);
            if (m2) dateFieldName = m2[1];
          }
        }
      }

      if (dateFieldName) {
        // Read existing date params
        // Read existing __gte/__lt params (new range format)
        var existingFrom = urlParams.get(dateFieldName + '__gte') || '';
        var existingTo = urlParams.get(dateFieldName + '__lt') || '';
        // Also read legacy date_hierarchy params for backward compat
        if (!existingFrom) {
          var existingYear = urlParams.get(dateFieldName + '__year') || '';
          var existingMonth = urlParams.get(dateFieldName + '__month') || '';
          var existingDay = urlParams.get(dateFieldName + '__day') || '';
          if (existingYear) {
            existingFrom = existingYear + '-' + (existingMonth || '01').padStart(2, '0') + '-' + (existingDay || '01').padStart(2, '0');
            if (existingDay) {
              existingTo = existingFrom;
            } else if (existingMonth) {
              var lastDay = new Date(parseInt(existingYear), parseInt(existingMonth), 0).getDate();
              existingTo = existingYear + '-' + existingMonth.padStart(2, '0') + '-' + lastDay;
            } else {
              existingTo = existingYear + '-12-31';
            }
          }
        }
        // For __lt the value is the day after, so convert back for display
        if (existingTo && existingTo.length === 10 && !urlParams.get(dateFieldName + '__lt')) {
          // already display-ready
        } else if (existingTo && existingTo.length === 10) {
          // __lt value is exclusive (day after), subtract 1 day for display
          var d = new Date(existingTo);
          d.setDate(d.getDate() - 1);
          existingTo = d.toISOString().slice(0, 10);
        }

        var rangeHtml =
          '<div class="enf-date-range">' +
          '<label><i class="fas fa-calendar-alt" style="margin-right:4px;"></i>Date Range:</label>' +
          '<input type="date" id="enf-date-from" value="' + existingFrom + '" title="From date">' +
          '<span style="color:var(--text-muted);font-size:0.75rem;">to</span>' +
          '<input type="date" id="enf-date-to" value="' + existingTo + '" title="To date">' +
          '<button type="button" class="enf-date-apply" id="enf-date-apply">Apply</button>' +
          '<button type="button" class="enf-date-clear" id="enf-date-clear">Clear</button>' +
          '</div>';

        // Insert date range picker. If active filters row exists, append to it. Otherwise create one.
        var filtersRow = document.querySelector('.enf-active-filters');
        if (filtersRow) {
          var rangeDiv = document.createElement('div');
          rangeDiv.innerHTML = rangeHtml;
          filtersRow.appendChild(rangeDiv.firstChild);
        } else {
          var dateRow = document.createElement('div');
          dateRow.className = 'enf-active-filters';
          dateRow.innerHTML = rangeHtml;
          var resEl = document.querySelector('#changelist .results') || document.querySelector('#changelist form');
          if (resEl) resEl.parentNode.insertBefore(dateRow, resEl);
        }

        // Bind apply
        var applyBtn = document.getElementById('enf-date-apply');
        var fromInput = document.getElementById('enf-date-from');
        var toInput = document.getElementById('enf-date-to');
        if (applyBtn) {
          applyBtn.addEventListener('click', function() {
            var from = fromInput.value;
            var to = toInput.value;
            if (!from && !to) return;
            var url = new URL(window.location.href);
            // Remove ALL old date params (hierarchy + range)
            Array.from(url.searchParams.keys()).forEach(function(k) {
              if (k.match(new RegExp('^' + dateFieldName + '__'))) url.searchParams.delete(k);
            });
            // Use __gte / __lt for proper date range filtering
            if (from) {
              url.searchParams.set(dateFieldName + '__gte', from);
            }
            if (to) {
              // __lt is exclusive, so add 1 day to include the "to" date
              var toDate = new Date(to);
              toDate.setDate(toDate.getDate() + 1);
              var ltVal = toDate.toISOString().slice(0, 10);
              url.searchParams.set(dateFieldName + '__lt', ltVal);
            }
            url.searchParams.delete('p'); // reset pagination
            window.location.href = url.toString();
          });
        }
        var clearBtn = document.getElementById('enf-date-clear');
        if (clearBtn) {
          clearBtn.addEventListener('click', function() {
            var url = new URL(window.location.href);
            Array.from(url.searchParams.keys()).forEach(function(k) {
              if (k.match(new RegExp('^' + dateFieldName + '__'))) url.searchParams.delete(k);
            });
            window.location.href = url.toString();
          });
        }
      }
    }
  });

  // ═══════════════════════════════════════════════════════════════════
  // 10b. BACK BUTTON ON CHANGE/ADD FORMS
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    // Only add on add/change form pages (not changelist, not dashboard)
    var h1 = document.querySelector('#content > h1');
    if (!h1) return;
    var title = h1.textContent.trim().toLowerCase();
    var isChangeForm = title.indexOf('change ') === 0 || title.indexOf('add ') === 0;
    if (!isChangeForm) return;

    // Build the back URL from breadcrumbs
    var breadcrumbs = document.querySelectorAll('.breadcrumbs a');
    var backUrl = null;
    if (breadcrumbs.length >= 2) {
      // The second-to-last breadcrumb link is the changelist
      backUrl = breadcrumbs[breadcrumbs.length - 1].href;
    }
    if (!backUrl) return;

    var backBtn = document.createElement('a');
    backBtn.href = backUrl;
    backBtn.className = 'enf-back-btn';
    backBtn.innerHTML = '<i class="fas fa-arrow-left"></i> Back';
    backBtn.title = 'Back to list';
    h1.parentNode.insertBefore(backBtn, h1);
  });

  // ═══════════════════════════════════════════════════════════════════
  // 11. TOAST NOTIFICATIONS
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.messagelist li').forEach(function(msg) {
      msg.style.animation = 'fadeIn 0.4s ease-out';
      setTimeout(function() {
        msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        msg.style.opacity = '0';
        msg.style.transform = 'translateY(-10px)';
        setTimeout(function() { msg.style.display = 'none'; }, 500);
      }, 5000);
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 12. KEYBOARD SHORTCUTS PANEL
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var modal = document.createElement('div');
    modal.className = 'enf-modal-overlay';
    modal.id = 'enf-shortcuts-modal';
    modal.innerHTML = '<div class="enf-modal" style="max-width:420px;">' +
      '<h3><i class="fas fa-keyboard" style="color:#844FC1;margin-right:8px;"></i>Keyboard Shortcuts</h3>' +
      '<div style="display:grid;gap:8px;">' +
      '<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border-color);"><span style="color:var(--text-secondary);font-size:0.88rem;">Search</span><kbd style="background:var(--primary-light);color:var(--primary);padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;">Ctrl + K</kbd></div>' +
      '<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border-color);"><span style="color:var(--text-secondary);font-size:0.88rem;">Go to Dashboard</span><kbd style="background:var(--primary-light);color:var(--primary);padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;">G then D</kbd></div>' +
      '<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="color:var(--text-secondary);font-size:0.88rem;">Show Shortcuts</span><kbd style="background:var(--primary-light);color:var(--primary);padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;">Shift + ?</kbd></div>' +
      '</div>' +
      '<button onclick="document.getElementById(\'enf-shortcuts-modal\').classList.remove(\'active\')" style="position:absolute;top:12px;right:12px;background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:1.2rem;"><i class="fas fa-times"></i></button>' +
      '</div>';
    document.body.appendChild(modal);

    window._enfGPressed = false;
    document.addEventListener('keydown', function(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

      if (e.key === '?' && e.shiftKey) {
        e.preventDefault();
        modal.classList.toggle('active');
        return;
      }
      if (e.key === 'Escape') {
        modal.classList.remove('active');
        return;
      }
      if (e.key === 'g' || e.key === 'G') {
        window._enfGPressed = true;
        setTimeout(function() { window._enfGPressed = false; }, 1500);
        return;
      }
      if (e.key === 'd' && window._enfGPressed) {
        window._enfGPressed = false;
        window.location = '/admin/';
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 13. SIDEBAR MODULE COLLAPSE TOGGLE (Dashboard index modules)
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('#content-main .module caption, .app-label').forEach(function(cap) {
      cap.style.cursor = 'pointer';
      cap.title = 'Click to collapse/expand';
      cap.addEventListener('click', function() {
        var table = cap.closest('table') || cap.closest('.module');
        if (!table) return;
        var rows = table.querySelectorAll('tr:not(:first-child), tbody');
        rows.forEach(function(r) {
          r.style.display = r.style.display === 'none' ? '' : 'none';
        });
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 12. INLINE DELETE CHECKBOX → STYLED BUTTON
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    // Target all delete cells in inline groups (both existing and dynamically added)
    function convertDeleteCheckboxes() {
      var deleteCells = document.querySelectorAll('.inline-group td.delete');
      if (!deleteCells.length) return;

      deleteCells.forEach(function(td) {
        // Skip if already converted
        if (td.querySelector('.enf-delete-btn')) return;

        var cb = td.querySelector('input[type="checkbox"]');
        if (!cb) return;

        // Hide original checkbox & label
        cb.style.display = 'none';
        var lbl = td.querySelector('label');
        if (lbl) lbl.style.display = 'none';

        // Create styled button
        var btn = document.createElement('a');
        btn.href = '#';
        btn.className = 'enf-delete-btn';
        btn.innerHTML = '✕ Remove';
        btn.title = 'Mark for deletion (save to confirm)';

        // If already checked (e.g. page reload), show active state
        if (cb.checked) {
          btn.classList.add('enf-delete-active');
          btn.innerHTML = '↩ Undo';
          var row = td.closest('tr');
          if (row) row.style.opacity = '0.45';
        }

        btn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          cb.checked = !cb.checked;
          cb.dispatchEvent(new Event('change', { bubbles: true }));
          var row = td.closest('tr');
          if (cb.checked) {
            btn.classList.add('enf-delete-active');
            btn.innerHTML = '↩ Undo';
            if (row) row.style.opacity = '0.45';
          } else {
            btn.classList.remove('enf-delete-active');
            btn.innerHTML = '✕ Remove';
            if (row) row.style.opacity = '1';
          }
        });

        td.appendChild(btn);
      });
    }

    // Run immediately
    convertDeleteCheckboxes();

    // Also convert when new inline rows are added (Django "Add another" button)
    var addButtons = document.querySelectorAll('.inline-group .add-row a, .inline-group .grp-add-handler');
    addButtons.forEach(function(addBtn) {
      addBtn.addEventListener('click', function() {
        setTimeout(convertDeleteCheckboxes, 100);
      });
    });

    // MutationObserver fallback for dynamically added rows
    var inlineGroups = document.querySelectorAll('.inline-group');
    inlineGroups.forEach(function(group) {
      var observer = new MutationObserver(function() {
        convertDeleteCheckboxes();
      });
      observer.observe(group, { childList: true, subtree: true });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 13. INLINE TABLE COLUMN FILTERS
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var inlineTables = document.querySelectorAll('.inline-group table');
    if (!inlineTables.length) return;

    var filterSVG = '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">'
      + '<path d="M1.5 1.5h13L9.5 7.7V13l-3 1.5V7.7z"/></svg>';

    inlineTables.forEach(function(table) {
      var headerRow = table.querySelector('thead tr');
      if (!headerRow) return;

      var ths = headerRow.querySelectorAll('th');
      var body = table.querySelector('tbody');
      if (!body) return;

      // Identify filterable columns (skip original, skip empty headers)
      ths.forEach(function(th, colIdx) {
        // Skip original column and columns with no text
        if (th.classList.contains('original')) return;
        var headerText = (th.textContent || '').trim();
        if (!headerText || headerText.length < 2) return;

        // Make th position relative for dropdown
        th.style.position = 'relative';

        // Add filter icon
        var icon = document.createElement('span');
        icon.className = 'enf-inline-filter-icon';
        icon.innerHTML = filterSVG;
        icon.title = 'Filter ' + headerText;
        th.appendChild(icon);

        var dropdown = null;
        var activeFilter = null; // null = no filter

        icon.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();

          // Close any other open filter dropdowns
          document.querySelectorAll('.enf-inline-filter-dropdown').forEach(function(d) {
            d.remove();
          });
          document.querySelectorAll('.enf-inline-filter-icon.enf-filter-active').forEach(function(ic) {
            if (ic !== icon && !ic._hasFilter) ic.classList.remove('enf-filter-active');
          });

          // Collect unique values from this column
          var values = [];
          var seen = {};
          var rows = body.querySelectorAll('tr.form-row');
          rows.forEach(function(row) {
            if (row.classList.contains('empty-form')) return;
            var cells = row.querySelectorAll('td');
            if (colIdx >= cells.length) return;
            var cell = cells[colIdx];
            // Skip original/hidden cells
            if (cell.classList.contains('original')) return;

            var val = '';
            // For select/autocomplete fields, get selected option text
            var sel = cell.querySelector('select');
            if (sel && sel.selectedIndex >= 0) {
              val = sel.options[sel.selectedIndex].text;
            }
            // For Select2 widgets
            if (!val || val === '---------') {
              var s2 = cell.querySelector('.select2-selection__rendered');
              if (s2) val = s2.textContent || s2.innerText || '';
            }
            // For readonly/text content
            if (!val || val === '---------') {
              val = cell.textContent || cell.innerText || '';
            }
            val = val.trim();
            if (val && val !== '---------' && !seen[val]) {
              seen[val] = true;
              values.push(val);
            }
          });

          values.sort();

          // Build dropdown
          dropdown = document.createElement('div');
          dropdown.className = 'enf-inline-filter-dropdown';

          // Search input
          var search = document.createElement('input');
          search.type = 'text';
          search.className = 'enf-inline-filter-search';
          search.placeholder = 'Search…';
          dropdown.appendChild(search);

          // "All" option
          var allItem = document.createElement('div');
          allItem.className = 'enf-inline-filter-item' + (activeFilter === null ? ' enf-selected' : '');
          allItem.textContent = '(All)';
          allItem.addEventListener('click', function() {
            activeFilter = null;
            icon._hasFilter = false;
            icon.classList.remove('enf-filter-active');
            applyFilter(body, colIdx, null);
            dropdown.remove();
          });
          dropdown.appendChild(allItem);

          // Value items
          values.forEach(function(v) {
            var item = document.createElement('div');
            item.className = 'enf-inline-filter-item' + (activeFilter === v ? ' enf-selected' : '');
            item.textContent = v;
            item.addEventListener('click', function() {
              activeFilter = v;
              icon._hasFilter = true;
              icon.classList.add('enf-filter-active');
              applyFilter(body, colIdx, v);
              dropdown.remove();
            });
            dropdown.appendChild(item);
          });

          // Search filtering within dropdown
          search.addEventListener('input', function() {
            var q = search.value.toLowerCase();
            dropdown.querySelectorAll('.enf-inline-filter-item').forEach(function(item) {
              if (item.textContent === '(All)') {
                item.style.display = '';
              } else {
                item.style.display = item.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
              }
            });
          });

          th.appendChild(dropdown);

          // Focus search
          setTimeout(function() { search.focus(); }, 50);
        });
      });
    });

    function applyFilter(tbody, colIdx, filterVal) {
      var rows = tbody.querySelectorAll('tr.form-row');
      rows.forEach(function(row) {
        if (row.classList.contains('empty-form')) return;
        // Don't filter the "Add another" row
        if (row.classList.contains('add-row')) return;

        if (filterVal === null) {
          row.style.display = '';
          return;
        }

        var cells = row.querySelectorAll('td');
        if (colIdx >= cells.length) return;
        var cell = cells[colIdx];

        var val = '';
        var sel = cell.querySelector('select');
        if (sel && sel.selectedIndex >= 0) {
          val = sel.options[sel.selectedIndex].text;
        }
        if (!val || val === '---------') {
          var s2 = cell.querySelector('.select2-selection__rendered');
          if (s2) val = s2.textContent || s2.innerText || '';
        }
        if (!val || val === '---------') {
          val = cell.textContent || cell.innerText || '';
        }
        val = val.trim();

        row.style.display = (val === filterVal) ? '' : 'none';
      });
    }

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.enf-inline-filter-dropdown') && !e.target.closest('.enf-inline-filter-icon')) {
        document.querySelectorAll('.enf-inline-filter-dropdown').forEach(function(d) {
          d.remove();
        });
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // 14. STICKY HORIZONTAL SCROLLBAR (always visible at top of changelist)
  //     Adds a synced "phantom" scrollbar above the result table so users
  //     can pan a wide table without scrolling to the bottom of the page.
  // ═══════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    var resultList = document.getElementById('result_list');
    if (!resultList) return;
    // Find the scroll container — Django wraps the table in <div class="results">
    var scrollHost = resultList.closest('.results') || resultList.parentElement;
    if (!scrollHost) return;

    // Ensure the host actually scrolls horizontally
    var hostStyle = window.getComputedStyle(scrollHost);
    if (hostStyle.overflowX === 'visible') scrollHost.style.overflowX = 'auto';

    // Build a sticky bar that mirrors table width
    var stickyWrap = document.createElement('div');
    stickyWrap.className = 'enf-sticky-scroll';
    stickyWrap.style.cssText =
      'position:sticky;top:0;z-index:50;height:18px;overflow-x:auto;overflow-y:hidden;'
      + 'background:linear-gradient(180deg,#f1f5f9,#e2e8f0);margin-bottom:-18px;'
      + 'border-bottom:1px solid #cbd5e1;border-radius:0 0 9px 9px;';
    var inner = document.createElement('div');
    inner.style.cssText = 'height:1px;';
    stickyWrap.appendChild(inner);
    scrollHost.parentElement.insertBefore(stickyWrap, scrollHost);

    function syncWidth() {
      inner.style.width = resultList.scrollWidth + 'px';
    }
    syncWidth();
    window.addEventListener('resize', syncWidth);

    var lock = false;
    stickyWrap.addEventListener('scroll', function() {
      if (lock) { lock = false; return; }
      lock = true;
      scrollHost.scrollLeft = stickyWrap.scrollLeft;
    });
    scrollHost.addEventListener('scroll', function() {
      if (lock) { lock = false; return; }
      lock = true;
      stickyWrap.scrollLeft = scrollHost.scrollLeft;
    });

    // If column manager mutates table width, re-measure
    var mo = new MutationObserver(syncWidth);
    mo.observe(resultList, { attributes: true, childList: true, subtree: true });
  });

})();
