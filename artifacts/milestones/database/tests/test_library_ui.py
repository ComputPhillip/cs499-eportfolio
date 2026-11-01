import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from checkers.app import Application
from checkers.library_ui import LibraryDialog
from checkers.model import Game, Piece, Move


class LibraryInterfaceTests(unittest.TestCase):
    def setUp(self):
        try:self.root=tk.Tk()
        except tk.TclError as error:self.skipTest(str(error))
        self.root.withdraw()
        self.app=Application(self.root)
        self.app.opponent.set('Two players')
        self.temp=tempfile.TemporaryDirectory()
        self.dialog=LibraryDialog(self.app,Path(self.temp.name)/'test.sqlite3')
        self.dialog.window.withdraw()

    def tearDown(self):
        if hasattr(self,'app'):
            self.app.close();self.temp.cleanup()

    def select_first(self):
        id=self.dialog.tree.get_children()[0]
        self.dialog.tree.selection_set(id)
        self.dialog.select()
        return id

    def test_library_save_replace_load_restores_settings(self):
        self.dialog.name.set('Opening');self.dialog.save_new();id=self.select_first()
        changed=Game.standard();changed.apply(changed.legal_moves()[0])
        self.app.game=changed;self.app.depth.set(4)
        self.dialog.name.set('Changed')
        with patch('checkers.library_ui.messagebox.askyesno',return_value=True):self.dialog.replace()
        self.select_first()
        self.app.game=Game.standard();self.app.depth.set(1)
        self.dialog.load()
        self.assertEqual(self.app.game,changed)
        self.assertEqual(self.app.depth.get(),4)
        self.assertEqual(self.app.opponent.get(),'Two players')
        # A player may resign between jumps; finished saves must not require one.
        chain=Game({(0,0):Piece('White'),(1,1):Piece('Black'),(3,3):Piece('Black')})
        chain.apply(Move((0,0),(2,2),(1,1)))
        self.app.game=chain
        self.app.resign()
        saved_id=self.dialog.library.save('Resigned during chain',self.app.game)
        saved=self.dialog.library.load(saved_id)
        self.assertEqual(saved.game.winner,'Black')
        self.assertIsNone(saved.game.forced)

    def test_delete_cancel_preserves_then_confirm_removes(self):
        self.dialog.name.set('Keep');self.dialog.save_new();self.select_first()
        with patch('checkers.library_ui.messagebox.askyesno',return_value=False):self.dialog.delete()
        self.assertEqual(len(self.dialog.library.list_positions()),1)
        with patch('checkers.library_ui.messagebox.askyesno',return_value=True):self.dialog.delete()
        self.assertEqual(self.dialog.library.list_positions(),[])


if __name__=='__main__':unittest.main()
