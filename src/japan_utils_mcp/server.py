"""japan-utils-mcp — MCP server exposing Japan-specific utilities to AI agents.

Tools provided:
    - era_to_western:    convert "令和8年" / "R8" → 2026
    - western_to_era:    convert 2026 → "令和8年" with English alias
    - kanji_to_romaji:   transliterate Japanese text to Hepburn romaji
    - lookup_postal_code: 7-digit Japanese 郵便番号 → prefecture/city/area
    - is_holiday:        check whether a given date is a Japanese national holiday
    - list_holidays:     list all national holidays for a given year
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import jpholiday  # type: ignore[import-untyped]
import posuto  # type: ignore[import-untyped]
import pykakasi  # type: ignore[import-untyped]
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("japan-utils")

# ──────────────────────────────────────────────────────────────────────
# Era conversion
# ──────────────────────────────────────────────────────────────────────

# Era → (start_year, kanji_name, english_name, single_letter_alias)
# Year-of-era 1 starts in start_year. e.g. 令和1 = 2019, 令和元年 = same.
_ERAS: list[tuple[int, str, str, str]] = [
    (2019, "令和", "Reiwa", "R"),
    (1989, "平成", "Heisei", "H"),
    (1926, "昭和", "Showa", "S"),
    (1912, "大正", "Taisho", "T"),
    (1868, "明治", "Meiji", "M"),
]

_ERA_KANJI_TO_INFO: dict[str, tuple[int, str, str, str]] = {
    e[1]: e for e in _ERAS
}
_ERA_LETTER_TO_INFO: dict[str, tuple[int, str, str, str]] = {
    e[3]: e for e in _ERAS
}


def _parse_era_year(text: str) -> tuple[str, int]:
    """Parse an era-year string into (era_kanji, year_of_era).

    Accepts: '令和8年', '令和8', '令和元年', 'R8', 'reiwa 8', 'Reiwa8'.
    Raises ValueError on failure.
    """
    s = text.strip()

    # Match '令和元年' or '令和8年' or '令和8'
    m = re.match(r"^(明治|大正|昭和|平成|令和)\s*(元|\d+)\s*年?$", s)
    if m:
        era_kanji = m.group(1)
        year_str = m.group(2)
        year_of_era = 1 if year_str == "元" else int(year_str)
        return era_kanji, year_of_era

    # Match 'R8', 'H30', 'S64', 'T15', 'M45' (single-letter alias)
    m = re.match(r"^([RHSTMrhstm])\s*(\d+)$", s)
    if m:
        letter = m.group(1).upper()
        info = _ERA_LETTER_TO_INFO.get(letter)
        if info is None:
            raise ValueError(f"Unknown era letter: {letter}")
        return info[1], int(m.group(2))

    # Match 'Reiwa 8', 'Heisei30', 'showa 64' (English name)
    m = re.match(r"^([A-Za-z]+)\s*(\d+)$", s)
    if m:
        name_lower = m.group(1).lower()
        for _start, kanji, english, _letter in _ERAS:
            if english.lower() == name_lower:
                return kanji, int(m.group(2))
        raise ValueError(f"Unknown era name: {m.group(1)}")

    raise ValueError(
        f"Could not parse era-year from {text!r}. "
        "Examples: '令和8年', '令和元年', 'R8', 'Reiwa 8'."
    )


@mcp.tool()
def era_to_western(era_year: str) -> dict[str, Any]:
    """Convert a Japanese era year to a Western (Gregorian) year.

    Args:
        era_year: An era-year string. Accepts kanji form ('令和8年', '令和8',
            '令和元年'), single-letter alias ('R8', 'H30'), or English alias
            ('Reiwa 8', 'Heisei 30').

    Returns:
        dict with keys:
            - western_year: int (Gregorian year)
            - era_kanji: str (e.g. '令和')
            - era_english: str (e.g. 'Reiwa')
            - year_of_era: int

    Examples:
        era_to_western("令和8年")  → {"western_year": 2026, ...}
        era_to_western("R8")      → {"western_year": 2026, ...}
        era_to_western("Reiwa 8") → {"western_year": 2026, ...}
    """
    era_kanji, year_of_era = _parse_era_year(era_year)
    info = _ERA_KANJI_TO_INFO[era_kanji]
    start_year, _kanji, english, _letter = info
    western = start_year + year_of_era - 1
    return {
        "western_year": western,
        "era_kanji": era_kanji,
        "era_english": english,
        "year_of_era": year_of_era,
    }


@mcp.tool()
def western_to_era(year: int) -> dict[str, Any]:
    """Convert a Western (Gregorian) year to its Japanese era year.

    Note: this returns the era in effect for the *majority* of the given
    Gregorian year. For year transitions (e.g. 1989 split between 昭和64
    and 平成1), it returns the newer era.

    Args:
        year: Western year (e.g. 2026). Must be 1868 or later.

    Returns:
        dict with keys:
            - era_kanji: str
            - era_english: str
            - year_of_era: int (1 for the first year of an era; written as 元年 in formal Japanese)
            - era_year_kanji: str (e.g. '令和8年')
            - era_year_short: str (e.g. 'R8')

    Examples:
        western_to_era(2026) → {"era_kanji": "令和", "era_english": "Reiwa",
                                 "year_of_era": 8, "era_year_kanji": "令和8年",
                                 "era_year_short": "R8"}
    """
    if year < 1868:
        raise ValueError("Years before 1868 (Meiji 1) are not supported.")

    for start_year, kanji, english, letter in _ERAS:
        if year >= start_year:
            year_of_era = year - start_year + 1
            if year_of_era == 1:
                era_year_kanji = f"{kanji}元年"
            else:
                era_year_kanji = f"{kanji}{year_of_era}年"
            return {
                "era_kanji": kanji,
                "era_english": english,
                "year_of_era": year_of_era,
                "era_year_kanji": era_year_kanji,
                "era_year_short": f"{letter}{year_of_era}",
            }

    raise ValueError(f"Could not map year {year} to any known era.")


# ──────────────────────────────────────────────────────────────────────
# Romaji
# ──────────────────────────────────────────────────────────────────────

_kakasi = pykakasi.kakasi()


@mcp.tool()
def kanji_to_romaji(text: str) -> dict[str, Any]:
    """Transliterate Japanese text (kanji + kana mix) to Hepburn romaji.

    Args:
        text: Japanese text. May contain kanji, hiragana, katakana, ASCII.
            Non-Japanese characters pass through unchanged.

    Returns:
        dict with keys:
            - romaji: str (space-separated Hepburn romaji)
            - hiragana: str (kanji converted to hiragana, kana preserved)
            - input: str (echo of the original input)

    Examples:
        kanji_to_romaji("山田太郎") → {"romaji": "yamada tarou", "hiragana": "やまだたろう"}
        kanji_to_romaji("東京駅") → {"romaji": "toukyou eki", "hiragana": "とうきょうえき"}

    Caveats:
        - Kanji with multiple readings (e.g. proper nouns) may be ambiguous.
          The transliteration uses the most common reading, which is
          sometimes wrong for personal names. Use as a starting point, not a
          guarantee.
    """
    results = _kakasi.convert(text)
    romaji = " ".join(r["hepburn"] for r in results if r["hepburn"]).strip()
    hira = "".join(r["hira"] for r in results)
    return {
        "romaji": romaji,
        "hiragana": hira,
        "input": text,
    }


# ──────────────────────────────────────────────────────────────────────
# Postal code lookup
# ──────────────────────────────────────────────────────────────────────


@mcp.tool()
def lookup_postal_code(postal_code: str) -> dict[str, Any]:
    """Look up a Japanese postal code (郵便番号) and return address components.

    Args:
        postal_code: 7-digit JP postal code. Accepts '150-0001', '1500001',
            '150 0001', or with full-width digits.

    Returns:
        dict with keys:
            - postal_code: str (normalized 7-digit form)
            - prefecture: str (都道府県)
            - city: str (市区町村)
            - area: str (町域 — neighborhood/area)
            - prefecture_kana: str (katakana reading of prefecture)
            - city_kana: str
            - area_kana: str
            - found: bool (true if the code resolved)

    Examples:
        lookup_postal_code("150-0001") → {
            "postal_code": "1500001",
            "prefecture": "東京都",
            "city": "渋谷区",
            "area": "神宮前",
            ...
            "found": True,
        }
    """
    digits = re.sub(r"[^0-9]", "", postal_code)
    digits = digits.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    if len(digits) != 7 or not digits.isdigit():
        return {
            "postal_code": postal_code,
            "found": False,
            "error": "Postal code must be 7 digits.",
        }

    try:
        entry = posuto.get(digits)
    except KeyError:
        return {
            "postal_code": digits,
            "found": False,
            "error": "Postal code not found in dataset.",
        }
    except Exception as exc:
        return {
            "postal_code": digits,
            "found": False,
            "error": f"Lookup failed: {exc}",
        }

    return {
        "postal_code": digits,
        "prefecture": entry.prefecture,
        "city": entry.city,
        "area": entry.neighborhood,
        "prefecture_kana": entry.prefecture_kana,
        "city_kana": entry.city_kana,
        "area_kana": entry.neighborhood_kana,
        "found": True,
    }


# ──────────────────────────────────────────────────────────────────────
# Holidays
# ──────────────────────────────────────────────────────────────────────


def _parse_date(text: str) -> date:
    """Accept 'YYYY-MM-DD', 'YYYY/MM/DD', or 'YYYYMMDD'."""
    s = text.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Could not parse date {text!r}. Use YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD."
    )


@mcp.tool()
def is_holiday(date_str: str) -> dict[str, Any]:
    """Check whether a date is a Japanese national holiday (祝日).

    Args:
        date_str: Date in 'YYYY-MM-DD', 'YYYY/MM/DD', or 'YYYYMMDD' format.

    Returns:
        dict with keys:
            - date: str (normalized 'YYYY-MM-DD')
            - is_holiday: bool
            - name_jp: str | None (holiday name in Japanese, if applicable)
            - weekday_jp: str (e.g. '月', '火', ...)
            - weekday_en: str (e.g. 'Monday')

    Examples:
        is_holiday("2026-05-03") → {"is_holiday": True, "name_jp": "憲法記念日", ...}
        is_holiday("2026-05-04") → {"is_holiday": True, "name_jp": "みどりの日", ...}
        is_holiday("2026-05-08") → {"is_holiday": False, "name_jp": None, ...}

    Notes:
        - Covers national holidays only (祝日 designated by the 国民の祝日に関する法律).
          Does not cover company-specific or regional observances.
        - 振替休日 (substitute holidays) are correctly identified.
    """
    d = _parse_date(date_str)
    name = jpholiday.is_holiday_name(d)
    weekday_jp = "月火水木金土日"[d.weekday()]
    weekday_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
        d.weekday()
    ]
    return {
        "date": d.isoformat(),
        "is_holiday": name is not None,
        "name_jp": name,
        "weekday_jp": weekday_jp,
        "weekday_en": weekday_en,
    }


@mcp.tool()
def list_holidays(year: int) -> dict[str, Any]:
    """List all Japanese national holidays for a given year.

    Args:
        year: Western year (e.g. 2026).

    Returns:
        dict with keys:
            - year: int
            - count: int
            - holidays: list of {date: 'YYYY-MM-DD', name_jp: str, weekday_en: str}

    Examples:
        list_holidays(2026)  →  {"year": 2026, "count": 16, "holidays": [...]}
    """
    holidays = []
    for d, name_jp in jpholiday.year_holidays(year):
        holidays.append(
            {
                "date": d.isoformat(),
                "name_jp": name_jp,
                "weekday_en": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ][d.weekday()],
            }
        )
    return {
        "year": year,
        "count": len(holidays),
        "holidays": holidays,
    }


# ──────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
