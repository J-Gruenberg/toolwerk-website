(function () {
  var CAL = 'https://calendly.com/j-gruenberg-gruenbergsolutions/analysegesprach-toolwerk';
  var funnel = document.getElementById('tw-funnel');
  if (!funnel) return;
  var labels = { 1: 'Was soll weg?', 2: 'Wohin dürfen wir uns melden?', 3: 'Termin wählen' };
  var state = { task: '' };
  function show(step) {
    funnel.querySelectorAll('.tw-step').forEach(function (el) { el.hidden = String(step) !== el.getAttribute('data-step'); });
    document.getElementById('tw-step-label').textContent = labels[step];
    document.getElementById('tw-step-count').textContent = 'Schritt ' + step + ' von 3';
    document.getElementById('tw-progress').style.width = step === 1 ? '33%' : (step === 2 ? '66%' : '100%');
    if (step === 2) document.getElementById('tw-task-chip').textContent = state.task;
  }
  function pick(task, focus) {
    state.task = task;
    show(2);
    if (focus) setTimeout(function () { var f = document.getElementById('tw-firma'); if (f) f.focus({ preventScroll: true }); }, 400);
  }
  funnel.querySelectorAll('.tw-task').forEach(function (b) {
    b.addEventListener('click', function () { pick(b.getAttribute('data-task'), true); });
  });
  document.querySelectorAll('a[data-task]').forEach(function (a) {
    a.addEventListener('click', function () { pick(a.getAttribute('data-task'), false); });
  });
  funnel.querySelector('.tw-back').addEventListener('click', function () { show(1); });
  funnel.querySelector('.tw-reset').addEventListener('click', function () { document.getElementById('tw-form').reset(); state.task = ''; show(1); });
  document.getElementById('tw-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var mail = document.getElementById('tw-mail').value.trim();
    var ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(mail);
    document.getElementById('tw-error').hidden = ok;
    if (!ok) { document.getElementById('tw-mail').focus(); return; }
    var firma = document.getElementById('tw-firma').value.trim();
    var tel = document.getElementById('tw-tel').value.trim();
    var note = 'Aufgabe: ' + (state.task || 'nicht gewählt') + (firma ? '. Firma: ' + firma : '') + (tel ? '. Telefon: ' + tel : '') + '. Quelle: tool-werk.de';
    var url = CAL + '?email=' + encodeURIComponent(mail) + '&a1=' + encodeURIComponent(note);
    document.getElementById('tw-calendar').href = url;
    show(3);
  });
  show(1);
})();
