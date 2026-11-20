import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_KEY = os.environ.get("FOOTBALL_API_KEY")
if not API_KEY:
    raise RuntimeError("FOOTBALL_API_KEY bulunamadi")

LIG_IDLERI = [
    203,  # Super Lig
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    88,   # Eredivisie
    94,   # Primeira Liga
    144,  # Pro League
    179,  # Premiership
    207,  # Swiss Super League
    218,  # Austrian Bundesliga
    71,   # Brasileirao Serie A
]

simdi = datetime.now(timezone.utc)
sezon = simdi.year if simdi.month >= 7 else simdi.year - 1

tum_puan_durumlari = []

for lig_id in LIG_IDLERI:
    url = f"https://v3.football.api-sports.io/standings?league={lig_id}&season={sezon}"
    req = urllib.request.Request(url)
    req.add_header("x-apisports-key", API_KEY)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            veri = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Lig {lig_id} HTTP hatasi: {e.code}")
        continue
    except Exception as e:
        print(f"Lig {lig_id} baglanti hatasi: {e}")
        continue

    if veri.get("errors"):
        print(f"Lig {lig_id} API hatasi: {veri.get('errors')}")
        continue

    response_listesi = veri.get("response", [])
    if not response_listesi:
        print(f"Lig {lig_id} ({sezon}) icin veri bos")
        continue

    lig_blogu = response_listesi[0].get("league", {})
    lig_adi = lig_blogu.get("name", "")
    ulke = lig_blogu.get("country", "")
    gruplar = lig_blogu.get("standings", [])

    takimlar = []
    for grup in gruplar:
        for sira_item in grup:
            takim = sira_item.get("team", {})
            all_istat = sira_item.get("all", {})
            goller = all_istat.get("goals", {})

            takimlar.append({
                "sira": sira_item.get("rank"),
                "takimId": takim.get("id"),
                "takim": takim.get("name"),
                "logo": takim.get("logo"),
                "grup": sira_item.get("group"),
                "oynanan": all_istat.get("played"),
                "galibiyet": all_istat.get("win"),
                "beraberlik": all_istat.get("draw"),
                "maglubiyet": all_istat.get("lose"),
                "atilanGol": goller.get("for"),
                "yenilenGol": goller.get("against"),
                "averaj": sira_item.get("goalsDiff"),
                "puan": sira_item.get("points"),
                "form": sira_item.get("form"),
                "sonGuncelleme": sira_item.get("update")
            })

    tum_puan_durumlari.append({
        "ligId": lig_id,
        "lig": lig_adi,
        "ulke": ulke,
        "sezon": sezon,
        "takimSayisi": len(takimlar),
        "takimlar": takimlar
    })
    print(f"Lig {lig_id} ({lig_adi}) eklendi: {len(takimlar)} takim")
    time.sleep(0.5)

with open("standings.json", "w", encoding="utf-8") as f:
    json.dump(tum_puan_durumlari, f, ensure_ascii=False, indent=2)

print(f"Toplam kaydedilen lig sayisi: {len(tum_puan_durumlari)}")
