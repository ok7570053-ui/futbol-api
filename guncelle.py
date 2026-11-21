import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY", "").strip()
THESPORTSDB_KEY = os.environ.get("THESPORTSDB_KEY", "3").strip() or "3"

TR_TZ = timezone(timedelta(hours=3))
BUGUN = datetime.now(TR_TZ).strftime("%Y-%m-%d")

FD_COMPETITIONS = {
    "PL": ("Premier Lig (İngiltere)", "İngiltere"),
    "PD": ("LaLiga", "İspanya"),
    "BL1": ("Bundesliga", "Almanya"),
    "SA": ("Serie A (İtalya)", "İtalya"),
    "FL1": ("Ligue 1", "Fransa"),
    "CL": ("Şampiyonlar Ligi", "Avrupa"),
}

TSDB_LEAGUES = [
    {"id": "4339", "lig": "Trendyol Süper Lig", "ulke": "Türkiye"},
    {"id": "4628", "lig": "Trendyol 1. Lig", "ulke": "Türkiye"},
    {"id": "4337", "lig": "Eredivisie", "ulke": "Hollanda"},
    {"id": "4344", "lig": "Premier Lig (Portekiz)", "ulke": "Portekiz"},
    {"id": "4351", "lig": "Serie A (Brezilya)", "ulke": "Brezilya"},
    {"id": "4346", "lig": "MLS", "ulke": "ABD"},
    {"id": "4348", "lig": "J1 Lig (Japonya)", "ulke": "Japonya"},
    {"id": "4396", "lig": "Premier Lig (Arjantin)", "ulke": "Arjantin"},
    {"id": "4330", "lig": "Premiership (İskoçya)", "ulke": "İskoçya"},
    {"id": "4334", "lig": "Ligue 2", "ulke": "Fransa"},
    {"id": "4335", "lig": "LaLiga 2", "ulke": "İspanya"},
    {"id": "4394", "lig": "Serie B (İtalya)", "ulke": "İtalya"},
    {"id": "4757", "lig": "2. Bundesliga", "ulke": "Almanya"},
]


def http_get_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def durum_donustur_fd(status_str):
    harita = {
        "SCHEDULED": "NS",
        "TIMED": "NS",
        "IN_PLAY": "LIVE",
        "PAUSED": "HT",
        "FINISHED": "FT",
        "POSTPONED": "PST",
        "CANCELLED": "CANC",
        "SUSPENDED": "SUSP",
    }
    return harita.get((status_str or "").upper(), status_str or "NS")


def durum_donustur_tsdb(status_str, ev_gol, dep_gol):
    s = (status_str or "").strip()
    if s.lower() in ("match finished", "ft", "aet", "pen"):
        return "FT"
    if ev_gol is not None and dep_gol is not None and not s:
        return "FT"
    return s if s else "NS"


def football_data_cek():
    if not FOOTBALL_DATA_KEY:
        print("Football-Data: FOOTBALL_DATA_KEY tanimli degil, atlaniyor.")
        return []

    sonuclar = []
    codes = ",".join(FD_COMPETITIONS.keys())
    url = f"https://api.football-data.org/v4/matches?competitions={codes}&dateFrom={BUGUN}&dateTo={BUGUN}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}

    try:
        data = http_get_json(url, headers=headers)
        matches = data.get("matches", [])
        for m in matches:
            comp_code = m.get("competition", {}).get("code", "")
            varsayilan_lig, varsayilan_ulke = FD_COMPETITIONS.get(
                comp_code,
                (m.get("competition", {}).get("name", "Bilinmeyen Lig"), m.get("area", {}).get("name", ""))
            )
            utc_tarih = m.get("utcDate", "")
            tarih_str = BUGUN
            saat_str = ""
            if utc_tarih:
                try:
                    dt_utc = datetime.fromisoformat(utc_tarih.replace("Z", "+00:00"))
                    dt_tr = dt_utc.astimezone(TR_TZ)
                    tarih_str = dt_tr.strftime("%Y-%m-%d")
                    saat_str = dt_tr.strftime("%H:%M")
                except ValueError:
                    parca = utc_tarih.split("T")
                    tarih_str = parca[0]
                    saat_str = parca[1][:5] if len(parca) > 1 else ""

            score_ft = m.get("score", {}).get("fullTime", {})
            sonuclar.append({
                "id": f"fd_{m.get('id')}",
                "lig": varsayilan_lig,
                "ulke": varsayilan_ulke,
                "ev": m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", ""),
                "dep": m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", ""),
                "tarih": tarih_str,
                "saat": saat_str,
                "durum": durum_donustur_fd(m.get("status", "")),
                "evGol": score_ft.get("home"),
                "depGol": score_ft.get("away"),
            })
        print(f"Football-Data: {len(sonuclar)} mac bulundu.")
    except urllib.error.HTTPError as e:
        print(f"Football-Data HTTP hatasi: {e.code}")
    except Exception as e:
        print(f"Football-Data hata: {e}")

    return sonuclar


