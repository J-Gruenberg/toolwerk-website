// Prüft, ob die Domain einer E-Mail-Adresse überhaupt Post empfangen kann.
// Wird vom Ablauf-Check auf der Startseite aufgerufen, bevor Calendly geöffnet wird.
// Grundsatz: Im Zweifel durchlassen (fail-open). Abgelehnt wird nur, wenn die
// Domain nachweislich nicht existiert oder ausdrücklich keine Post annimmt.
const dns = require('dns').promises;
const { domainToASCII } = require('url');

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(Object.assign(new Error('timeout'), { code: 'ETIMEOUT' })), ms)),
  ]);
}

const GIBT_ES_NICHT = new Set(['ENOTFOUND', 'NXDOMAIN']);
const KEINE_DATEN = new Set(['ENODATA']);

async function hatAdresse(domain) {
  for (const typ of ['A', 'AAAA']) {
    try {
      const r = await withTimeout(dns.resolve(domain, typ), 2000);
      if (r && r.length) return true;
    } catch (e) {
      if (!GIBT_ES_NICHT.has(e.code) && !KEINE_DATEN.has(e.code)) return null; // unklar
    }
  }
  return false;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const roh = String((req.query && req.query.d) || '').trim().toLowerCase().replace(/\.$/, '');
  const domain = roh ? domainToASCII(roh) : '';

  if (!domain || domain.length > 253 || !/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(domain)) {
    return res.status(200).json({ ok: false, grund: 'format' });
  }

  try {
    const mx = await withTimeout(dns.resolveMx(domain), 2500);
    const echte = (mx || []).filter((m) => m.exchange && m.exchange !== '.');
    if (echte.length) return res.status(200).json({ ok: true });
    // Null-MX (RFC 7505): Domain nimmt ausdrücklich keine Post an
    if (mx && mx.length) return res.status(200).json({ ok: false, grund: 'keine-post' });
    return res.status(200).json({ ok: true, unsicher: true });
  } catch (e) {
    if (GIBT_ES_NICHT.has(e.code)) {
      return res.status(200).json({ ok: false, grund: 'domain' });
    }
    if (KEINE_DATEN.has(e.code)) {
      // Kein MX-Eintrag: Laut Standard darf dann die normale Adresse der Domain Post annehmen
      const a = await hatAdresse(domain);
      if (a === false) return res.status(200).json({ ok: false, grund: 'domain' });
      return res.status(200).json({ ok: true, unsicher: a === null });
    }
    // Zeitüberschreitung oder Serverfehler: nicht blockieren
    return res.status(200).json({ ok: true, unsicher: true });
  }
};
