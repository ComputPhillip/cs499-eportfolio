"""SQLite position library. One transaction replaces a parent and all its pieces."""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from . import storage
from .model import Game

SCHEMA_VERSION = 1
MODES = ('Two players', 'Computer Black', 'Computer White')

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_games (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) BETWEEN 1 AND 80),
    turn TEXT NOT NULL CHECK(turn IN ('White','Black')),
    forced_x INTEGER, forced_y INTEGER,
    winner TEXT CHECK(winner IN ('White','Black')),
    opponent TEXT NOT NULL CHECK(opponent IN ('Two players','Computer Black','Computer White')),
    depth INTEGER NOT NULL CHECK(depth BETWEEN 1 AND 4),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK((forced_x IS NULL AND forced_y IS NULL) OR
          (forced_x IS NOT NULL AND forced_y IS NOT NULL AND
           forced_x BETWEEN 0 AND 7 AND forced_y BETWEEN 0 AND 7 AND (forced_x+forced_y)%2=0))
);
CREATE TABLE IF NOT EXISTS pieces (
    game_id INTEGER NOT NULL REFERENCES saved_games(id) ON DELETE CASCADE,
    x INTEGER NOT NULL CHECK(x BETWEEN 0 AND 7),
    y INTEGER NOT NULL CHECK(y BETWEEN 0 AND 7),
    color TEXT NOT NULL CHECK(color IN ('White','Black')),
    king INTEGER NOT NULL CHECK(king IN (0,1)),
    PRIMARY KEY(game_id,x,y),
    CHECK((x+y)%2=0),
    CHECK(king=1 OR NOT ((color='White' AND y=7) OR (color='Black' AND y=0)))
);
CREATE INDEX IF NOT EXISTS games_recent ON saved_games(updated_at DESC,id DESC);
"""


@dataclass(frozen=True)
class SavedPosition:
    id: int
    name: str
    game: Game
    opponent: str
    depth: int


class PositionLibrary:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError('Unsupported database schema version.')
            if version == 0:
                # Refuse to reinterpret an unrelated database as a checkers library.
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if tables:
                    raise ValueError('This file is not a checkers position library.')
                conn.executescript('BEGIN;\n' + SCHEMA + '\nPRAGMA user_version=1;\nCOMMIT;')
            # Check expected columns before creating a dialog for this file.
            conn.execute('SELECT id,name,turn,forced_x,forced_y,winner,opponent,depth,created_at,updated_at FROM saved_games LIMIT 0')
            conn.execute('SELECT game_id,x,y,color,king FROM pieces LIMIT 0')

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _validated(game, opponent, depth):
        if opponent not in MODES or type(depth) is not int or not 1 <= depth <= 4:
            raise ValueError('Invalid opponent or search depth.')
        data = dict(version=1, turn=game.turn, forced=list(game.forced) if game.forced else None,
                    pieces=[dict(x=x,y=y,color=p.color,king=p.king) for (x,y),p in game.board.items()])
        clean = storage.validate(data)
        if game.winner not in (None,'White','Black'):
            raise ValueError('Invalid winner.')
        if clean.winner is not None and game.winner not in (None,clean.winner):
            raise ValueError('Winner conflicts with the terminal board.')
        if game.winner and game.forced:
            raise ValueError('A finished position cannot require another capture.')
        clean.winner = game.winner or clean.winner
        return clean

    def save(self, name, game, opponent='Two players', depth=3, position_id=None):
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError('Use a name containing 1 to 80 characters.')
        name = name.strip()
        clean = self._validated(game,opponent,depth)
        fx,fy = clean.forced or (None,None)
        fields = (name,clean.turn,fx,fy,clean.winner,opponent,depth)
        with self._connection() as conn:
            if position_id is None:
                cursor = conn.execute('INSERT INTO saved_games(name,turn,forced_x,forced_y,winner,opponent,depth) VALUES(?,?,?,?,?,?,?)',fields)
                position_id = cursor.lastrowid
            else:
                cursor = conn.execute("UPDATE saved_games SET name=?,turn=?,forced_x=?,forced_y=?,winner=?,opponent=?,depth=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",fields+(position_id,))
                if cursor.rowcount != 1:
                    raise KeyError('Saved position no longer exists.')
                conn.execute('DELETE FROM pieces WHERE game_id=?',(position_id,))
            conn.executemany('INSERT INTO pieces(game_id,x,y,color,king) VALUES(?,?,?,?,?)',
                             [(position_id,x,y,p.color,int(p.king)) for (x,y),p in sorted(clean.board.items())])
        return position_id

    def list_positions(self):
        with self._connection() as conn:
            return [dict(row) for row in conn.execute('''SELECT g.id,g.name,g.turn,g.winner,g.opponent,g.depth,g.updated_at,
                (SELECT count(*) FROM pieces p WHERE p.game_id=g.id) AS piece_count
                FROM saved_games g ORDER BY g.updated_at DESC,g.id DESC''')]

    def load(self, position_id):
        with self._connection() as conn:
            # Explicit transaction gives parent and child reads one consistent snapshot.
            conn.execute('BEGIN')
            row = conn.execute('SELECT * FROM saved_games WHERE id=?',(position_id,)).fetchone()
            if row is None:
                raise KeyError('Saved position no longer exists.')
            records = conn.execute('SELECT x,y,color,king FROM pieces WHERE game_id=? ORDER BY x,y',(position_id,)).fetchall()
            if any(type(r['king']) is not int or r['king'] not in (0,1) for r in records):
                raise ValueError('Invalid stored piece rank.')
            pieces = [dict(x=r['x'],y=r['y'],color=r['color'],king=bool(r['king'])) for r in records]
            if (row['forced_x'] is None) != (row['forced_y'] is None):
                raise ValueError('Incomplete stored capture continuation.')
            forced = None if row['forced_x'] is None else [row['forced_x'],row['forced_y']]
            game = storage.validate(dict(version=1,turn=row['turn'],forced=forced,pieces=pieces))
            game.winner = row['winner'] or game.winner
            clean = self._validated(game,row['opponent'],row['depth'])
            return SavedPosition(row['id'],row['name'],clean,row['opponent'],row['depth'])

    def delete(self, position_id):
        with self._connection() as conn:
            if conn.execute('DELETE FROM saved_games WHERE id=?',(position_id,)).rowcount != 1:
                raise KeyError('Saved position no longer exists.')
