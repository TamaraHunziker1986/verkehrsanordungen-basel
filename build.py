#!/usr/bin/env python3
"""Holt Verkehrsanordnungen und verkehrsrelevante Baupublikationen aus dem
Kantonsblatt Basel-Stadt und baut daraus docs/index.html.

Läuft ohne Zusatzpakete (nur Python-Standardbibliothek).
"""
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.kantonsblatt.ch/api/v1"
ROOT = Path(__file__).resolve().parent
START = "2026-01-01"  # fixer Startpunkt der Übersicht

# Rubriken: Verkehrsanordnung, weitere verkehrspolizeiliche Bekanntmachung, Strassenbau,
# Baupublikationen, Bau- und Nutzungsgesuch Allmend
RUBRICS = ["VE-BS40", "VE-BS50", "VE-BS10", "BP-BS10", "BP-BS20"]

# Baupublikationen nur, wenn eines dieser Stichworte im Projekt vorkommt
BP_KEEP = re.compile(
    r"parkpl|parkfeld|parkier|autoabstell|abstellpl|einstellhalle|tiefgarage|garage|carport|"
    r"ladesäule|ladestation|elektroparkpl|e-mobilit|veloverleih|strassenlinie|änderung der baulinie|"
    r"fahrweg|fahrbahn|trottoir|bushaltestelle|\btram\b|tramlinie|eisenbahnrechtlich|"
    r"umgestaltung der allmend|umgestaltung parkplatz|erschliessungsplan|verkehr|strassenraum|baustelleninstall|gerüst",
    re.I,
)
# Gesuche auf Allmend sind immer Strassenraum; nur Boulevard-Gastronomie weglassen
BP_DROP = re.compile(r"boulevard|gartenwirtschaft|aussenbewirtung", re.I)
# Baumfällungen bei privaten Bauprojekten betreffen den Verkehr nicht
BP10_PUBLIC_TREES = re.compile(r"^Baumfällung|öffentlichen? Hand|Allmend|Strasse\b", re.I)

DE_WD = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
DE_MO = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
         "September", "Oktober", "November", "Dezember"]


def get(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "verkehrsanordnungen-basel (GitHub Actions)",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"  Fehler {e}, neuer Versuch", file=sys.stderr)
            time.sleep(min(60, 5 * 2 ** i))


def list_pubs(sub, since):
    out, page = [], 0
    while True:
        q = urllib.parse.urlencode({
            "publicationStates": "PUBLISHED",
            "subRubrics": sub,
            "publicationDate.start": since,
            "pageRequest.page": page,
            "pageRequest.size": 200,
        })
        j = get(f"{API}/publications?{q}")
        content = j.get("content") or []
        out += content
        if not content or len(out) >= j.get("total", 0):
            return out
        page += 1


def strip_html(h):
    h = re.sub(r"<br\s*/?>", "\n", str(h), flags=re.I)
    h = re.sub(r"</p>|</div>|</li>", "\n", h, flags=re.I)
    h = re.sub(r"<li[^>]*>", "\n- ", h, flags=re.I)
    h = html.unescape(re.sub(r"<[^>]+>", "", h))
    h = re.sub(r"[ \t ]+", " ", h)
    h = re.sub(r"\n\s*\n+", "\n", h)
    return h.strip()


def flatten(fields, acc):
    for f in fields or []:
        label = (f.get("label") or {}).get("de")
        v = f.get("value")
        if isinstance(v, dict):
            v = v.get("de") or v.get("defaultValue")
        if f.get("type") == "PANEL" and label:
            acc.append("## " + label)
        if v and isinstance(v, str):
            acc.append((label + ": " if label else "") + strip_html(v))
        flatten(f.get("fields"), acc)
    return acc


CACHE_FILE = ROOT / "cache" / "views.json"
CACHE = {}


def view_text(pid):
    """Text einer Publikation; einmal geholte Texte kommen aus dem Zwischenspeicher."""
    if pid in CACHE:
        return CACHE[pid]
    v = get(f"{API}/publications/{pid}/view")
    CACHE[pid] = "\n".join(flatten(v.get("fields"), []))
    time.sleep(0.3)
    return CACHE[pid]


BOILER = re.compile(
    r"Die baulichen Anpassungen und/oder die anderweitige Nutzung sind nicht Bestandteil "
    r"dieser Verkehrsanordnung\. Diesbezüglich wird auf die separate Publikation der "
    r"Allmendverwaltung im Kantonsblatt verwiesen\.")
ERLASS = re.compile(r"wird folgende (?:temporäre )?Verkehrsanordnung erlassen:|werden folgende [^:]*?Anordnungen erlassen:|werden folgende Verkehrsanordnungen erlassen:")


