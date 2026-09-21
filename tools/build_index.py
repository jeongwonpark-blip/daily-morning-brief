# -*- coding: utf-8 -*-
"""data/YYYY-MM-DD.json 들을 훑어 data/index.json 과 data/search.json 을 다시 만든다.

새 브리핑 JSON을 data/ 에 넣은 뒤 이 스크립트를 한 번 돌리면 끝.
  python3 tools/build_index.py
"""
import os, re, json, glob, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# 시황 지표 정규화 — 날마다 표기가 조금씩 달라서 키워드로 묶는다.
SERIES = [
    ("KOSPI",  "코스피",       lambda n: "코스피" in n and "닥" not in n),
    ("KOSDAQ", "코스닥",       lambda n: "코스닥" in n),
    ("SPX",    "S&P 500",      lambda n: "S&P" in n),
    ("NDX",    "나스닥",       lambda n: "나스닥" in n),
    ("USDKRW", "원/달러",      lambda n: "원/달러" in n or "USD" in n.upper()),
    ("KTB10",  "국고채 10년",  lambda n: "국고채" in n and "10" in n),
    ("UST10",  "미 10년물",    lambda n: ("미" in n or "美" in n) and "10년" in n),
    ("WTI",    "WTI",          lambda n: "WTI" in n.upper()),
    ("VIX",    "VIX",          lambda n: "VIX" in n.upper()),
]


def to_num(v):
    v = re.sub(r"[^\d.\-]", "", (v or "").replace("−", "-"))
    try:
        return round(float(v), 4)
    except ValueError:
        return None


def pct_num(p):
    return to_num(p)


def market_map(day):
    out = {}
    for row in (day["market"]["tiles"] + day["market"]["subs"]):
        n = row.get("name", "")
        for key, _lab, test in SERIES:
            if key in out or not test(n):
                continue
            v = to_num(row.get("value"))
            if v is None:
                continue
            out[key] = {"v": v, "pct": pct_num(row.get("pct")), "pctText": (row.get("pct") or "").strip(),
                        "dir": row.get("dir", "flat"), "raw": row.get("value"),
                        "chg": row.get("change", ""), "name": n}
    return out


def build():
    days, search = [], []
    for path in sorted(glob.glob(os.path.join(DATA, "20*-*-*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        items = [(s["name"], it) for s in d["sections"] for it in s["items"]]
        days.append({
            "date": d["date"],
            "weekday": d["weekday"],
            "sub": d.get("sub", ""),
            "asof": d["market"].get("asof", ""),
            "counts": {"items": len(items),
                       "impact": sum(1 for _s, it in items if it.get("impact")),
                       "sections": len(d["sections"])},
            "lead": items[0][1]["title"] if items else "",
            "sections": [s["name"] for s in d["sections"]],
            "market": market_map(d),
        })
        search.append({"d": d["date"],
                       "i": [{"s": sec, "t": it["title"],
                              "x": (it.get("summary", "") + " " + it.get("why", "")).strip()}
                             for sec, it in items]})

    days.sort(key=lambda x: x["date"])
    search.sort(key=lambda x: x["d"])
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes")

    json.dump({"updated": stamp,
               "series": [{"key": k, "label": lab} for k, lab, _ in SERIES],
               "days": days},
              open(os.path.join(DATA, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    json.dump({"updated": stamp, "days": search},
              open(os.path.join(DATA, "search.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("index.json  %d일" % len(days))
    print("search.json %d건" % sum(len(x["i"]) for x in search))
    for d in days:
        print("  %s (%s) 기사 %2d · 주가반응 %d · 지표 %s"
              % (d["date"], d["weekday"], d["counts"]["items"], d["counts"]["impact"],
                 ",".join(sorted(d["market"]))))


if __name__ == "__main__":
    build()
