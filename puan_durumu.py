import os
import json


def main():
    api_key = os.environ.get("FOOTBALL_API_KEY", "").strip()
    if not api_key:
        print("puan_durumu.py: FOOTBALL_API_KEY bulunamadi, adim atlaniyor.")
        if not os.path.exists("standings.json"):
            with open("standings.json", "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        return


if __name__ == "__main__":
    main()
