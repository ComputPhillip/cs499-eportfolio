"""A one-move heuristic opponent. No minimax or search enhancement yet."""
from random import Random
from .model import Game


def choose_move(game, rng=None):
    rng = rng or Random()
    moves = game.legal_moves()
    if not moves:
        return None
    scores = []
    for move in moves:
        piece = game.board[move.start]
        preview = Game(dict(game.board), game.turn, game.forced)
        preview.apply(move)
        enemy = 'Black' if piece.color == 'White' else 'White'
        threats = Game(dict(preview.board), enemy)
        exposed = any(m.captured == move.end for m in threats.legal_moves())
        captured = game.board.get(move.captured)
        score = (bool(captured), bool(captured and captured.king), not exposed,
                 preview.board[move.end].king and not piece.king,
                 move.start[1] != (0 if piece.color == 'White' else 7))
        scores.append((score, move))
    best = max(score for score, _ in scores)
    return rng.choice([move for score, move in scores if score == best])
