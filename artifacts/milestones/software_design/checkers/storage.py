"""Validated JSON saves and read-only import of the original text format."""
import json
from pathlib import Path
from .model import Game, Piece


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Unsupported save format.')
    if data.get('turn') not in ('White', 'Black'):
        raise ValueError('Invalid player turn.')
    records = data.get('pieces')
    if not isinstance(records, list) or not records or len(records) > 24:
        raise ValueError('A saved position must contain 1–24 pieces.')
    board = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Invalid piece record.')
        x, y, color, king = (record.get(k) for k in ('x', 'y', 'color', 'king'))
        if type(x) is not int or type(y) is not int or not Game.inside((x, y)) or (x + y) % 2:
            raise ValueError('Invalid piece square.')
        if color not in ('White', 'Black') or type(king) is not bool or (x, y) in board:
            raise ValueError('Invalid or duplicate piece.')
        if not king and y == (7 if color == 'White' else 0):
            raise ValueError('A piece on its crowning row must be a king.')
        board[x, y] = Piece(color, king)
    if any(sum(p.color == c for p in board.values()) > 12 for c in ('White', 'Black')):
        raise ValueError('Too many pieces of one color.')
    forced = data.get('forced')
    if forced is not None:
        if not isinstance(forced, list) or len(forced) != 2 or any(type(n) is not int for n in forced):
            raise ValueError('Invalid capture continuation.')
        forced = tuple(forced)
    game = Game(board, data['turn'], forced)
    if forced is not None and not game.candidates(forced, True):
        raise ValueError('Saved continuation has no legal capture.')
    game.resolve_terminal()
    return game


def load(path):
    path = Path(path)
    if path.stat().st_size > 100_000:
        raise ValueError('Save file is too large.')
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.txt':
        lines = text.splitlines()
        if not lines or lines[-1] not in ('W', 'B'):
            raise ValueError('Invalid legacy turn marker.')
        pieces = []
        for row in lines[:-1]:
            if len(row) != 4 or not row[:2].isdigit() or row[2] not in 'WB' or row[3] not in 'PK':
                raise ValueError('Invalid legacy piece record.')
            pieces.append(dict(x=int(row[0]), y=int(row[1]), color='White' if row[2]=='W' else 'Black', king=row[3]=='K'))
        return validate(dict(version=1, turn='White' if lines[-1]=='W' else 'Black', pieces=pieces))
    return validate(json.loads(text))


def save(game, path):
    data = dict(version=1, turn=game.turn, forced=list(game.forced) if game.forced else None,
                pieces=[dict(x=x, y=y, color=p.color, king=p.king) for (x,y),p in sorted(game.board.items())])
    validate(data)
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    try:
        temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
