import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("FOOTBALL_API_KEY")
if not API_KEY:
    raise RuntimeError("FOOTBALL_API_KEY bulunamadi")

# Turkiye saati (UTC+3)
tr_tz = timezone(timedelta(hours=3))
bugun = datetime.now(tr_tz).strftime("%Y-%m-%d")

url = f"https://v3.football.api-sports.io/fixtures?date={bugun}"
req = urllib.request.Request(url)
req.add_header("x-apisports-key", API_KEY)

with urllib.request.urlopen(req, timeout=30) as resp:
    veri = json.loads(resp.read().decode("utf-8"))

errors = veri.get("errors")
results = veri.get("results", 0)
response_list = veri.get("response", [])

print(f"Tarih (TR): {bugun} | API results: {results} | API errors: {errors}")

maclar = []
lig_sayaclari = {}

for item in response_list:
    lig_adi = item.get("league", {}).get("name", "Bilinmeyen Lig")
    if lig_sayaclari.get(lig_adi, 0) >= 3:
        continue

    lig_sayaclari[lig_adi] = lig_sayaclari.get(lig_adi, 0) + 1
    fixture = item.get("fixture", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})

    tarih_saat = fixture.get("date", "")
    tarih_parca = tarih_saat.split("T")
    tarih_str = tarih_parca[0] if len(tarih_parca) > 0 else bugun
    saat_str = tarih_parca[1][:5] if len(tarih_parca) > 1 else ""

    maclar.append({
        "id": fixture.get("id"),
        "lig": lig_adi,
        "ulke": item.get("league", {}).get("country", ""),
        "ev": teams.get("home", {}).get("name", ""),
        "dep": teams.get("away", {}).get("name", ""),
        "tarih": tarih_str,
        "saat": saat_str,
        "durum": fixture.get("status", {}).get("short", ""),
        "evGol": goals.get("home"),
        "depGol": goals.get("away")
    })

mevcut_maclar = []
if os.path.exists("maclar.json"):
    try:
        with open("maclar.json", "r", encoding="utf-8") as f:
            eski = json.load(f)
            if isinstance(eski, list):
                mevcut_maclar = eski
    except Exception:
        mevcut_maclar = []

if len(maclar) > 0:
    with open("maclar.json", "w", encoding="utf-8") as f:
        json.dump(maclar, f, ensure_ascii=False, indent=2)
    print(f"Kaydedilen yeni mac sayisi: {len(maclar)}")
else:
    if len(mevcut_maclar) > 0:
        print(f"Yeni mac 0 geldi; mevcut {len(mevcut_maclar)} maclik maclar.json korundu.")
    else:
        with open("maclar.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print("Yeni mac 0 geldi ve onceki kayit yoktu; bos liste yazildi.")
