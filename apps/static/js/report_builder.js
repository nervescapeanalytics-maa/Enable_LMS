/**
 * Report Builder — Dynamic column/filter/group_by/sort_by suggestions
 * based on the selected report_type. Updates TagListWidget suggestions on change.
 */
(function() {
  'use strict';

  // Per-report-type column suggestions (mirrors REPORT_TYPE_COLUMNS in forms.py)
  var TYPE_COLUMNS = {
    'STUDENT': ['student_name','student_id','roll_number','email','phone','class_name','section','batch','center','admission_date','date_of_birth','gender','status','parent_name','parent_phone','address','academic_year','semester','created_at'],
    'TEACHER': ['teacher_name','teacher_id','email','phone','subject','department','designation','qualification','date_of_joining','experience_years','status','classes_assigned','center','created_at'],
    'ATTENDANCE': ['student_name','roll_number','class_name','section','batch','attendance_date','status','attendance_percentage','present_count','absent_count','late_count','leave_count','teacher_name','subject','center','month','week'],
    'EXAM': ['student_name','roll_number','exam_name','subject','total_marks','obtained_marks','percentage','grade','rank','class_name','section','batch','center','exam_date','academic_year','semester','status'],
    'CENTER': ['center_name','center_code','address','city','state','student_count','teacher_count','batch_count','active_classes','attendance_rate','avg_score','status','established_date','contact_person','phone'],
    'FINANCIAL': ['student_name','roll_number','fee_type','fee_amount','paid_amount','due_amount','discount','payment_date','payment_mode','payment_status','receipt_number','class_name','batch','center','academic_year','semester'],
    'COMBINED': ['student_name','student_id','roll_number','email','phone','class_name','section','batch','center','attendance_percentage','present_count','absent_count','exam_name','total_marks','obtained_marks','percentage','grade','rank','teacher_name','subject','department','fee_amount','paid_amount','due_amount','payment_status','academic_year','semester','status','created_at']
  };

  var TYPE_GROUP_BY = {
    'STUDENT': ['class_name','section','batch','center','gender','status'],
    'TEACHER': ['department','subject','designation','center'],
    'ATTENDANCE': ['class_name','section','batch','center','month','week','status'],
    'EXAM': ['class_name','section','batch','center','subject','grade'],
    'CENTER': ['city','state','status'],
    'FINANCIAL': ['class_name','batch','center','payment_status','fee_type'],
    'COMBINED': ['class_name','section','batch','center','academic_year']
  };

  var TYPE_SORT_BY = {
    'STUDENT': ['student_name','roll_number','class_name','admission_date','created_at'],
    'TEACHER': ['teacher_name','date_of_joining','department','subject'],
    'ATTENDANCE': ['student_name','roll_number','attendance_percentage','attendance_date'],
    'EXAM': ['student_name','roll_number','percentage','rank','total_marks','obtained_marks'],
    'CENTER': ['center_name','student_count','teacher_count','attendance_rate'],
    'FINANCIAL': ['student_name','fee_amount','paid_amount','due_amount','payment_date'],
    'COMBINED': ['student_name','roll_number','percentage','attendance_percentage','created_at']
  };

  function updateSuggestions(selectEl, dataListId, items) {
    // Find the datalist or suggestion container for TagListWidget
    // TagListWidget uses a datalist element or inline suggestion chips
    var container = selectEl.closest('.enf-tag-input-wrapper');
    if (!container) return;
    var datalist = container.querySelector('datalist');
    if (datalist) {
      datalist.innerHTML = '';
      items.forEach(function(item) {
        var opt = document.createElement('option');
        opt.value = item;
        datalist.appendChild(opt);
      });
    }
    // Also update any suggestion dropdown
    var suggestWrap = container.querySelector('.enf-tag-suggestions');
    if (suggestWrap) {
      suggestWrap.innerHTML = '';
      items.forEach(function(item) {
        var chip = document.createElement('span');
        chip.className = 'enf-tag-suggestion';
        chip.textContent = item;
        chip.dataset.value = item;
        suggestWrap.appendChild(chip);
      });
    }
  }

  function formatLabel(s) {
    return s.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
  }

  function updateInfoPanel(reportType) {
    var existing = document.getElementById('enf-report-type-info');
    if (existing) existing.remove();

    if (!reportType || !TYPE_COLUMNS[reportType]) return;

    var cols = TYPE_COLUMNS[reportType];
    var groups = TYPE_GROUP_BY[reportType] || [];
    var sorts = TYPE_SORT_BY[reportType] || [];

    var html =
      '<div id="enf-report-type-info" style="background:rgba(132,79,193,0.04);border:1px solid rgba(132,79,193,0.15);' +
      'border-radius:10px;padding:16px 20px;margin:12px 0;animation:fadeIn 0.3s ease;">' +
      '<div style="font-weight:700;font-size:0.85rem;color:var(--primary,#844FC1);margin-bottom:10px;">' +
      '<i class="fas fa-info-circle" style="margin-right:6px;"></i>Available Fields for ' + formatLabel(reportType) + ' Report</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px;">';
    cols.forEach(function(c) {
      html += '<span style="display:inline-block;padding:2px 8px;background:rgba(132,79,193,0.08);' +
        'border:1px solid rgba(132,79,193,0.15);border-radius:4px;font-size:0.72rem;font-weight:500;' +
        'color:var(--primary,#844FC1);">' + formatLabel(c) + '</span>';
    });
    html += '</div>';
    html += '<div style="font-size:0.75rem;color:var(--text-muted,#64748b);">' +
      '<b>Group by:</b> ' + groups.map(formatLabel).join(', ') +
      ' &nbsp;|&nbsp; <b>Sort by:</b> ' + sorts.map(formatLabel).join(', ') + '</div></div>';

    // Insert after the report_type field row
    var typeRow = document.querySelector('.field-report_type');
    if (typeRow) {
      var infoDiv = document.createElement('div');
      infoDiv.innerHTML = html;
      typeRow.parentNode.insertBefore(infoDiv.firstChild, typeRow.nextSibling);
    }
  }

  document.addEventListener('DOMContentLoaded', function() {
    var typeSelect = document.getElementById('id_report_type');
    if (!typeSelect) return;

    function onTypeChange() {
      var rt = typeSelect.value;
      updateInfoPanel(rt);

      // Update TagListWidget suggestion datalists
      var columnsInput = document.querySelector('[name="columns_json"]');
      var groupInput = document.querySelector('[name="group_by"]');
      var sortInput = document.querySelector('[name="sort_by"]');

      if (columnsInput) updateSuggestions(columnsInput, 'columns_json_list', TYPE_COLUMNS[rt] || []);
      if (groupInput) updateSuggestions(groupInput, 'group_by_list', TYPE_GROUP_BY[rt] || []);
      if (sortInput) updateSuggestions(sortInput, 'sort_by_list', TYPE_SORT_BY[rt] || []);
    }

    typeSelect.addEventListener('change', onTypeChange);
    // Run once on load if value is already selected
    if (typeSelect.value) onTypeChange();
  });
})();
