"""Minimax with alpha-beta pruning; depth counts completed turns, not jumps."""
from dataclasses import dataclass
from math import inf
from time import perf_counter
from .model import Game, Move

WIN = 100_000

class SearchCancelled(Exception):
    """Cancelled searches never return partial decisions."""

@dataclass
class SearchStats:
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    elapsed_seconds: float = 0.0

@dataclass
class SearchResult:
    move: Move | None
    score: int
    depth: int
    stats: SearchStats

def evaluate(game, perspective):
    total = 0
    for (x, y), piece in game.board.items():
        value = 175 if piece.king else 100 + 4 * (y if piece.color == 'White' else 7-y)
        value += 3 if 2 <= x <= 5 and 2 <= y <= 5 else 0
        total += value if piece.color == perspective else -value
    return total

def ordered_moves(game, moves):
    """Identical stable order in both searches, including deterministic ties."""
    def key(move):
        piece = game.board[move.start]
        captured = game.board.get(move.captured)
        promotion = not piece.king and move.end[1] == (7 if piece.color == 'White' else 0)
        return (-int(captured is not None), -int(bool(captured and captured.king)),
                -int(promotion), move.start, move.end)
    return sorted(moves, key=key)

def search(game, depth=3, *, pruning=True, cancel=None):
    if type(depth) is not int or not 1 <= depth <= 8:
        raise ValueError('Search depth must be an integer from 1 through 8.')
    started = perf_counter()
    stats = SearchStats()
    perspective = game.turn
    def visit(state, remaining, alpha, beta):
        if cancel is not None and cancel.is_set():
            raise SearchCancelled()
        stats.nodes += 1
        moves = state.legal_moves()
        if state.winner or not moves:
            stats.leaves += 1
            winner = state.winner or ('Black' if state.turn == 'White' else 'White')
            return (WIN if winner == perspective else -WIN), None
        if remaining <= 0 and state.forced is None:
            stats.leaves += 1
            return evaluate(state, perspective), None
        maximizing = state.turn == perspective
        best_score, best_move = (-inf if maximizing else inf), None
        for move in ordered_moves(state, moves):
            # Immutable pieces are shared; mutable board dictionaries are copied.
            child = Game(dict(state.board), state.turn, state.forced, state.winner)
            child.apply(move)
            child_depth = remaining - int(child.turn != state.turn)
            score, _ = visit(child, child_depth, alpha, beta)
            if best_move is None or (score > best_score if maximizing else score < best_score):
                best_score, best_move = score, move
            if maximizing:
                alpha = max(alpha, best_score)
            else:
                beta = min(beta, best_score)
            if pruning and alpha >= beta:
                stats.cutoffs += 1
                break
        return best_score, best_move
    score, move = visit(game, depth, -inf, inf)
    stats.elapsed_seconds = perf_counter() - started
    return SearchResult(move, int(score), depth, stats)

def choose_move(game, rng=None, depth=3):
    """Compatibility entry point; rng is unused because ties are deterministic."""
    return search(game, depth).move
