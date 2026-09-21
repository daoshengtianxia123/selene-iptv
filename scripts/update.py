#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_BASE = "https://raw.githubusercontent.com/daoshengtianxia123/selene-iptv/main"

SOURCES = [
    {
        "name": "best-fan-cctv",
        "url": "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_cctv.m3u8",
        "priority": 0,
    },
    {
        "name": "best-fan-province",
        "url": "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_province.m3u8",
        "priority": 0,
    },
    {
        "name": "collect-iptv",
        "url": "https://raw.githubusercontent.com/zilong7728/Collect-IPTV/main/best_sorted.m3u8",
        "priority": 1,
    },
    {
        "name": "vbskycn",
        "url": "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.m3u",
        "priority": 2,
    },
]

CCTV_META = {
    "CCTV-1": "CCTV-1 综合",
    "CCTV-2": "CCTV-2 财经",
    "CCTV-3": "CCTV-3 综艺",
    "CCTV-4": "CCTV-4 中文国际",
    "CCTV-5": "CCTV-5 体育",
    "CCTV-5+": "CCTV-5+ 体育赛事",
    "CCTV-6": "CCTV-6 电影",
    "CCTV-7": "CCTV-7 国防军事",
    "CCTV-8": "CCTV-8 电视剧",
    "CCTV-9": "CCTV-9 纪录",
    "CCTV-10": "CCTV-10 科教",
    "CCTV-11": "CCTV-11 戏曲",
    "CCTV-12": "CCTV-12 社会与法",
    "CCTV-13": "CCTV-13 新闻",
    "CCTV-14": "CCTV-14 少儿",
    "CCTV-15": "CCTV-15 音乐",
    "CCTV-16": "CCTV-16 奥林匹克",
    "CCTV-17": "CCTV-17 农业农村",
    "CCTV-4K": "CCTV-4K 超高清",
}
CCTV_ORDER = list(CCTV_META)

PROVINCE_ORDER = [
    "北京卫视", "东方卫视", "湖南卫视", "江苏卫视", "浙江卫视",
    "广东卫视", "深圳卫视", "山东卫视", "安徽卫视", "天津卫视",
    "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "辽宁卫视",
    "黑龙江卫视", "吉林卫视", "四川卫视", "重庆卫视", "贵州卫视",
    "云南卫视", "广西卫视", "海南卫视", "陕西卫视", "山西卫视",
    "内蒙古卫视", "甘肃卫视", "青海卫视", "宁夏卫视", "新疆卫视",
    "西藏卫视", "东南卫视", "厦门卫视", "延边卫视", "安多卫视",
    "三沙卫视", "大湾区卫视",
]

ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
RESP_RE = re.compile(r"^(\d+)ms$", re.I)
USER_AGENT = "Mozilla/5.0 selene-iptv-updater/1.0"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return data.decode("utf-8-sig", errors="replace")


