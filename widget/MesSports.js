// ─────────────────────────────────────────────────────────────
//  Widget « Mes sports » pour l'app Scriptable (iPhone).
//  Affiche les prochains matchs + les derniers résultats (24 h).
//
//  Paramètre du widget (facultatif) : un sport pour filtrer,
//  ex. « foot », « rugby », « biathlon »… (vide = tout)
// ─────────────────────────────────────────────────────────────

const BASE = "https://raw.githubusercontent.com/theo2212/sport-calendar/main/docs/";
const sport = (args.widgetParameter || "").trim().toLowerCase();
const URL_ICS = BASE + (sport ? `sport-${sport}.ics` : "calendar.ics");

const size = config.widgetFamily || "large";
const MAX = { small: 3, medium: 4, large: 9, extraLarge: 9 }[size] || 9;

// ── Récupération (avec cache hors-ligne) ─────────────────────
const fm = FileManager.local();
const cache = fm.joinPath(fm.cacheDirectory(), `messports-${sport || "all"}.ics`);
let ics;
try {
  ics = await new Request(URL_ICS).loadString();
  fm.writeString(cache, ics);
} catch (e) {
  ics = fm.fileExists(cache) ? fm.readString(cache) : "";
}

// ── Lecture du .ics ──────────────────────────────────────────
function parse(text) {
  const lines = text.replace(/\r\n[ \t]/g, "").split(/\r?\n/);
  const out = [];
  let cur = null;
  for (const l of lines) {
    if (l === "BEGIN:VEVENT") cur = {};
    else if (l === "END:VEVENT") { if (cur) out.push(cur); cur = null; }
    else if (cur) {
      const i = l.indexOf(":");
      if (i < 0) continue;
      const key = l.slice(0, i).split(";")[0];
      cur[key] = l.slice(i + 1).replace(/\\n/g, "\n").replace(/\\,/g, ",").replace(/\\;/g, ";").replace(/\\\\/g, "\\");
    }
  }
  return out.map(e => ({
    title: e.SUMMARY || "",
    start: icsDate(e.DTSTART),
    end: icsDate(e.DTEND),
    desc: e.DESCRIPTION || "",
  }));
}
function icsDate(s) {
  if (!s) return null;
  const m = s.match(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/);
  return m ? new Date(Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6])) : null;
}

const now = new Date();
const all = parse(ics).filter(e => e.start).sort((a, b) => a.start - b.start);
const recent = all.filter(e => e.end < now && now - e.end < 24 * 3600e3).slice(-2);
const upcoming = all.filter(e => e.end >= now).slice(0, MAX - Math.min(recent.length, size === "small" ? 0 : 2));
const items = [...(size === "small" ? [] : recent), ...upcoming].slice(0, MAX);

// ── Mise en forme ────────────────────────────────────────────
const fmtDay = new DateFormatter(); fmtDay.locale = "fr_FR"; fmtDay.dateFormat = "EEE d";
const fmtTime = new DateFormatter(); fmtTime.locale = "fr_FR"; fmtTime.dateFormat = "HH:mm";
function when(d) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = Math.round((new Date(d).setHours(0, 0, 0, 0) - today) / 864e5);
  const day = diff === 0 ? "Auj." : diff === 1 ? "Demain" : fmtDay.string(d);
  return `${day} ${fmtTime.string(d)}`;
}

const w = new ListWidget();
const bg = new LinearGradient();
bg.colors = [new Color("#0B1D33"), new Color("#123B5E")];
bg.locations = [0, 1];
w.backgroundGradient = bg;
w.setPadding(12, 14, 12, 14);
w.url = "calshow:";   // touche le widget → ouvre Calendrier

const head = w.addStack();
const h = head.addText(sport ? `🏟️ ${sport[0].toUpperCase() + sport.slice(1)}` : "🏟️ Mes sports");
h.font = Font.boldSystemFont(size === "small" ? 13 : 15);
h.textColor = Color.white();
head.addSpacer();
if (size !== "small") {
  const u = head.addText(`maj ${fmtTime.string(now)}`);
  u.font = Font.systemFont(10); u.textColor = new Color("#9FB3C8");
}
w.addSpacer(8);

if (!items.length) {
  const t = w.addText("Aucun match à venir 💤");
  t.font = Font.systemFont(13); t.textColor = new Color("#C9D6E3");
}

for (const e of items) {
  const done = e.end < now;
  const live = e.start <= now && now <= e.end;
  const row = w.addStack();
  row.centerAlignContent();
  if (size !== "small") {
    const t = row.addText(live ? "EN DIRECT" : done ? "Terminé" : when(e.start));
    t.font = Font.mediumMonospacedSystemFont(10);
    t.textColor = live ? new Color("#FF5A5F") : done ? new Color("#7F93A8") : new Color("#7FD1FF");
    t.lineLimit = 1;
    row.addSpacer(6);
    t.minimumScaleFactor = 0.8;
  }
  const col = row.addStack();
  col.layoutVertically();
  const title = col.addText(e.title);
  title.font = Font.semiboldSystemFont(size === "small" ? 11 : 12);
  title.textColor = done ? new Color("#C9D6E3") : Color.white();
  title.lineLimit = 1;
  title.minimumScaleFactor = 0.75;
  if (size === "small") {
    const t = col.addText(live ? "EN DIRECT" : when(e.start));
    t.font = Font.systemFont(9); t.textColor = new Color("#7FD1FF");
  }
  w.addSpacer(size === "large" ? 5 : 3);
}
w.addSpacer();
w.refreshAfterDate = new Date(Date.now() + 30 * 60e3);

Script.setWidget(w);
if (!config.runsInWidget) await w.presentLarge();
Script.complete();
