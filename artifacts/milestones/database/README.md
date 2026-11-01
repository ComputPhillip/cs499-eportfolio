# Checkers database enhancement

This separate milestone builds on the algorithms version while retaining its minimax opponent and graphical board. Earlier milestone files are unchanged. `previous_milestone_manifest.json` records the algorithms source hashes taken before copying.

## Run

Requires Python 3.10 or newer with Tkinter and SQLite (both in the standard library):

```powershell
python run_checkers.py
python -m unittest discover -s tests -v
```

Use **Saved positions** to open the local library. Give the current board a name and choose **Save new**. Select a saved row to load it, replace it with the current board, or delete it. Replacement and deletion ask for confirmation. Close the dialog to resume computer play. Start a custom position and wait for an active move to finish before opening the library. The existing Load/Save buttons still import legacy text and read/write JSON.

The library is created on demand at `data/positions.sqlite3` beside this milestone's launcher. Run from a folder you can write to. Copy the database while the application is closed to make a backup. Runtime databases are excluded from version control; there is no bundled personal game data.

## Data model

- `saved_games`: integer primary key, unique trimmed name, side to move, optional forced-capture coordinates, optional winner, opponent mode, search depth, creation and update timestamps in UTC.
- `pieces`: one row per occupied square, composite primary key `(game_id, x, y)`, piece color and king flag. `game_id` references `saved_games` with `ON DELETE CASCADE`.
- `games_recent` indexes update time and ID for recent-first listing. A correlated count query supplies each position's piece count without storing a redundant count.

This one-to-many relationship separates game metadata from repeating piece records. Primary keys prevent duplicate squares; foreign keys prevent orphaned pieces. CHECK constraints enforce square bounds, dark squares, valid colors, king flags, promotion rows, modes, depths, and paired continuation coordinates. Application validation adds cross-row checks such as piece counts and legal capture continuation. The database is a position library, not a move-history or replay model.

## Integrity and security

All user values use SQL placeholders, including names and record IDs. Foreign keys are enabled on every connection. Insert and replacement operations commit metadata and all piece rows as one transaction. Failed replacement rolls back both the deletion of old pieces and metadata changes. A load uses an explicit read transaction so metadata and piece queries share a consistent snapshot; loaded content is revalidated before it replaces the displayed game.

Schema version 1 is stored in `PRAGMA user_version`. Unknown versions and unversioned files with existing tables are rejected; no migration from a prior database version is needed because this is the first database milestone. Expected columns are checked at open. Connections close after each operation. The GUI uses short synchronous local operations, while the existing search worker remains separate.

The library preserves board, turn, capture continuation, winner (including resignation), opponent mode and depth. JSON saves intentionally retain their earlier narrower format. A loaded position can resume computer play immediately when its saved mode assigns that turn to the computer.

This is a local single-user application. Parameter binding and validation protect specific data boundaries; they do not provide authentication, encryption, cloud backup, hostile-file isolation, or a comprehensive security audit. There is no history, replay, undo, repetition draw rule, or multiuser conflict resolution. Large-library latency and full manual usability remain unmeasured.

## Verification on November 1 2026

The complete suite passes 31 tests: 20 inherited rules, storage, search and interface tests; nine database tests; and two library-dialog integration tests. New checks cover create/read/update/delete across reopened connections; cascade deletion; forced-capture and resignation round trips; an SQL-injection-shaped name; duplicate names; a deliberately failing child insert that proves replacement rollback; foreign keys and CHECK constraints; invalid inputs and missing IDs; empty-piece tampering and bypassed rank/continuation constraints; and unknown schema versions. Tk checks invoke save/replace/load with settings restoration, resignation between forced jumps, and cancellation/confirmation of deletion. Resignation clears pending capture continuation in this milestone so a finished position can be saved. The inherited geometry test passes at 960 by 760 and 720 by 560.

Tests use temporary databases and do not alter user saves. In the restricted authoring environment, Python's `tempfile.tempdir` was redirected to a writable workspace test directory; the normal unittest command above applies outside that sandbox. These checks validate representative behavior, not every possible damaged database or a complete human playthrough.

See `ALGORITHMS_README.md` for inherited minimax design and benchmark results. Its statements about missing database support describe the earlier milestone. The snapshot manifest can be used to confirm that algorithms files remained unchanged.

Review the work before submitting. Original graphics-library attribution to John Zelle remains in the original artifact; this enhanced interface uses Tkinter directly.

## Targeted visible checks

The database milestone was operated through its visible Windows interface on November 1, 2026. The main window and 700 by 440 library dialog displayed readable controls and an unobstructed board/footer. A new named opening save appeared with 24 pieces and White turn. Replacing that entry with a new name updated its row after confirmation. After a legal White opening move and a computer reply, loading the saved entry restored the visible starting arrangement and White turn. Opening the deletion prompt and choosing No preserved the row. The final deletion path is covered by automated dialog and database tests. These targeted checks are not a full human game or broad usability study.