def parse_m3u(text: str, source: dict) -> list[dict]:
    result: list[dict] = []
    pending: dict | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("#EXTINF:"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.split(",", 1)[1].strip() if "," in line else attrs.get("tvg-name", "").strip()
            pending = {
                "name": name,
                "attrs": attrs,
                "source": source["name"],
                "priority": source["priority"],
            }
            continue

        if line.startswith("#"):
            continue

        if pending is not None:
            if line.startswith(("http://", "https://")):
                pending["url"] = line
                result.append(pending)
            pending = None

    return result


def clean_name(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "")
    s = s.replace("－", "-").replace("—", "-").replace("_", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_cctv(name: str) -> str | None:
    s = clean_name(name).upper()

    if "欧洲" in s or "美洲" in s:
        return None

    if re.search(r"CCTV\s*-?\s*4K", s):
        return "CCTV-4K"

    if re.search(r"CCTV\s*-?\s*5\s*\+", s):
        return "CCTV-5+"

    m = re.search(r"CCTV\s*-?\s*(\d{1,2})", s)
    if not m:
        return None

    n = int(m.group(1))
    key = f"CCTV-{n}"
    return key if key in CCTV_META else None


def canonical_province(name: str) -> str | None:
    s = clean_name(name)
    s = re.sub(r"(?i)\b(?:HD|UHD|FHD)\b", "", s)
    s = s.replace("高清", "").replace("超高清", "").replace("4K", "")
    s = re.sub(r"\s+", "", s)

    for channel in PROVINCE_ORDER:
        if channel in s:
            return channel
    return None


def response_ms(entry: dict) -> int:
    value = entry["attrs"].get("response-time", "")
    m = RESP_RE.match(value)
    return int(m.group(1)) if m else 999999


def candidate_score(entry: dict) -> tuple:
    # Upstream priority first; for sources with measured response-time,
    # prefer the lower latency entry.
    return (entry["priority"], response_ms(entry))


def select_channels(entries: list[dict], kind: str) -> dict[str, dict]:
    selected: dict[str, dict] = {}

    for entry in entries:
        name = entry["attrs"].get("tvg-name") or entry["name"]
        key = canonical_cctv(name) if kind == "cctv" else canonical_province(name)
        if not key:
            # Some lists have the useful display name only after the comma.
            key = canonical_cctv(entry["name"]) if kind == "cctv" else canonical_province(entry["name"])
        if not key:
            continue

        old = selected.get(key)
        if old is None or candidate_score(entry) < candidate_score(old):
            selected[key] = entry

    return selected


def esc(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')


def make_m3u(selected: dict[str, dict], order: list[str], kind: str) -> str:
    lines = ["#EXTM3U"]
    group = "央视频道" if kind == "cctv" else "卫视频道"

    for key in order:
        entry = selected.get(key)
        if not entry:
            continue

        display = CCTV_META[key] if kind == "cctv" else key
        attrs = entry["attrs"]
        tvg_id = attrs.get("tvg-id") or key
        logo = attrs.get("tvg-logo", "")
        source = entry["source"]

        info = (
            f'#EXTINF:-1 tvg-id="{esc(tvg_id)}" tvg-name="{esc(display)}" '
            f'tvg-logo="{esc(logo)}" group-title="{group}",{display}'
        )
        lines.append(f"# source: {source}")
        lines.append(info)
        lines.append(entry["url"])

    return "\n".join(lines) + "\n"


B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    zeroes = len(data) - len(data.lstrip(b"\0"))
    number = int.from_bytes(data, "big")
    chars: list[str] = []

    while number:
        number, rem = divmod(number, 58)
        chars.append(B58_ALPHABET[rem])

    encoded = "".join(reversed(chars))
    return ("1" * zeroes) + (encoded or ("" if zeroes else "1"))


def write_outputs(cctv: dict[str, dict], province: dict[str, dict]) -> None:
    cctv_text = make_m3u(cctv, CCTV_ORDER, "cctv")
    province_text = make_m3u(province, PROVINCE_ORDER, "province")

    live_lines = ["#EXTM3U"]
    for text in (cctv_text, province_text):
        for line in text.splitlines()[1:]:
            live_lines.append(line)
    live_text = "\n".join(live_lines) + "\n"

    (ROOT / "cctv.m3u").write_text(cctv_text, encoding="utf-8")
    (ROOT / "province.m3u").write_text(province_text, encoding="utf-8")
    (ROOT / "live.m3u").write_text(live_text, encoding="utf-8")

    payload = {
        "lives": {
            "china_tv": {
                "key": "china_tv",
                "name": "央视 + 卫视",
                "url": f"{RAW_BASE}/live.m3u",
                "from": "selene-iptv",
            }
        }
    }
    raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (ROOT / "selene-sub.txt").write_text(b58encode(raw_json) + "\n", encoding="utf-8")


def main() -> None:
    entries: list[dict] = []
    failures: list[str] = []

    for source in SOURCES:
        try:
            text = fetch_text(source["url"])
            parsed = parse_m3u(text, source)
            print(f'{source["name"]}: {len(parsed)} entries')
            entries.extend(parsed)
        except Exception as exc:
            failures.append(f'{source["name"]}: {exc}')
            print(f'WARN: {source["name"]}: {exc}')

    if not entries:
        raise SystemExit("No upstream playlist could be loaded; refusing to overwrite outputs.")

    cctv = select_channels(entries, "cctv")
    province = select_channels(entries, "province")

    if len(cctv) < 8:
        raise SystemExit(f"Too few CCTV channels ({len(cctv)}); refusing to overwrite outputs.")
    if len(province) < 10:
        raise SystemExit(f"Too few province channels ({len(province)}); refusing to overwrite outputs.")

    write_outputs(cctv, province)

    print(f"Generated CCTV channels: {len(cctv)}")
    print(f"Generated province channels: {len(province)}")
    if failures:
        print("Completed with upstream warnings:")
        for item in failures:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
