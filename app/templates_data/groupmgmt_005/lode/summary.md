# Anjani — Lode Summary

Anjani is a modern, fully-asynchronous, class-based **Telegram group management bot** built on **Pyrogram/Pyrofork** (a Telegram MTProto client library). It is a community administration bot (usable in production as @dAnjani_bot) under active development by the UserbotIndo team.

## Key facts
- **Language:** Python 3.9+ (fully async with `async`/`await`).
- **Package:** `anjani`, version 2.14.20, distributed on PyPI (`poetry`-managed).
- **Entry point:** `anjani.main:start` (via `anjani/main.py`).
- **Data stores:** MongoDB (primary domain data via `database_provider`), SQLite (Pyrogram session/storage via `SQLiteStorage`).
- **Key runtime deps:** `pyro`/`pyrofork`, `aiohttp`, `mongodb` driver, i18n (YAML locale files).

## Architecture
The bot is built as a **single `Anjani` class** that composes several **mixin base classes** (Python MRO composition):
`Anjani(TelegramBot, DatabaseProvider, PluginExtender, CommandDispatcher, EventDispatcher)`.

- **Core mixins** (in `anjani/core/`): `anjani_bot`, `telegram_bot`, `database_provider`, `plugin_extenter`, `command_dispatcher`, `event_dispatcher`, `sqlite_storage`, `metrics`, `anjani_mixin_base`.
- **Plugin system:** a **class-based plugin** model (`anjani/plugin.py::Plugin`). Plugins declare commands via decorators (`@command.filters(...)`) and listeners via `@listener(...)`. Dispatchers register/unregister them at load time.
- **CustomFilter & filters:** permission/context filters in `anjani/filters.py` and `anjani/util/types.py`.

## Plugin inventory
- `anjani/plugins/` (22 files) — core user-facing modules: admins, backups, debug, federation, filters, language, lockings, main, misc, muting, notes, purge, reporting, restriction, rules, spam_shield, staff_tools, stats, topic, users, welcome.
- `anjani/internal_plugins/` (4) — canonical, health, spam_prediction, and package root.
- `anjani/custom_plugins/` (2) — user custom plugins.
- `anjani/language/` — i18n strings: `en.yml`, `id.yml`, `de.yml`.

## Scale
~13,500 LOC in the main package (excluding tests). Tests are minimal: `test/test_base_converter.py`, `test/test_tg.py`.

See [architecture/summary.md](architecture/summary.md) for the layer diagram and [practices.md](practices.md) for conventions.