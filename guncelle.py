import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

FD_API_KEY = os.environ.get("FOOTBALL_DATA_KEY", "").strip()
FD_BASE_URL = "https://api.football-data.org/v4"
OUTPUT_FILE = "maclar.json"

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


def get_tr_date_str():
    now_tr = datetime.now(ZoneInfo("Europe/Istanbul"))
    return now_tr.strftime("%Y-%m-%d")


def fetch_football_data_matches(date_str):
    if not FD_API_KEY:
        print("UYARI: FOOTBALL_DATA_KEY ortam degiskeni bulunamadi.")
        return []

    headers = {
        "X-Auth-Token": FD_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "dateFrom": date_str,
        "dateTo": date_str,
        "competitions": ",".join(FD_COMPETITIONS),
    }

    url = f"{FD_BASE_URL}/matches"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"Football-Data API hatasi: {e}")
        return []
    except ValueError as e:
        print(f"Football-Data JSON parse hatasi: {e}")
        return []

    raw_matches = data.get("matches", [])
    normalized = []

    for m in raw_matches:
        comp = m.get("competition", {}) or {}
        home = m.get("homeTeam", {}) or {}
        away = m.get("awayTeam", {}) or {}
        score = m.get("score", {}) or {}
        full_time = score.get("fullTime", {}) or {}

        normalized.append({
            "id": m.get("id"),
            "kaynak": "football-data",
            "lig_kodu": comp.get("code"),
            "lig": comp.get("name"),
            "ulke": (m.get("area") or {}).get("name"),
            "tarih_saat_utc": m.get("utcDate"),
            "durum": m.get("status"),
            "ev_sahibi": home.get("name"),
            "deplasman": away.get("name"),
            "skor": {
                "ev": full_time.get("home"),
                "deplasman": full_time.get("away"),
            },
        })

    return normalized


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


def main():
    date_str = get_tr_date_str()
    print(f"Football-Data cekimi basladi | Tarih (TR): {date_str}")

    new_matches = fetch_football_data_matches(date_str)
    print(f"Football-Data: {len(new_matches)} mac bulundu.")

    if new_matches:
        save_matches(OUTPUT_FILE, new_matches)
        print(f"{OUTPUT_FILE} guncellendi ({len(new_matches)} mac kaydedildi).")
        return

    existing = load_existing_matches(OUTPUT_FILE)
    if existing:
        print(
            f"Yeni mac 0 geldi; mevcut {OUTPUT_FILE} kaydi korundu ({len(existing)} mac)."
        )
    else:
        save_matches(OUTPUT_FILE, [])
        print(f"Yeni mac 0 geldi ve onceki kayit yoktu; bos liste yazildi.")


if __name__ == "__main__":
    main()
