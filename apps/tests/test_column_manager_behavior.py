"""
Functional (behavioral) test for column_manager.js v7.

Regression test: in v6, every DOM mutation re-tagged data-orig-col attributes
based on visual position. After the user hid column "phone" (orig-col 5), the
next admin filter or pagination re-render relabeled the remaining cells back
to 0, 1, 2, 3, ... and the hide rule (`[data-orig-col="5"]`) no longer matched
anything — so columns "came back". v7 must:

  1. Tag a fresh table once, recording orig-col on every header + body cell.
  2. After the simulated mutation (rows replaced), the *new* body cells must
     get tagged using the header's existing orig-col map. Existing cells'
     orig-col attributes must NOT be rewritten.
  3. Hidden column data-orig-col stays consistent so the CSS rule keeps
     working.

We use a tiny JS evaluator (subprocess of node) so this test runs without a
browser — the JS file is loaded as-is.
"""
import os
import shutil
import subprocess
import textwrap

import pytest


JS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'js', 'column_manager.js',
)


def _node_available() -> bool:
    return shutil.which('node') is not None


@pytest.mark.skipif(not _node_available(), reason='node not installed in test env')
def test_v7_observer_does_not_clobber_orig_col_after_mutation(tmp_path):
    # Minimal DOM shim. We expose only the functions under test by stripping
    # the IIFE wrapper at evaluation time.
    js_src = open(JS_PATH).read()
    # Pull the two helper functions out into the global scope of our shim.
    harness = textwrap.dedent(
        r"""
        // ── Tiny DOM shim — just enough for the helpers to walk attributes.
        function makeCell(text) {
          return {
            _attrs: {},
            children: [],
            textContent: text || '',
            classList: { contains: function () { return false; } },
            hasAttribute: function (k) { return k in this._attrs; },
            getAttribute: function (k) { return this._attrs[k] !== undefined ? this._attrs[k] : null; },
            setAttribute: function (k, v) { this._attrs[k] = String(v); },
            querySelector: function () { return null; },
          };
        }
        function makeRow(n) {
          var row = { children: [] };
          for (var i = 0; i < n; i++) row.children.push(makeCell('c' + i));
          row.querySelectorAll = function () { return []; };
          return row;
        }
        function makeTable(headerN, bodyRowsN) {
          var thead = { firstChild: null };
          var headerRow = makeRow(headerN);
          var tbody = { rows: [] };
          for (var r = 0; r < bodyRowsN; r++) tbody.rows.push(makeRow(headerN));
          var table = {
            _headerRow: headerRow,
            _tbody: tbody,
            querySelector: function (sel) {
              if (sel === 'thead tr') return headerRow;
              if (sel === 'tbody') return tbody;
              return null;
            },
            querySelectorAll: function (sel) {
              if (sel === 'tbody tr') return tbody.rows;
              return [];
            },
          };
          return table;
        }

        // Pull tagOriginalIndices + tagNewBodyCells out of the IIFE source.
        // We re-declare them at top level by eval'ing extracted bodies.
        var SRC = process.argv[2] ? require('fs').readFileSync(process.argv[2], 'utf8') : '';
        function extract(name) {
          var m = SRC.match(new RegExp('function\\s+' + name + '\\s*\\([\\s\\S]*?\\n  \\}', 'm'));
          if (!m) throw new Error('helper not found: ' + name);
          return m[0];
        }
        eval(extract('tagOriginalIndices'));
        eval(extract('tagNewBodyCells'));

        // ── Scenario ───────────────────────────────────────────────────────
        var table = makeTable(/*headerN*/ 6, /*bodyRowsN*/ 3);
        tagOriginalIndices(table);

        // Snapshot orig-col for header and one body cell at column 5
        var headerOrig = table._headerRow.children.map(function (c) { return c.getAttribute('data-orig-col'); });
        var body0Col5 = table._tbody.rows[0].children[5].getAttribute('data-orig-col');

        // Simulate admin mutation: replace tbody rows with brand-new untagged
        // rows (this is what Django admin filter/pagination does).
        table._tbody.rows = [];
        for (var r = 0; r < 4; r++) table._tbody.rows.push(makeRow(6));

        // v7 contract: observer calls tagNewBodyCells (NOT tagOriginalIndices)
        tagNewBodyCells(table);

        // Header orig-col must be unchanged
        var headerOrigAfter = table._headerRow.children.map(function (c) { return c.getAttribute('data-orig-col'); });
        if (JSON.stringify(headerOrig) !== JSON.stringify(headerOrigAfter)) {
          console.log('FAIL header tags changed: ' + JSON.stringify(headerOrigAfter));
          process.exit(1);
        }

        // New body cells must be tagged matching header
        var newBody0Col5 = table._tbody.rows[0].children[5].getAttribute('data-orig-col');
        if (newBody0Col5 !== headerOrig[5]) {
          console.log('FAIL new body cell tag mismatch: ' + newBody0Col5 + ' != ' + headerOrig[5]);
          process.exit(1);
        }

        // Original body cell orig-col must equal new body cell orig-col at same column
        if (body0Col5 !== newBody0Col5) {
          console.log('FAIL body tag drift after mutation: was ' + body0Col5 + ' now ' + newBody0Col5);
          process.exit(1);
        }

        // Now simulate hide rule for orig-col 5: it must still match the new cell.
        var match = table._tbody.rows[0].children[5].getAttribute('data-orig-col') === '5';
        if (!match) {
          console.log('FAIL hide rule [data-orig-col="5"] would not match the new cell');
          process.exit(1);
        }
        console.log('OK');
        """
    )
    script = tmp_path / 'harness.js'
    script.write_text(harness)
    result = subprocess.run(
        ['node', str(script), JS_PATH],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, (
        'v7 functional test failed\nstdout:\n' + result.stdout
        + '\nstderr:\n' + result.stderr
    )
    assert 'OK' in result.stdout