def thesportsdb_cek():
    sonuclar = []

    for idx, lig_info in enumerate(TSDB_LEAGUES):
        lig_id = lig_info["id"]
        url = f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_KEY}/eventsday.php?d={BUGUN}&l={lig_id}"
        try:
            data = http_get_json(url, headers={"User-Agent": "Mozilla/5.0"})
            events = data.get("events") or []
            for ev in events:
                if (ev.get("strSport") or "").lower() != "soccer":
                    continue

                ev_gol_raw = ev.get("intHomeScore")
                dep_gol_raw = ev.get("intAwayScore")
                ev_gol = int(ev_gol_raw) if ev_gol_raw is not None and str(ev_gol_raw).isdigit() else None
                dep_gol = int(dep_gol_raw) if dep_gol_raw is not None and str(dep_gol_raw).isdigit() else None

                saat_ham = (ev.get("strTime") or "").strip()
                saat_str = saat_ham[:5] if len(saat_ham) >= 5 else ""

                sonuclar.append({
                    "id": f"tsdb_{ev.get('idEvent')}",
                    "lig": lig_info["lig"],
                    "ulke": lig_info["ulke"],
                    "ev": ev.get("strHomeTeam", ""),
                    "dep": ev.get("strAwayTeam", ""),
                    "tarih": ev.get("dateEvent") or BUGUN,
                    "saat": saat_str,
                    "durum": durum_donustur_tsdb(ev.get("strStatus", ""), ev_gol, dep_gol),
                    "evGol": ev_gol,
                    "depGol": dep_gol,
                })
        except urllib.error.HTTPError as e:
            print(f"TheSportsDB ({lig_info['lig']}) HTTP hatasi: {e.code}")
        except Exception as e:
            print(f"TheSportsDB ({lig_info['lig']}) hata: {e}")

        if idx < len(TSDB_LEAGUES) - 1:
            time.sleep(0.35)

    print(f"TheSportsDB: {len(sonuclar)} mac bulundu.")
    return sonuclar


def birlestir_ve_tekillestir(liste_a, liste_b):
    birlesik = []
    gorulen = set()

    for mac in (liste_a + liste_b):
        ev_k = (mac.get("ev") or "").strip().lower()
        dep_k = (mac.get("dep") or "").strip().lower()
        tarih_k = (mac.get("tarih") or "").strip()
        anahtar = f"{tarih_k}|{ev_k}|{dep_k}"

        if not ev_k or not dep_k or anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        birlesik.append(mac)

    birlesik.sort(key=lambda x: (x.get("saat") or "99:99", x.get("lig") or ""))
    return birlesik


def mevcut_maclari_oku(dosya_yolu="maclar.json"):
    if not os.path.exists(dosya_yolu):
        return []
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            veri = json.load(f)
            return veri if isinstance(veri, list) else []
    except Exception:
        return []


def main():
    print(f"Hibrit fikstur cekimi basladi | Tarih (TR): {BUGUN}")
    fd_maclar = football_data_cek()
    tsdb_maclar = thesportsdb_cek()
    yeni_maclar = birlestir_ve_tekillestir(fd_maclar, tsdb_maclar)

    eski_maclar = mevcut_maclari_oku("maclar.json")

    if len(yeni_maclar) > 0:
        with open("maclar.json", "w", encoding="utf-8") as f:
            json.dump(yeni_maclar, f, ensure_ascii=False, indent=2)
        print(f"Basarili: {len(yeni_maclar)} mac maclar.json dosyasina yazildi.")
    else:
        if len(eski_maclar) > 0:
            print(f"Yeni mac 0 geldi; mevcut {len(eski_maclar)} maclik maclar.json korundu.")
        else:
            with open("maclar.json", "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            print("Yeni mac 0 geldi ve onceki kayit yoktu; bos liste yazildi.")


if __name__ == "__main__":
    main()
