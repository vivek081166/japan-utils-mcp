# japan-utils-mcp

MCP server exposing **Japan-specific utilities** to AI agents (Claude, Cursor, Cline, Continue, etc.). Hand your agent the small bag of JP-specific functions every Japan-related task needs but no generic LLM gets right reliably:

- 🗓️ **Era ↔ Western year** — `令和8年` ↔ `2026`
- 🔤 **Kanji → Hepburn romaji** — `山田太郎` → `yamada tarou`
- 📮 **Postal code lookup** — `150-0001` → `東京都 渋谷区 神宮前`
- 🎌 **National holiday calendar** — is `2026-05-03` a holiday? what about all of 2026?

Built on top of well-maintained Japanese libraries (`jpholiday`, `posuto`, `pykakasi`) — wrapped as MCP tools so any AI agent can call them without re-implementing reading rules, era arithmetic, or postal data.

## Why this exists

Generic LLMs hallucinate on JP-specific data:

- "What year is 令和8年?" — often wrong
- "Convert 山田太郎 to romaji" — gets the surname wrong half the time
- "What's the address for postal code 150-0001?" — fabricates plausible-looking nonsense
- "Is May 3rd a Japanese holiday?" — guesses

This MCP gives them a deterministic answer.

## Tools

| Tool | What it does |
|------|--------------|
| `era_to_western` | `令和8年` / `R8` / `Reiwa 8` / `令和元年` → Gregorian year + era metadata |
| `western_to_era` | `2026` → era kanji (`令和`), English (`Reiwa`), year-of-era (`8`), formatted strings |
| `kanji_to_romaji` | Mixed Japanese text → Hepburn romaji + hiragana reading |
| `lookup_postal_code` | 7-digit JP postal code → prefecture / city / area, with kana readings |
| `is_holiday` | Date string → is it a national holiday? + Japanese name + weekday |
| `list_holidays` | Year → all national holidays for that year |

All tools return structured JSON. See tool docstrings in `src/japan_utils_mcp/server.py` for full schemas and examples.

## Installation

### Run with `uvx` (no install — recommended once published)

```bash
uvx japan-utils-mcp
```

### From source (today)

```bash
git clone https://github.com/vivek081166/japan-utils-mcp.git
cd japan-utils-mcp
uv sync
uv run japan-utils-mcp
```

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "japan-utils": {
      "command": "uvx",
      "args": ["japan-utils-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add japan-utils -- uvx japan-utils-mcp
```

### Cursor / Cline / Continue

Same JSON snippet as Claude Desktop, in their respective MCP config files.

## Examples

Once connected, ask your agent things like:

> **What year is 令和8年?**
> → `era_to_western("令和8年")` → `2026`

> **What's the address for postal code 150-0001?**
> → `lookup_postal_code("150-0001")` → `東京都 渋谷区 神宮前`

> **Convert 山田太郎 to romaji.**
> → `kanji_to_romaji("山田太郎")` → `yamada tarou`

> **Is May 3rd 2026 a Japanese holiday?**
> → `is_holiday("2026-05-03")` → `憲法記念日` (Constitution Memorial Day)

> **List all Japanese holidays in 2026.**
> → `list_holidays(2026)` → 18 holidays with names and dates

## Caveats

- **Romaji of personal names** uses the most common reading — proper nouns with unusual readings will be wrong. This is a fundamental limitation of any kanji-to-romaji conversion without disambiguation context.
- **Postal code dataset** ships via the `posuto` library, refreshed against Japan Post's monthly KEN_ALL. If you need ultra-fresh data, refresh `posuto` periodically.
- **Holidays** covers national holidays (国民の祝日) only — not company-specific or regional observances.
- **Era conversion** supports Meiji (明治) through Reiwa (令和). Earlier eras are not supported.

## Development

```bash
git clone https://github.com/vivek081166/japan-utils-mcp.git
cd japan-utils-mcp
uv sync
uv run python -c "from japan_utils_mcp.server import era_to_western; print(era_to_western('令和8年'))"
```

## License

MIT
