# Checkers software design and engineering enhancement

This desktop application develops the supplied IT 450 checkers baseline into a modular, animated 2D application. Original files are preserved separately in `../original`. This is the software engineering enhancement; minimax, database storage, and replay remain later milestones.

## Run

Use Python 3.10 or newer with Tkinter installed. From this directory:

```powershell
python run_checkers.py
python -m unittest discover -s tests -v
```

No third-party packages are required. Select a piece and click a gold destination marker. Captures are mandatory; a multi-capture must continue with the same piece. White moves first. Choose human play or either computer color. Custom setup opens an empty board with a piece/erase brush; pieces placed on their promotion row become kings. Start position begins play with the selected first turn. New game restores standard play. The board scales with the window and moves animate without blocking the event loop.

## Architecture and changes

- `model.py`: GUI-independent piece, move, board state, legal moves, terminal detection, and capture continuation. Integer coordinates replace the original float-index capture failure.
- `view.py`: owns canvas objects, responsive coordinate conversion, piece rendering, and legal-destination overlays. Removed pieces and overlays are deleted; existing piece objects are reused.
- `app.py`: coordinates input, setup, animation, opponent scheduling, and save/load dialogs. Generation tokens invalidate pending animation or computer callbacks when a new game is loaded or started.
- `ai.py`: one-move heuristic selection with random tie-breaking. It evaluates successor positions and honors forced continuations. Its ordering differs from the original filter chain; no strength improvement is claimed.
- `storage.py`: validates a new position completely before the controller replaces the active game. JSON preserves board, turn, and capture continuation; it uses temporary-file replacement on save. Legacy `checkers.txt` is importable. Opponent selection remains a UI preference and is not saved. Resignation outcomes and move history are not persisted.

The application explicitly uses American checkers crowning behavior: reaching the king row ends the turn. The original code could continue capturing after promotion. Save/import validation rejects invalid coordinates, duplicate squares, invalid colors/ranks, impossible continuations, and excessive piece counts. Custom positions may start with only one side, in which case terminal detection ends play immediately.

## Baseline and attribution

The original `Checkers_v24.py` uses a Tkinter wrapper by John Zelle. Its `graphics.py` identifies its author and GPL licensing; the original dependency and notices are retained unchanged. The enhanced renderer uses Tkinter directly and does not load the old `.pyc` files. Do not claim authorship of the original library. Preserve applicable original licensing and attribution when distributing the project.


## Validation and remaining work

Automated checks cover standard legal moves, mandatory and chained captures, promotion, king movement, blocked players, legal computer decisions, save/load continuation, legacy import, and malformed records. These tests do not establish playing strength. Inspect resizing, animation, setup, save/load dialogs, and human/computer play on the target desktop before recording the final demonstration. The required pre-enhancement review can still show the preserved original files.

Initial validation on November 1, 2026: all 10 automated tests passed. A hidden-window Tkinter smoke check passed coordinate round trips, 100 redraws holding at 112 canvas objects, animation completion, and reset during animation. All seven original file copies matched their supplied SHA-256 hashes. A full manual visual/playthrough review remains outstanding.
