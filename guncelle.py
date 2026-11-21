import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

FD_API_KEY = os.environ.get("FOOTBALL_DATA_KEY", "").strip()
FD_BASE_URL = "https://api.football-data.org/v4"
OUTPUT_FILE = "maclar.json"
TR_TZ = ZoneInfo("Europe/Istanbul")

# Football-Data.org ucretsiz planinda acik olan temel yarismalar
FD_COMPETITIONS = [
    "PL",   # Premier League
    "PD",   # LaLiga
    "BL1",  # Bundesliga
    "SA",   # Serie A
    "FL1",  # Ligue 1
    "DED",  # Eredivisie
    "PPL",  # Primeira Liga
    "ELC",  # Championship
    "BSA",  # Brasileiro Serie A
    "CL",   # UEFA Champions League
]

STATUS_MAP = {
    "SCHEDULED": "Baslamadi",
    "TIMED": "Baslamadi",
    "IN_PLAY": "Canli",
    "PAUSED": "Devre Arasi",
    "FINISHED": "Bitti",
    "POSTPONED": "Ertelendi",
    "SUSPENDED": "Askida",
    "CANCELLED": "Iptal",
}


def get_tr_window():
    now_tr = datetime.now(TR_TZ)
    start_tr = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
    end_tr = start_tr + timedelta(days=1) - timedelta(seconds=1)

    # UTC sinirinda kalan gece/sabah maclarini kacirmamak icin 1 gunluk pencere
    date_from = (start_tr - timedelta(days=1)).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d")
    date_to = (end_tr + timedelta(days=1)).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d")
    target_date_str = start_tr.strftime("%Y-%m-%d")
    return target_date_str, date_from, date_to


def format_match(m, target_date_str):
    utc_str = m.get("utcDate")
    if not utc_str:
        return None

    try:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    except ValueError:
        return None

    dt_tr = dt_utc.astimezone(TR_TZ)
    match_date_tr = dt_tr.strftime("%Y-%m-%d")
    if match_date_tr != target_date_str:
        return None

    comp = m.get("competition", {}) or {}
    home = m.get("homeTeam", {}) or {}
    away = m.get("awayTeam", {}) or {}
    score = m.get("score", {}) or {}
    full_time = score.get("fullTime", {}) or {}

    ev_skor = full_time.get("home")
    dep_skor = full_time.get("away")
    status_raw = m.get("status", "")

    if ev_skor is not None and dep_skor is not None:
        skor_yazi = f"{ev_skor} - {dep_skor}"
    else:
        skor_yazi = " - "

    return {
        "id": m.get("id"),
        "kaynak": "football-data",
        "lig_kodu": comp.get("code"),
        "lig": comp.get("name"),
        "tarih_tr": match_date_tr,
        "saat_tr": dt_tr.strftime("%H:%M"),
        "tarih_saat_utc": utc_str,
        "durum_kod": status_raw,
        "durum": STATUS_MAP.get(status_raw, status_raw),
        "ev_sahibi": home.get("name"),
        "deplasman": away.get("name"),
        "skor_yazi": skor_yazi,
        "skor": {
            "ev": ev_skor,
            "deplasman": dep_skor,
        },
    }


def fetch_todays_matches(target_date_str, date_from, date_to):
    if not FD_API_KEY:
        print("UYARI: FOOTBALL_DATA_KEY ortam degiskeni bulunamadi.")
        return []

    headers = {
        "X-Auth-Token": FD_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "competitions": ",".join(FD_COMPETITIONS),
    }

    url = f"{FD_BASE_URL}/matches"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"Football-Data API hatasi: {e}")
        return None
    except ValueError as e:
        print(f"Football-Data JSON parse hatasi: {e}")
        return None

    matches = []
    for raw_m in data.get("matches", []):
        item = format_match(raw_m, target_date_str)
        if item:
            matches.append(item)

    matches.sort(key=lambda x: (x["saat_tr"], x["lig_kodu"] or "", x["ev_sahibi"] or ""))
    return matches


def load_existing_matches(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                return content
            if isinstance(content, dict) and isinstance(content.get("matches"), list):
                return content["matches"]
    except Exception as e:
        print(f"Mevcut {filepath} okunamadi: {e}")
    return []


def save_matches(filepath, matches):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)


def print_match_summary(matches):
    for m in matches:
        print(
            f"[{m['saat_tr']}] ({m['lig_kodu']}) {m['ev_sahibi']} vs {m['deplasman']} "
            f"| Skor: {m['skor_yazi']} | Durum: {m['durum']}"
        )


def main():
    target_date_str, date_from, date_to = get_tr_window()
    print(f"Football-Data cekimi basladi | Gun (TR): {target_date_str}")

    result = fetch_todays_matches(target_date_str, date_from, date_to)

    # API hatasi olustuysa mevcut maclar.json kaydini koru
    if result is None:
        existing = load_existing_matches(OUTPUT_FILE)
        print(f"API hatasi nedeniyle mevcut {OUTPUT_FILE} korundu ({len(existing)} mac).")
        return

    print(f"Bugun (TR) icin {len(result)} mac bulundu.")
    if result:
        print_match_summary(result)
        save_matches(OUTPUT_FILE, result)
        print(f"{OUTPUT_FILE} guncellendi ({len(result)} mac).")
    else:
        existing = load_existing_matches(OUTPUT_FILE)
        if existing:
            print(f"Bugun yeni mac 0 geldi; mevcut {OUTPUT_FILE} korundu ({len(existing)} mac).")
        else:
            save_matches(OUTPUT_FILE, [])
            print(f"Bugun mac yok; {OUTPUT_FILE} bos liste [] olarak kaydedildi.")


if __name__ == "__main__":
    main()
