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
  var errorEl = document.getElementById('tw-error');
  var errorText = errorEl.textContent;
  var submitBtn = document.querySelector('#tw-form button[type="submit"]');
  var submitText = submitBtn ? submitBtn.textContent : '';
  var busy = false;
  function fehler(text) {
    errorEl.textContent = text || errorText;
    errorEl.hidden = false;
    document.getElementById('tw-mail').focus();
  }
  // Prüft serverseitig, ob die Mail-Domain Post empfangen kann. Im Zweifel: durchlassen.
  function domainOk(mail, done) {
    var domain = mail.split('@').pop();
    var fertig = false;
    function ende(ok) { if (!fertig) { fertig = true; done(ok); } }
    setTimeout(function () { ende(true); }, 4000);
    try {
      fetch('/api/mail-check?d=' + encodeURIComponent(domain), { cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : { ok: true }; })
        .then(function (j) { ende(!(j && j.ok === false)); })
        .catch(function () { ende(true); });
    } catch (err) { ende(true); }
  }
  function weiter(mail) {
    var firma = document.getElementById('tw-firma').value.trim();
    var tel = document.getElementById('tw-tel').value.trim();
    var note = 'Aufgabe: ' + (state.task || 'nicht gewählt') + (firma ? '. Firma: ' + firma : '') + (tel ? '. Telefon: ' + tel : '') + '. Quelle: tool-werk.de';
    var url = CAL + '?email=' + encodeURIComponent(mail) + '&a1=' + encodeURIComponent(note);
    var cal = document.getElementById('tw-calendar');
    cal.href = url;
    cal.setAttribute('target', '_blank');
    show(3);
  }
  document.getElementById('tw-form').addEventListener('submit', function (e) {
    e.preventDefault();
    if (busy) return;
    var mail = document.getElementById('tw-mail').value.trim();
    var ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(mail);
    errorEl.hidden = true;
    if (!ok) { fehler(); return; }
    // Fallenfeld: Menschen sehen es nicht, Bots füllen es aus. Dann still ins Leere laufen lassen.
    var hp = document.getElementById('tw-hp');
    if (hp && hp.value) {
      var cal = document.getElementById('tw-calendar');
      cal.href = '#check';
      cal.removeAttribute('target');
      show(3);
      return;
    }
    busy = true;
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Einen Moment …'; }
    domainOk(mail, function (domainGut) {
      busy = false;
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitText; }
      if (!domainGut) { fehler('Unter dieser E-Mail-Adresse kommt keine Post an. Bitte prüfen Sie die Schreibweise.'); return; }
      weiter(mail);
    });
  });
  show(1);
  // Von Unterseiten: /?aufgabe=...#check wählt die Aufgabe direkt vor
  try {
    var wanted = new URLSearchParams(location.search).get('aufgabe');
    if (wanted) {
      funnel.querySelectorAll('.tw-task').forEach(function (b) {
        if (b.getAttribute('data-task') === wanted) pick(wanted, false);
      });
    }
  } catch (e) {}
})();
