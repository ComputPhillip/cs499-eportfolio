import tempfile
import unittest
from pathlib import Path
from random import Random
from checkers.model import Game, Piece, Move
from checkers.ai import choose_move
from checkers import storage

W, B = Piece('White'), Piece('Black')


class RulesTests(unittest.TestCase):
    def test_standard(self):
        game=Game.standard()
        self.assertEqual(len(game.board),24)
        self.assertEqual(len(game.legal_moves()),7)

    def test_capture_and_continuation(self):
        game=Game({(0,0):W,(1,1):B,(3,3):B,(6,0):W})
        self.assertEqual(game.legal_moves(),[Move((0,0),(2,2),(1,1))])
        game.apply(game.legal_moves()[0])
        self.assertEqual(game.forced,(2,2))
        self.assertEqual(game.turn,'White')
        self.assertEqual(game.legal_moves(),[Move((2,2),(4,4),(3,3))])
        game.apply(game.legal_moves()[0])
        self.assertEqual(game.winner,'White')

    def test_invalid_move_does_not_mutate(self):
        game=Game.standard()
        before=dict(game.board)
        with self.assertRaises(ValueError):
            game.apply(Move((0,0),(7,7)))
        self.assertEqual(game.board,before)

    def test_crowning_ends_capture_turn(self):
        game=Game({(1,5):W,(2,6):B,(4,6):B})
        game.apply(Move((1,5),(3,7),(2,6)))
        self.assertTrue(game.board[3,7].king)
        self.assertEqual(game.turn,'Black')
        self.assertIsNone(game.forced)

    def test_king_can_move_backward(self):
        game=Game({(2,2):Piece('White',True),(7,7):B})
        self.assertIn(Move((2,2),(1,1)),game.legal_moves())

    def test_blocked_opponent(self):
        game=Game({(0,0):W},turn='Black')
        self.assertIsNone(choose_move(game))
        game.resolve_terminal()
        self.assertEqual(game.winner,'White')

    def test_ai_returns_legal_move_without_mutating(self):
        game=Game.standard()
        before=dict(game.board)
        self.assertIn(choose_move(game,Random(10)),game.legal_moves())
        self.assertEqual(game.board,before)


class StorageTests(unittest.TestCase):
    def test_roundtrip_preserves_forced_capture(self):
        game=Game({(0,0):W,(1,1):B,(3,3):B})
        game.apply(game.legal_moves()[0])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'game.json'
            storage.save(game,path)
            loaded=storage.load(path)
        self.assertEqual(loaded,game)

    def test_reject_invalid_coordinates_duplicate_and_turn(self):
        base=dict(version=1,turn='White',pieces=[dict(x=0,y=0,color='White',king=False)])
        for bad in [dict(base,turn='bad'),dict(base,pieces=base['pieces']*2),
                    dict(base,pieces=[dict(x=9,y=0,color='White',king=False)])]:
            with self.assertRaises(ValueError):
                storage.validate(bad)

    def test_legacy_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'checkers.txt'
            path.write_text('00WK\n77BK\nW')
            game=storage.load(path)
        self.assertEqual(game.board[(0,0)],Piece('White',True))
        self.assertEqual(game.turn,'White')


if __name__=='__main__':
    unittest.main()
