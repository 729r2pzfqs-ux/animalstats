/* Client-side search. The index is fetched on first focus (or on the /search/ page), not on every page load. */
(function () {
  'use strict';
  var index = null, loading = null;
  var STOP = ['how', 'long', 'do', 'does', 'a', 'an', 'the', 'live', 'fast', 'is', 'much', 'weigh', 'facts', 'can', 'run', 'big', 'tall', 'what', 'eat'];

  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) loading = fetch('/search-index.json').then(function (r) { return r.json(); }).then(function (d) { index = d; return d; });
    return loading;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function norm(s) { return s.toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }

  function score(item, q, words) {
    var n = norm(item.n), best = 0;
    if (n === q) best = 100;
    else if (n.split(' ').indexOf(q) >= 0) best = 88;
    else if (n.indexOf(q) === 0) best = 80;
    else if ((' ' + n).indexOf(' ' + q) >= 0) best = 55;
    else if (q.length > 3 && n.indexOf(q) >= 0) best = 25;
    item.a.forEach(function (a) {
      a = norm(a);
      if (a === q) best = Math.max(best, 92);
      else if ((' ' + a).indexOf(' ' + q) >= 0) best = Math.max(best, 50);
    });
    if (norm(item.s).indexOf(q) === 0) best = Math.max(best, 70);
    if (!best && words.length > 1) {
      var hay = n + ' ' + item.a.join(' ');
      var hits = words.filter(function (w) { return w.length > 2 && hay.indexOf(w) >= 0; }).length;
      if (hits === words.length) best = 60;
    }
    if (best && item.c !== 'Comparison' && item.c !== 'Ranking') best += 1;
    return best;
  }
  function find(q, limit) {
    q = norm(q);
    if (q.length < 2) return null;
    var words = q.split(' ').filter(function (w) { return STOP.indexOf(w) < 0; });
    // Also try singular forms ("cats" → "cat", "foxes" → "fox", "wolves" → "wolf") and keep each item's best score.
    var singular = words.map(function (w) {
      return w.replace(/ves$/, 'f').replace(/(s|x|ch|sh)es$/, '$1').replace(/([^s])s$/, '$1');
    });
    var best = {};
    [[words.join(' ') || q, words], [singular.join(' '), singular]].forEach(function (v) {
      index.forEach(function (it, i) {
        var sc = score(it, v[0], v[1]);
        if (sc > (best[i] || 0)) best[i] = sc;
      });
    });
    return Object.keys(best).map(function (i) { return [best[i], index[i]]; })
      .sort(function (a, b) { return b[0] - a[0] || a[1].n.length - b[1].n.length; }).slice(0, limit).map(function (x) { return x[1]; });
  }
  function rowHtml(it, i) {
    return '<a role="option" data-i="' + i + '" href="' + it.u + '" class="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-2.5 last:border-0 hover:bg-emerald-50">' +
      '<span><span class="font-semibold text-slate-900">' + esc(it.n) + '</span><span class="block text-xs text-slate-500">' + esc(it.c) + (it.s ? ' · <em>' + esc(it.s) + '</em>' : '') + '</span></span>' +
      (it.l ? '<span class="shrink-0 text-right text-xs text-slate-600"><span class="block">' + esc(it.l) + '</span><span class="block">' + esc(it.w) + '</span></span>' : '') + '</a>';
  }

  function attach(box) {
    var input = box.querySelector('input'), out = box.querySelector('[data-results]'), active = -1;
    function close() { out.classList.add('hidden'); out.innerHTML = ''; active = -1; }
    function render() {
      var hits = find(input.value, 8);
      if (hits === null) { close(); return; }
      out.innerHTML = hits.length ? hits.map(rowHtml).join('')
        : '<div class="px-4 py-3 text-sm text-slate-500">No match. <a class="link" href="/animals/">Browse all animals</a></div>';
      active = -1;
      out.classList.remove('hidden');
    }
    function move(d) {
      var items = out.querySelectorAll('a[data-i]');
      if (!items.length) return;
      if (active >= 0) items[active].classList.remove('bg-emerald-50');
      active = (active + d + items.length) % items.length;
      items[active].classList.add('bg-emerald-50');
      items[active].scrollIntoView({ block: 'nearest' });
    }
    input.addEventListener('focus', load);
    input.addEventListener('input', function () { load().then(render); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Escape') { close(); input.blur(); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var items = out.querySelectorAll('a[data-i]');
        var target = items[active >= 0 ? active : 0];
        window.location.href = target ? target.getAttribute('href') : '/search/?q=' + encodeURIComponent(input.value);
      }
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) close(); });
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-search]'), attach);

  /* /search/?q=… results page (target of the WebSite SearchAction) */
  var page = document.getElementById('search-page-results');
  if (page) {
    var q = new URLSearchParams(window.location.search).get('q') || '';
    var status = document.getElementById('search-status');
    if (q) {
      var top = document.getElementById('q-top');
      if (top) top.value = q;
      load().then(function () {
        var hits = find(q, 30) || [];
        status.textContent = hits.length + ' result' + (hits.length === 1 ? '' : 's') + ' for “' + q + '”';
        if (hits.length) { page.innerHTML = hits.map(rowHtml).join(''); page.classList.remove('hidden'); }
      });
    }
  }
})();
