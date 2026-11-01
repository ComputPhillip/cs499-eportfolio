"""Modal named-position library. SQLite access stays on the Tk main thread."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .database import PositionLibrary


class LibraryDialog:
    def __init__(self, app, path):
        self.app = app
        self.library = PositionLibrary(path)
        self.window = tk.Toplevel(app.root)
        self.window.title('Saved positions')
        self.window.geometry('700x440')
        self.window.minsize(620,380)
        self.window.transient(app.root)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.grab_set()
        frame = ttk.Frame(self.window,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Save and revisit positions',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Includes player mode, search depth, and the game result.').pack(anchor='w',pady=(4,12))
        self.tree = ttk.Treeview(frame,columns=('pieces','turn','updated'),show='tree headings',height=8)
        self.tree.heading('#0',text='Name'); self.tree.column('#0',width=240,minwidth=140)
        for key,label,width in [('pieces','Pieces',55),('turn','Turn',70),('updated','Saved UTC',160)]:
            self.tree.heading(key,text=label); self.tree.column(key,width=width,minwidth=width)
        self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.select)
        entryrow = ttk.Frame(frame); entryrow.pack(fill='x',pady=10)
        ttk.Label(entryrow,text='Name:').pack(side='left')
        self.name = tk.StringVar()
        ttk.Entry(entryrow,textvariable=self.name).pack(side='left',fill='x',expand=True,padx=(8,0))
        buttons = ttk.Frame(frame); buttons.pack(fill='x')
        for label,method in [('Save new',self.save_new),('Replace selected',self.replace),
                             ('Load selected',self.load),('Delete selected',self.delete),('Close',self.close)]:
            ttk.Button(buttons,text=label,command=method).pack(side='left',padx=(0,6))
        self.reload()

    def reload(self):
        for child in self.tree.get_children():self.tree.delete(child)
        for row in self.library.list_positions():
            self.tree.insert('', 'end',iid=str(row['id']),text=row['name'],
                             values=(row['piece_count'],row['turn'],row['updated_at']))

    def selected_id(self):
        ids=self.tree.selection()
        if not ids:raise ValueError('Select a saved position first.')
        return int(ids[0])

    def select(self,event=None):
        if self.tree.selection():self.name.set(self.tree.item(self.tree.selection()[0],'text'))

    def guarded(self,action):
        try:action()
        except (OSError,sqlite3.Error,ValueError,KeyError) as error:
            messagebox.showerror('Position library',str(error),parent=self.window)

    def save_new(self):
        def action():
            self.library.save(self.name.get(),self.app.game,self.app.opponent.get(),self.app.depth.get())
            self.reload()
        self.guarded(action)

    def replace(self):
        def action():
            position_id=self.selected_id()
            if messagebox.askyesno('Replace saved position','Replace the selected save with the current board?',parent=self.window):
                self.library.save(self.name.get(),self.app.game,self.app.opponent.get(),self.app.depth.get(),position_id)
                self.reload()
        self.guarded(action)

    def load(self):
        def action():
            position=self.library.load(self.selected_id())
            self.app.opponent.set(position.opponent);self.app.depth.set(position.depth)
            self.window.grab_release();self.window.destroy()
            self.app.reset(position.game)
        self.guarded(action)

    def delete(self):
        def action():
            position_id=self.selected_id()
            if messagebox.askyesno('Delete saved position','Delete the selected position from this library?',parent=self.window):
                self.library.delete(position_id);self.reload();self.name.set('')
        self.guarded(action)

    def close(self):
        self.window.grab_release();self.window.destroy()
        self.app.schedule_ai()
