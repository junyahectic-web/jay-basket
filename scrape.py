"""藤沢市公共施設予約システムで、バスケットボールができる室場の空き枠を取得し docs/data.json に保存する。
GitHub Actions から1時間ごとに実行し、docs/index.html（検索画面）がこのデータを読む。

使い方:  python scrape.py
対象:    「目的から探す」でバスケットボール・ミニバスケットボールができる室場。
         秋葉台・秩父宮はサブアリーナだけ（含めるかは画面のチェックで選ぶ）。
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jpholiday
from playwright.sync_api import sync_playwright

BASE = "https://fujisawacity.service-now.com/facilities_reservation"
DAYS = 120
JST = timezone(timedelta(hours=9))  # GitHub Actions のサーバーは UTC なので日本時間で「今日」を決める
OUTPUT = Path(__file__).with_name("docs") / "data.json"
# 「屋内スポーツ」の中で検索する目的（上から順に探す）
PURPOSES = ["バスケットボール", "ミニバスケットボール"]
# 施設名にこの文字を含む施設は、サブアリーナ（室場名にこの文字を含む室場）だけを取得する
SUB_ARENAS = {"akibadai": ("秋葉台", "第2体育室"), "chichibu": ("秩父宮", "サブアリーナ")}


def clean_room(text: str) -> str:
    """「体育室（定員200名） 枠の確認/予約」→「体育室」"""
    return re.sub(r"（定員.*", "", text).replace("　", " ").strip()


def sub_arena_key(facility: str, room: str):
    """(対象にするか, サブアリーナならそのキー) を返す。"""
    for key, (fac_word, room_word) in SUB_ARENAS.items():
        if fac_word in facility:
            return room_word in room, key
    return True, None


def find_rooms(page, purpose: str) -> list:
    """目的で検索し、[(施設名, 室場名, 予約枠確認URL)] を返す。"""
    page.goto(f"{BASE}?id=facility_search&tab=2", wait_until="networkidle", timeout=60000)
    page.get_by_text("屋内スポーツ", exact=True).first.click()
    page.locator(f"[id$='_{purpose}']").first.check()
    page.get_by_role("button", name="検索").first.click()
    page.wait_for_selector("h4.facility-name")
    page.wait_for_load_state("networkidle")
    facilities = page.evaluate("""() => [...document.querySelectorAll('h4.facility-name')].map(h => ({
        fac: h.textContent.trim(),
        rooms: [...h.closest('.ng-scope').querySelectorAll('.facility-room p')]
            .map(p => [p.textContent.trim(), p.querySelector('a')?.getAttribute('href')]),
    }))""")
    return [(f["fac"], clean_room(text), f"{BASE}{href}") for f in facilities for text, href in f["rooms"]]


def fetch_week(page, api_url: str, body: dict, d: date) -> dict:
    """ページ内で週データ取得APIを呼ぶ（ページのセッショントークンを使う）。"""
    return page.evaluate(
        """async ([url, body]) => {
            const r = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json',
                          'X-UserToken': window.g_ck},
                body: JSON.stringify(body),
            });
            return (await r.json()).result.data;
        }""",
        [api_url, {**body, "input_date": d.isoformat()}],
    )


def fetch_free_slots(page, url: str, today: date, end: date) -> list:
    """室場の空き枠を [(日付, 時間帯)] で返す。"""
    # ページ表示時に飛ぶ最初の週データ取得リクエストから、APIのURLと送信内容を取得
    with page.expect_request(lambda r: "getMonthlyData" in (r.post_data or "")) as req_info:
        page.goto(url, wait_until="networkidle", timeout=60000)
    req = req_info.value
    api_url, body = req.url, json.loads(req.post_data)

    # 指定日の前後3日（計7日）分が返るが、月をまたぐ部分は切れるため、
    # まだ取得していない日があればその日を基準に取り直す
    slots, days = {}, set()
    d = today
    while d <= end:
        if d.isoformat() not in days:
            data = fetch_week(page, api_url, body, min(d + timedelta(days=3), end))
            slots.update(data.get("slots") or {})
            days.update(data.get("date_list_keys") or [])
            days.add(d.isoformat())  # 枠が無い日でも無限ループしないように
        d += timedelta(days=1)

    free = []
    for key, s in slots.items():
        day, period = key.split("_", 1)
        if s and s.get("value") == "O" and today.isoformat() <= day <= end.isoformat():
            free.append((day, period))
    return sorted(free)


def main():
    today = datetime.now(JST).date()
    end = today + timedelta(days=DAYS - 1)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # URL → 室場の情報に集約（両方の目的で出る室場は1回だけ取得）
        rooms = {}
        for purpose in PURPOSES:
            for facility, room, url in find_rooms(page, purpose):
                target, key = sub_arena_key(facility, room)
                if target:
                    rooms.setdefault(url, {"facility": facility, "room": room, "purposes": [],
                                           "sub_arena": key})["purposes"].append(purpose)
        print(f"対象: {len(rooms)}室場")

        slots = []
        for i, (url, info) in enumerate(rooms.items()):
            free = fetch_free_slots(page, url, today, end)
            print(f"{info['facility']} {info['room']}: 空き {len(free)}枠")
            slots += [[i, day, period] for day, period in free]
        browser.close()

    holidays = {}
    d = today
    while d <= end:
        if name := jpholiday.is_holiday_name(d):
            holidays[d.isoformat()] = name
        d += timedelta(days=1)

    OUTPUT.write_text(json.dumps({
        "updated": datetime.now(JST).isoformat(timespec="minutes"),
        "start": today.isoformat(),
        "end": end.isoformat(),
        "rooms": [{**info, "purposes": "・".join(info["purposes"])} for info in rooms.values()],
        "slots": slots,  # [室場の番号, 日付, 時間帯]
        "holidays": holidays,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"保存: {OUTPUT}（空き {len(slots)}枠、{today} 〜 {end}）")


if __name__ == "__main__":
    main()
