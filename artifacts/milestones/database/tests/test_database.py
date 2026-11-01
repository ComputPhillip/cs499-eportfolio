import sqlite3
import tempfile
import unittest
from pathlib import Path
from checkers.database import PositionLibrary
from checkers.model import Game, Piece, Move


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'positions.sqlite3'
        self.library=PositionLibrary(self.path)

    def tearDown(self):self.temp.cleanup()

    def test_create_read_update_delete_across_connections(self):
        game=Game.standard()
        id=self.library.save('Opening',game,'Computer Black',4)
        reopened=PositionLibrary(self.path)
        saved=reopened.load(id)
        self.assertEqual((saved.game,saved.opponent,saved.depth),(game,'Computer Black',4))
        game.apply(game.legal_moves()[0])
        self.assertEqual(reopened.save('After one move',game,'Two players',2,id),id)
        self.assertEqual(reopened.load(id).game,game)
        self.assertEqual(reopened.list_positions()[0]['piece_count'],24)
        reopened.delete(id)
        self.assertEqual(reopened.list_positions(),[])
        with self.library._connection() as conn:self.assertEqual(conn.execute('SELECT count(*) FROM pieces').fetchone()[0],0)

    def test_capture_continuation_and_resignation_round_trip(self):
        game=Game({(0,0):Piece('White'),(1,1):Piece('Black'),(3,3):Piece('Black')})
        game.apply(Move((0,0),(2,2),(1,1)))
        id=self.library.save('Chain',game)
        self.assertEqual(self.library.load(id).game,game)
        resigned=Game.standard();resigned.winner='Black'
        id=self.library.save('Resigned',resigned)
        self.assertEqual(self.library.load(id).game.winner,'Black')
        self.assertEqual(self.library.load(id).game.legal_moves(),[])

    def test_names_are_bound_values_and_duplicates_do_not_overwrite(self):
        name="Robert'); DROP TABLE pieces;--"
        id=self.library.save(name,Game.standard())
        self.assertEqual(self.library.load(id).name,name)
        with self.assertRaises(sqlite3.IntegrityError):self.library.save(name,Game.standard())
        self.assertEqual(len(self.library.list_positions()),1)

    def test_failed_piece_write_rolls_back_replacement(self):
        original=Game.standard();id=self.library.save('Original',original)
        with self.library._connection() as conn:
            conn.execute("CREATE TRIGGER reject_piece BEFORE INSERT ON pieces BEGIN SELECT RAISE(ABORT,'test rejection'); END")
        altered=Game.standard();altered.apply(altered.legal_moves()[0])
        with self.assertRaises(sqlite3.IntegrityError):self.library.save('Changed',altered,position_id=id)
        saved=self.library.load(id)
        self.assertEqual((saved.name,saved.game),('Original',original))

    def test_schema_constraints_and_foreign_keys(self):
        with self.library._connection() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO pieces VALUES(999,0,0,'White',0)")
        id=self.library.save('Valid',Game.standard())
        for values in [(id,1,0,'White',0),(id,8,0,'White',0),(id,0,0,'Orange',0),(id,0,0,'White',2)]:
            with self.subTest(values=values),self.library._connection() as conn:
                with self.assertRaises(sqlite3.IntegrityError):conn.execute('INSERT INTO pieces VALUES(?,?,?,?,?)',values)

    def test_invalid_state_and_missing_id_fail_without_mutation(self):
        for name,game,mode,depth in [('',Game.standard(),'Two players',3),('X',Game(),'Two players',3),
                                    ('X',Game.standard(),'Invalid',3),('X',Game.standard(),'Two players',True),
                                    ('X',Game.standard(),'Two players',5)]:
            with self.subTest(name=name,mode=mode,depth=depth),self.assertRaises(ValueError):self.library.save(name,game,mode,depth)
        with self.assertRaises(KeyError):self.library.load(42)
        with self.assertRaises(KeyError):self.library.delete(42)
        with self.assertRaises(KeyError):self.library.save('Missing',Game.standard(),position_id=42)
        self.assertEqual(self.library.list_positions(),[])

    def test_load_revalidates_tampered_cross_row_state(self):
        id=self.library.save('Corrupted',Game.standard())
        with self.library._connection() as conn:conn.execute('DELETE FROM pieces WHERE game_id=?',(id,))
        with self.assertRaises(ValueError):self.library.load(id)

    def test_unknown_schema_is_rejected(self):
        with self.library._connection() as conn:conn.execute('PRAGMA user_version=99')
        with self.assertRaises(ValueError):PositionLibrary(self.path)

    def test_load_rejects_bypassed_rank_and_continuation_constraints(self):
        id=self.library.save('Tampered',Game.standard())
        with self.library._connection() as conn:
            conn.execute('PRAGMA ignore_check_constraints=ON')
            conn.execute('UPDATE pieces SET king=2 WHERE game_id=? AND x=0 AND y=0',(id,))
        with self.assertRaises(ValueError):self.library.load(id)
        with self.library._connection() as conn:
            conn.execute('PRAGMA ignore_check_constraints=ON')
            conn.execute('UPDATE pieces SET king=0 WHERE game_id=?',(id,))
            conn.execute('UPDATE saved_games SET forced_y=2 WHERE id=?',(id,))
        with self.assertRaises(ValueError):self.library.load(id)


if __name__=='__main__':unittest.main()
