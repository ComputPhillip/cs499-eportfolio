"""American checkers rules; no window, disk access, or global mutable state."""
from dataclasses import dataclass, field
from typing import Optional

Square = tuple[int, int]


@dataclass(frozen=True)
class Piece:
    color: str
    king: bool = False


@dataclass(frozen=True)
class Move:
    start: Square
    end: Square
    captured: Optional[Square] = None


@dataclass
class Game:
    board: dict[Square, Piece] = field(default_factory=dict)
    turn: str = 'White'
    forced: Optional[Square] = None
    winner: Optional[str] = None

    @classmethod
    def standard(cls):
        return cls({(x, y): Piece('White' if y < 3 else 'Black')
                    for x in range(8) for y in range(8)
                    if (x + y) % 2 == 0 and (y < 3 or y > 4)})

    @staticmethod
    def inside(square):
        return all(0 <= n < 8 for n in square)

    def candidates(self, square, captures_only=False):
        piece = self.board.get(square)
        if not piece or piece.color != self.turn:
            return []
        x, y = square
        directions = (-1, 1) if piece.king else ((1,) if piece.color == 'White' else (-1,))
        moves = []
        for dy in directions:
            for dx in (-1, 1):
                near, far = (x + dx, y + dy), (x + 2 * dx, y + 2 * dy)
                other = self.board.get(near)
                if other and other.color != piece.color and self.inside(far) and far not in self.board:
                    moves.append(Move(square, far, near))
                elif not captures_only and self.inside(near) and near not in self.board:
                    moves.append(Move(square, near))
        return moves

    def legal_moves(self):
        if self.winner:
            return []
        if self.forced is not None:
            return self.candidates(self.forced, captures_only=True)
        moves = [move for square in self.board for move in self.candidates(square)]
        captures = [move for move in moves if move.captured is not None]
        return captures or moves

    def apply(self, move):
        if move not in self.legal_moves():
            raise ValueError('That move is not legal.')
        piece = self.board.pop(move.start)
        if move.captured is not None:
            del self.board[move.captured]
        crowned = not piece.king and move.end[1] == (7 if piece.color == 'White' else 0)
        self.board[move.end] = Piece(piece.color, piece.king or crowned)
        # American checkers ends the turn on crowning, even if a king could jump back.
        if move.captured is not None and not crowned and self.candidates(move.end, True):
            self.forced = move.end
        else:
            self.forced = None
            self.turn = 'Black' if self.turn == 'White' else 'White'
            if not self.legal_moves():
                self.winner = piece.color

    def resolve_terminal(self):
        if not self.legal_moves():
            self.winner = 'Black' if self.turn == 'White' else 'White'
