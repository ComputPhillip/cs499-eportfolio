import unittest
from random import Random
from threading import Event
from checkers.model import Game, Piece, Move
from checkers.ai import search, evaluate, WIN, SearchCancelled


def reference_score(game, depth, perspective):
    """Small independent exhaustive oracle with no alpha/beta or ordering."""
    legal = game.legal_moves()
    if game.winner or not legal:
        winner = game.winner or ('Black' if game.turn == 'White' else 'White')
        return WIN if winner == perspective else -WIN
    if depth <= 0 and game.forced is None:
        return evaluate(game, perspective)
    values = []
    for move in legal:
        child = Game(dict(game.board), game.turn, game.forced, game.winner)
        child.apply(move)
        values.append(reference_score(child, depth-int(child.turn != game.turn), perspective))
    return (max if game.turn == perspective else min)(values)


class SearchTests(unittest.TestCase):
    def test_seeded_positions_match_exhaustive_oracle(self):
        rng = Random(499)
        game = Game.standard()
        for step in range(16):
            if game.winner:
                break
            if step % 2 == 0:
                with self.subTest(step=step, turn=game.turn):
                    before = Game(dict(game.board),game.turn,game.forced,game.winner)
                    result = search(game,2)
                    plain = search(game,2,pruning=False)
                    self.assertEqual(result.score,reference_score(game,2,game.turn))
                    self.assertEqual((result.score,result.move),(plain.score,plain.move))
                    self.assertLessEqual(result.stats.nodes,plain.stats.nodes)
                    self.assertEqual(game,before)
                    child = Game(dict(game.board),game.turn,game.forced)
                    child.apply(result.move)
                    self.assertEqual(result.score,reference_score(child,2-int(child.turn!=game.turn),game.turn))
            game.apply(rng.choice(game.legal_moves()))

    def test_opening_pruning_reduces_nodes(self):
        a,b=search(Game.standard(),3),search(Game.standard(),3,pruning=False)
        self.assertEqual((a.move,a.score),(b.move,b.score))
        self.assertLess(a.stats.nodes,b.stats.nodes)
        self.assertGreater(a.stats.cutoffs,0)

    def test_capture_chain_finishes_at_depth_one(self):
        game=Game({(0,0):Piece('White'),(1,1):Piece('Black'),(3,3):Piece('Black')})
        result=search(game,1)
        self.assertEqual(result.score,WIN)
        self.assertEqual(result.move,Move((0,0),(2,2),(1,1)))
        game.apply(result.move)
        self.assertEqual(search(game,1).move,Move((2,2),(4,4),(3,3)))

    def test_black_capture_win(self):
        game=Game({(4,4):Piece('Black'),(3,3):Piece('White')},turn='Black')
        self.assertEqual(search(game,1).score,WIN)

    def test_terminal_and_blocked(self):
        game=Game({(0,0):Piece('White')},turn='Black')
        self.assertEqual(search(game,2).score,-WIN)
        self.assertIsNone(search(game,2).move)
        game.winner='Black'
        self.assertEqual(search(game,2).score,WIN)

    def test_cancellation_and_depth_validation(self):
        event=Event(); event.set()
        with self.assertRaises(SearchCancelled):
            search(Game.standard(),4,cancel=event)
        for depth in [0,-1,9,True,1.5]:
            with self.assertRaises(ValueError): search(Game.standard(),depth)

    def test_deterministic_ties(self):
        game=Game.standard()
        self.assertEqual(search(game,2).move,search(game,2).move)


if __name__=='__main__': unittest.main()
