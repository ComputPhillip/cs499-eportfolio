# Checkers algorithms and data structures enhancement

This milestone adds depth-limited minimax with alpha-beta pruning to the graphical checkers application. Launch this copy to use search-based play. The software design milestone remains separately preserved in `../software_design`, with SHA-256 checksums in `../software_design_manifest.json`. The earlier `../../enhanced` copy also remains unchanged. Original IT 450 files remain in `../../original`.

## Run and reproduce

Requires Python 3.10 or newer with Tkinter. No external packages are required. From this directory:

```powershell
python run_checkers.py
python -m unittest discover -s tests -v
python benchmark_search.py
```

Choose Computer White or Computer Black and a search depth from 1 to 4. The interface displays positions visited, alpha-beta cutoffs, and search elapsed time after each decision. New game, custom setup, load, and changes to player mode or depth invalidate pending decisions. Search runs on a daemon worker thread; only the main thread touches Tkinter. Cancellation is checked at every visited position. Interface tests use a hidden Tk window and skip if no display is available.

## Search and data structures

`checkers/ai.py` implements deterministic minimax. Scores are always relative to the player who started the search. The current state's player determines whether a node maximizes or minimizes that score. A terminal win scores 100000 and a loss scores -100000, dominating the heuristic. Nonterminal evaluation uses pawn material (100), king material (175), pawn advancement (4 per row), and a small center bonus (3).

Depth counts completed player turns. A jump that requires another capture by the same piece does not decrement depth or switch the maximizing player. Search completes the capture sequence before applying its evaluation cutoff. Promotion follows the software design model: crowning ends the turn. The selected answer is one legal action; the controller searches again if a forced continuation remains.

The board is a dictionary keyed by integer coordinate tuples. Frozen Piece and Move data classes allow safe sharing of piece values while each search child receives an independent dictionary. Legal actions form a sorted list. Recursive depth-first traversal keeps the active path and sibling move lists, rather than materializing an entire search tree. Captures, captured kings, promotions, and coordinate order provide deterministic ordering. Strict improvement selects a new best move, so equally scored choices have stable tie-breaking.

Alpha is the best maximizing bound and beta is the best minimizing bound. Once alpha is at least beta, remaining siblings cannot improve the decision for the ancestor, and the branch stops. `search(..., pruning=False)` uses the same evaluation and move order with pruning disabled. The tests also implement a separate exhaustive oracle to check scores independently of the pruning switch.

For branching factor b and turn depth d, minimax is exponential in depth, approximately O(b^d) for a tree of complete turns. Forced capture chains add action nodes within those turns. Alpha-beta retains exponential worst-case cost; ordering determines how much it saves. Board copying and legal-move validation add per-node cost. This implementation favors clarity and isolation of state over compact bitboards or in-place undo. It does not use a transposition table. The API accepts depths 1 through 8, but deeper searches can take substantially longer; the UI caps selection at 4.

## Verification and measurements

The regression suite retains software design rules/storage checks and adds score agreement with an independent exhaustive oracle, deterministic ties, unchanged input states, alpha-beta versus plain minimax agreement, both player perspectives, forced capture completion, terminal positions, invalid depths, and cancellation. Tk integration checks exercise actual search-to-animation completion and rejection of a stale worker result after reset.

`benchmark_search.py` compares three fixed positions at depths 2, 3, and 4, using three runs per algorithm and median elapsed time. The midgame comes from 18 seeded legal actions (seed 499). Both algorithms share ordering and evaluation. `benchmarks/search_results.csv` records nodes, leaves, cutoffs, score, selected move, median time, repetition count, Python version, and platform. Nodes include the root, terminal states, and evaluated leaves; cutoffs count cutoff events, not all unvisited descendants. Search timing excludes animation and the UI scheduling delay.

The initial run on November 1, 2026 produced matching scores and moves for all nine position/depth pairs. At opening depth 4, nodes fell from 1828 to 459; at seeded-midgame depth 4, from 1580 to 281. The forced capture position used 3 nodes with either algorithm. Consult the CSV for measured time; fewer nodes are not a universal guarantee of faster execution. These fixtures establish correctness and examples of pruning savings, not tournament strength or exhaustive game-rule coverage.

## Scope and attribution

`heuristic_ai.py` preserves the software design opponent for future comparisons. The live interface now uses minimax; the old rng argument to choose_move is accepted for compatibility but does not randomize search ties. Rules and storage retain the software design implementation. The algorithms UI reserves space for the status footer before allocating the expanding canvas, fixing a clipping issue found during visible testing. JSON saves still omit opponent settings, history, and resignation outcomes. No database, replay, repetition draw rule, or playing-strength tournament is included. Representative visible interaction checks are recorded below; a full standard-position game and broader user review remain useful before the final portfolio demonstration.

## Visible interaction checks on November 1 2026

The desktop interface was exercised through mouse and keyboard input. At the default window size, the initial canvas layout pushed the status footer out of view. Reserving the footer before packing the canvas corrected the issue in this algorithms version; the preserved software design snapshot was not edited. A Tk regression test checks footer visibility and non-overlap at 960 by 760 and the minimum 720 by 560 client size.

Observed results:

- Standard opening: selected White at (2,2), saw legal destination highlights, moved to (3,3), and observed the computer reply. The telemetry displayed depth 3, 75 nodes, 11 cutoffs, and 0.003 seconds for that reply.
- Capture: White jumped from (3,3) to (1,5); Black's reply recaptured. Counts changed from 12 each to 11 each, and the turn returned to White.
- Settings: changed depth from 3 to 4 while preserving the active board.
- Save/load: saved the 11-versus-11 position through the native dialog, reset to the 24-piece opening, and loaded the saved file. The visible position and White turn were restored. The file is retained as `benchmarks/ui_saved_game.json` for reproduction.
- Custom endgame: placed White at (0,0), Black at (1,1) and (3,3), and started play. White's first jump to (2,2) retained the turn and displayed the forced-continuation message. The second jump to (4,4) removed the remaining Black piece and displayed the White win message.

These are targeted interaction checks, including completion of a custom endgame, rather than a complete standard-opening game or proof of playing strength. Timings shown during interaction are single observations, not benchmark medians.

The original graphics library identifies John Zelle as its author; original attribution remains preserved, and the enhanced renderer uses Tkinter directly.