def place_suffix(title):
    if re.search(r",\s*Riehen$", title.strip()):
        return " (Riehen)"
    if re.search(r",\s*Bettingen$", title.strip()) and "Basel, Bettingen" not in title:
        return " (Bettingen)"
    return ""


def clean_streets(parts, suf):
    out = []
    for p in parts:
        p = re.sub(r"\s*\b(Nutzung|Erschliessung)\b.*$", "", p.strip()).strip(" ,-")
        if p and p not in ("Basel", "Riehen", "Bettingen") and p not in out:
            out.append(p)
    return ", ".join(x + suf for x in out)


def record_va(meta, text):
    title = meta["title"]["de"]
    streets = (re.search(r"Betroffene Strasse\(n\):\s*(.*)", text) or [None, ""])[1].strip()
    body = text.split("Verfügende Stelle")[0]
    typ = "T" if "## Temporäre" in body else ("P" if "## Permanente" in body else "")
    if re.search(r"Baubedingt|temporär", title + body, re.I):
        typ = "T"
    body = re.sub(r"Betroffene Strasse\(n\):.*\n?", "", body)
    body = re.sub(r"## [^\n]*\n?", "", body)
    body = BOILER.sub("", body)
    body = re.sub(r"[ \t]*\n[ \t]*", "\n", body).strip()
    reason = ""
    m = ERLASS.search(body)
    if m:
        reason = body[:m.start()].strip().rstrip(",")
        body = body[m.end():]
        body = re.sub(r"\n?(Zwecks|Im Zusammenhang|Zur |Aufgrund|Infolge)[^\n]*?" + ERLASS.pattern, "\n", body)
    body = re.sub(r"\n+", "\n", body).strip()
    if len(body) > 1600:
        body = body[:1600].rsplit("\n", 1)[0] + "\n… (Auszug, vollständiger Text im Kantonsblatt)"
    clean_title = re.sub(r", Basel$", "", title)
    if not streets:
        streets = re.sub(r"^(Verkehrsanordnung|Baubedingte Massnahmen)\s+", "", clean_title)
        streets = re.sub(r",\s*(Basel|Riehen|Bettingen).*$", "", streets)
    suf = place_suffix(title)
    streets = ", ".join(s.strip() + suf for s in re.split(r",\s*", streets) if s.strip())
    return [meta["publicationDate"][:10], meta["subRubric"].replace("-BS", ""), clean_title,
            streets, typ, reason, body, meta["id"]]


