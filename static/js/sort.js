/* Click-to-sort for tables marked data-sortable. Numeric cells carry data-v. */
(function () {
  'use strict';
  Array.prototype.forEach.call(document.querySelectorAll('table[data-sortable]'), function (table) {
    var heads = table.querySelectorAll('th[data-sort]'), body = table.tBodies[0];
    Array.prototype.forEach.call(heads, function (th) {
      var col = Array.prototype.indexOf.call(th.parentNode.children, th), dir = 0;
      th.setAttribute('role', 'button'); th.tabIndex = 0;
      function sort() {
        dir = dir === 1 ? -1 : 1;
        var num = th.getAttribute('data-sort') === 'num';
        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[col], y = b.cells[col];
          if (num) return (parseFloat(x.getAttribute('data-v')) - parseFloat(y.getAttribute('data-v')) || 0) * -dir;
          return x.textContent.trim().localeCompare(y.textContent.trim()) * dir;
        });
        rows.forEach(function (r) { body.appendChild(r); });
        Array.prototype.forEach.call(heads, function (h) { h.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', (num ? -dir : dir) === 1 ? 'ascending' : 'descending');
      }
      th.addEventListener('click', sort);
      th.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(); } });
    });
  });
})();
