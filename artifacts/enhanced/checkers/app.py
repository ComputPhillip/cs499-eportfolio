"""Event-driven controller; UI creation happens only inside main()."""
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .model import Game, Piece
from .view import BoardView
from .ai import choose_move
from . import storage


class Application:
    def __init__(self, root):
        self.root = root
        root.title('Checkers | Graphics and Software Design')
        root.geometry('960x760')
        root.minsize(720,560)
        self.game = Game.standard()
        self.selected = None
        self.busy = False
        self.editing = False
        self.generation = 0
        self.status = tk.StringVar()
        self.opponent = tk.StringVar(value='Computer Black')
        self.place = tk.StringVar(value='White Pawn')
        self.setup_turn = tk.StringVar(value='White')
        header = ttk.Frame(root, padding=(18,14))
        header.pack(fill='x')
        ttk.Label(header, text='CHECKERS', font=('Segoe UI',20,'bold')).pack(side='left')
        ttk.Label(header, text='Select a piece, then a highlighted destination.').pack(side='right')
        toolbar = ttk.Frame(root, padding=(18,0,18,10))
        toolbar.pack(fill='x')
        for label, command in [('New game', self.new_game),('Custom setup', self.custom),
                               ('Start position', self.start),('Load', self.load),('Save', self.save),('Resign', self.resign)]:
            ttk.Button(toolbar,text=label,command=command).pack(side='left',padx=(0,6))
        settings = ttk.Frame(root,padding=(18,0,18,8))
        settings.pack(fill='x')
        choice=ttk.Combobox(settings,textvariable=self.opponent,state='readonly',width=19,
                            values=('Two players','Computer Black','Computer White'))
        choice.pack(side='left',padx=(0,14))
        choice.bind('<<ComboboxSelected>>',lambda event:self.schedule_ai())
        ttk.Label(settings,text='Setup brush:').pack(side='left')
        ttk.Combobox(settings,textvariable=self.place,state='readonly',width=13,
                      values=('White Pawn','White King','Black Pawn','Black King','Erase')).pack(side='left',padx=5)
        ttk.Label(settings,text='First turn:').pack(side='left',padx=(10,0))
        ttk.Combobox(settings,textvariable=self.setup_turn,state='readonly',width=7,
                     values=('White','Black')).pack(side='left',padx=5)
        self.view=BoardView(root,self.click)
        self.view.pack(fill='both',expand=True,padx=18)
        ttk.Label(root,textvariable=self.status,padding=16,font=('Segoe UI',11)).pack(fill='x')
        self.refresh()

    def reset(self, game, editing=False):
        self.generation += 1
        self.game,self.editing,self.busy,self.selected=game,editing,False,None
        self.refresh()
        self.schedule_ai()

    def refresh(self):
        moves=[m for m in self.game.legal_moves() if m.start==self.selected] if not self.editing else []
        self.view.render(self.game,self.selected,moves)
        if self.editing:
            text='Setup: choose a brush and click a dark square. Press Start position when ready.'
        elif self.game.winner:
            text=f'{self.game.winner} wins. Start a new game or load a position.'
        else:
            white=sum(p.color=='White' for p in self.game.board.values())
            text=f'{self.game.turn} to move  |  White {white} · Black {len(self.game.board)-white}'
            if self.game.forced is not None:
                text += '  |  Continue the capture with the same piece.'
        self.status.set(text)

    def new_game(self):
        self.reset(Game.standard())

    def custom(self):
        self.reset(Game(),editing=True)

    def start(self):
        if not self.editing:
            return
        if not self.game.board:
            messagebox.showinfo('Empty position','Place at least one piece before starting.')
            return
        self.game.turn=self.setup_turn.get()
        self.game.resolve_terminal()
        self.reset(self.game)

    def is_computer(self):
        return self.opponent.get() == 'Computer '+self.game.turn

    def click(self,square):
        if square is None or self.busy:
            return
        if self.editing:
            if sum(square)%2:
                self.status.set('Pieces belong on dark squares.')
                return
            brush=self.place.get()
            if brush=='Erase':
                self.game.board.pop(square,None)
            else:
                color,rank=brush.split()
                count=sum(p.color==color for sq,p in self.game.board.items() if sq!=square)
                if count>=12:
                    self.status.set('Each player can have at most 12 pieces.')
                    return
                king=rank=='King' or square[1]==(7 if color=='White' else 0)
                self.game.board[square]=Piece(color,king)
            self.refresh()
            return
        if self.game.winner or self.is_computer():
            return
        legal=self.game.legal_moves()
        move=next((m for m in legal if m.start==self.selected and m.end==square),None)
        if move:
            self.animate(move)
        else:
            self.selected=square if any(m.start==square for m in legal) else None
            self.refresh()

    def animate(self,move):
        self.busy=True
        self.selected=move.start
        self.refresh()
        generation=self.generation
        started=time.monotonic()
        def frame():
            if generation!=self.generation:
                return
            fraction=min(1,(time.monotonic()-started)/.24)
            smooth=fraction*fraction*(3-2*fraction)
            a,b=self.view.center(move.start),self.view.center(move.end)
            self.view.position_piece(move.start,(a[0]+(b[0]-a[0])*smooth,a[1]+(b[1]-a[1])*smooth))
            if fraction<1:
                self.root.after(16,frame)
            else:
                self.game.apply(move)
                self.busy=False
                self.selected=self.game.forced
                self.refresh()
                self.schedule_ai()
        frame()

    def schedule_ai(self):
        if self.editing or self.busy or self.game.winner or not self.is_computer():
            return
        generation=self.generation
        def play():
            if generation!=self.generation or self.busy or self.editing or self.game.winner or not self.is_computer():
                return
            move=choose_move(self.game)
            if move is None:
                self.game.resolve_terminal()
                self.refresh()
            else:
                self.animate(move)
        self.root.after(350,play)

    def load(self):
        path=filedialog.askopenfilename(filetypes=[('Checkers saves','*.json *.txt')])
        if path:
            try:
                game=storage.load(path)
            except (OSError,ValueError,TypeError) as error:
                messagebox.showerror('Unable to load',str(error))
                return
            self.reset(game)

    def save(self):
        if self.busy:
            self.status.set('Wait for the current move to finish before saving.')
            return
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Checkers save','*.json')])
        if path:
            try:
                # Setup turn is a UI choice until Start position is pressed.
                game=Game(dict(self.game.board),self.setup_turn.get()) if self.editing else self.game
                storage.save(game,path)
                self.status.set('Game saved.')
            except (OSError,ValueError) as error:
                messagebox.showerror('Unable to save',str(error))

    def resign(self):
        if not self.editing and not self.game.winner and not self.busy:
            self.generation+=1
            self.game.winner='Black' if self.game.turn=='White' else 'White'
            self.refresh()


def main():
    root=tk.Tk()
    Application(root)
    root.mainloop()


if __name__=='__main__':
    main()