def project_text(text):
    m = re.search(r"Angaben zum Projekt:\s*([\s\S]*?)(?:\nGesuchsteller|\nAngaben zur Auflage|$)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"## Projekt\n([\s\S]*?)(?:\n## |$)", text)
    if m:
        return m.group(1).strip()
    return text[:600]


def record_bp(meta, text):
    title = meta["title"]["de"]
    proj = project_text(text)
    gs = re.search(r"Gesuchsteller:\s*([^\n]*)", text)
    place = re.search(r"Ortsbezeichnung:\s*([^\n]*)", text)
    lines = [l for l in proj.split("\n") if l.strip() and l.strip() != "-"]
    # Adresslisten bei Baupublikationen kürzen
    short = []
    for l in lines:
        if re.search(r"^\S.*\d{4} (Basel|Riehen|Bettingen)$", l) or re.match(r"^Sektion ", l):
            continue
        short.append(l)
    summary = " ".join(short)[:600]
    if gs:
        summary += " Gesuchsteller: " + gs.group(1).strip().rstrip(",") + "."
    streets = ""
    if place:
        streets = re.sub(r"^(Basel|Riehen|Bettingen),\s*", "", place.group(1))
        streets = re.sub(r"\s*-\s*(Nutzung|Erschliessung).*$", "", streets)
        streets = re.sub(r"\s*\d[\d\s+\-–]*", " ", streets)
        streets = re.split(r",", streets)
    else:
        m = re.search(r":\s*(.+)$", title)
        streets = m.group(1) if m else ""
        streets = re.sub(r"\s*\d[\w\s,]*?(?=,|$)", "", streets)
        streets = re.split(r",", streets)
    streets = clean_streets(streets, place_suffix(title))
    return [meta["publicationDate"][:10], meta["subRubric"].replace("-BS", ""),
            re.sub(r"^Bau- und Nutzungsgesuch auf Allmend - ", "Bau- und Nutzungsgesuch auf Allmend: ", title),
            streets, "", "", summary.strip(), meta["id"]]


TREE = re.compile(r"baumfäll\w*|baumpflanz\w*|baumbestand\w*|bäume\w*|baum\w*", re.I)
# "Verkehrssicherheit" bei Bäumen heisst Bruchgefahr, nicht Strassenverkehr
TREE_NOISE = re.compile(r"verkehrssicherheit", re.I)


def tree_only(text):
    """True, wenn es nur um Bäume geht und kein Bezug zu Verkehr oder Strassenraum besteht."""
    if not re.search(r"baumfäll", text, re.I):
        return False
    # Fällungen zur Pflege des Baumbestands (öffentliche Hand) sind Unterhalt, kein Verkehrsprojekt
    if re.match(r"\s*Baumfällung", text, re.I) and re.search(r"Pflege und Erhalt", text, re.I):
        return True
    rest = TREE_NOISE.sub("", TREE.sub("", text))
    return not BP_KEEP.search(rest)


def keep_bp(meta, text):
    proj = project_text(text)
    title = meta["title"]["de"]
    # Baumfällungen nur, wenn sie zu einem Verkehrs- oder Strassenprojekt gehören
    if tree_only(title + "\n" + proj):
        return False
    if meta["subRubric"] == "BP-BS20":
        return not BP_DROP.search(proj)
    return bool(BP_KEEP.search(TREE_NOISE.sub("", proj)))


def main():
    since = START
    if CACHE_FILE.exists():
        CACHE.update(json.loads(CACHE_FILE.read_text(encoding="utf-8")))
    # Bereits aufbereitete Verkehrsanordnungen aus dem letzten Lauf übernehmen (spart Abfragen)
    known = {}
    old_file = ROOT / "docs" / "data.json"
    if old_file.exists():
        known = {r[7]: r for r in json.loads(old_file.read_text(encoding="utf-8")) if r[1] == "VE40"}
    rows = []
    for sub in RUBRICS:
        pubs = list_pubs(sub, since)
        print(f"{sub}: {len(pubs)} Publikationen seit {since}")
        for p in pubs:
            meta = p["meta"]
            if sub == "VE-BS40" and meta["id"] in known and meta["id"] not in CACHE:
                rows.append(known[meta["id"]])
                continue
            try:
                text = view_text(meta["id"])
            except Exception as e:  # noqa: BLE001
                print(f"  übersprungen {meta['id']}: {e}", file=sys.stderr)
                continue
            if sub == "VE-BS40":
                rows.append(record_va(meta, text))
            elif sub == "VE-BS50":
                # Verwertungsverfügungen enthalten Personendaten und betreffen den Verkehr nicht
                if re.search(r"Verwertung|Abholaufforderung", meta["title"]["de"] + text, re.I):
                    continue
                r = record_bp(meta, text)
                if not r[3]:
                    r[3] = clean_streets([meta["title"]["de"].split(",")[0]], place_suffix(meta["title"]["de"]))
                rows.append(r)
            elif sub == "VE-BS10":
                r = record_bp(meta, text)
                if not r[3]:
                    r[3] = clean_streets([meta["title"]["de"].split(",")[0]], place_suffix(meta["title"]["de"]))
                rows.append(r)
            elif keep_bp(meta, text):
                rows.append(record_bp(meta, text))
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(CACHE, ensure_ascii=False), encoding="utf-8")
    if not rows:
        sys.exit("Keine Daten erhalten, Seite bleibt unverändert.")
    # Das Kantonsblatt nimmt Baupublikationen nach Ablauf der Frist vom Netz.
    # Frühere Einträge deshalb aus dem letzten Lauf übernehmen, damit nichts verloren geht.
    old_file = ROOT / "docs" / "data.json"
    if old_file.exists():
        have = {r[7] for r in rows}
        for r in json.loads(old_file.read_text(encoding="utf-8")):
            if r[7] not in have and r[0] >= since and r[1] != "VE50" \
                    and not (r[1].startswith("BP") and tree_only(r[2] + "\n" + r[6])):
                rows.append(r)
    # Erschliessung und Nutzung zum selben Ort zusammenfassen
    merged, seen = [], {}
    for r in rows:
        key = (r[0], r[1], r[3]) if r[1] == "BP20" and r[3] else None
        if key and key in seen:
            prev = seen[key]
            if r[6] not in prev[6]:
                prev[6] = prev[6] + " / " + r[6]
            continue
        if key:
            seen[key] = r
        merged.append(r)
    rows = merged
    rows.sort(key=lambda r: r[0], reverse=True)
    latest = dt.date.fromisoformat(rows[0][0])
    stand = f"Kantonsblatt vom {DE_WD[latest.weekday()]}, {latest.day}. {DE_MO[latest.month - 1]} {latest.year}"
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    out = (tpl.replace("/*DATA*/", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
              .replace("/*STAND*/", stand).replace("/*SINCE*/", since))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(out, encoding="utf-8")
    (ROOT / "docs" / "data.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} Einträge geschrieben, {stand}")


if __name__ == "__main__":
    main()
