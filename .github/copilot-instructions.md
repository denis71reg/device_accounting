## Device Accounting — Copilot instructions

Short, actionable guidance to help an AI coding agent be productive in this repository.

Scope and big picture
- This is a small single-service Python project that maintains a local SQLite database (`devices.db`) with four tables: `locations`, `device_types`, `employees`, and `devices`.
- Core logic lives in the `da` package: `da/database.py` (DB schema + helpers) and `da/main.py` (seed/run CLI-like entrypoint).
- The app is intended to run as a single process (script or container). The Dockerfile runs `python -m da.main`.

Key files to reference when making changes
- `da/database.py`: database initialization, insert helpers (add_*), and simple selects (get_full_inventory). Use existing helper patterns (context managers with `sqlite3.connect`) and follow the current error printing style.
- `da/main.py`: data seeding and textual report output. Example of how helpers are used (seed_data, print_report, main).
- `Dockerfile` / `docker-compose.yml`: container build and mounting `devices.db` for persistence. `requirements.txt` currently empty — CI/build assumes it can be left blank or populated.

Developer workflows & run commands
- Local run (python): from repository root run `python -m da.main` (same as Docker CMD). This creates `devices.db` in the working directory if missing and prints a text report.
- Docker: `docker build -t device_accounting .` then `docker run -v $(pwd)/devices.db:/app/devices.db device_accounting` or use `docker-compose up --build` per `docker-compose.yml`.

Project-specific conventions and patterns
- SQLite usage: code uses `sqlite3.connect(DB_NAME)` and `.execute(...).fetchone()`/`.fetchall()` directly. Keep this pattern; prefer context managers for connections.
- Error reporting: functions print messages (e.g., `[OK]`, `[INFO]`, `[ERROR]`) rather than raising exceptions. When modifying helpers preserve the same surface behavior unless intentionally changing the contract.
- IDs resolution: lookup helpers return `id` or `None` (e.g., `get_location_id`). Use truthy checks as shown in `add_device`.

Integration points & external dependencies
- No external services. Persistence is SQLite file `devices.db` in repo root by default (Docker image expects `/app/devices.db` mounted).
- `requirements.txt` is present but empty. If adding dependencies, update `requirements.txt` and the `Dockerfile` will pick them up during build.

Tests and linting
- There are no tests in the repo. When adding tests, prefer a lightweight pytest setup and add `pytest` to `requirements.txt` and a simple `tests/` folder.

Small edits guidance
- When updating schema in `initialize_database()`, keep migration considerations in mind: do not drop tables silently; prefer additive ALTER TABLE steps or document manual migration needed.
- Keep SQL strings triple-quoted and aligned with existing style.
- For print formatting (reporting), follow the fixed-width display in `print_report()` (use same column widths).

Examples (use these as templates)
- Adding a location: call `add_location("Склад Основной")` — helper prints status and handles uniqueness via sqlite integrity errors.
- Creating a device: follow `add_device(...)` usage in `da/main.py`; the function resolves type/location/employee names and prints informative messages on missing references.

If you need clarification
- Ask where to place tests or if changing error behavior is allowed. For schema migrations, request permission before destructive changes.

End of instructions.
