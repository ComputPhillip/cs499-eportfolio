"""Canvas renderer: owns drawing objects and coordinate conversion."""
import tkinter as tk


class BoardView(tk.Canvas):
    def __init__(self, parent, on_square):
        super().__init__(parent, background='#16202b', highlightthickness=0, width=640, height=640)
        self.squares = [self.create_rectangle(0, 0, 0, 0, outline='') for _ in range(64)]
        self.pieces = {}
        self.overlays = []
        self.snapshot = None
        self.selected = None
        self.moves = []
        self.bind('<Button-1>', lambda event: on_square(self.square_at(event.x, event.y)))
        self.bind('<Configure>', self.resize)

    def geometry(self):
        side = max(8, min(self.winfo_width(), self.winfo_height()) - 32)
        return (self.winfo_width() - side) / 2, (self.winfo_height() - side) / 2, side / 8

    def center(self, square):
        left, top, size = self.geometry()
        x, y = square
        return left + (x + .5) * size, top + (7 - y + .5) * size

    def square_at(self, px, py):
        left, top, size = self.geometry()
        x, row = int((px-left)//size), int((py-top)//size)
        return (x, 7-row) if 0 <= x < 8 and 0 <= row < 8 else None

    def resize(self, event=None):
        left, top, size = self.geometry()
        for y in range(8):
            for x in range(8):
                item = self.squares[y*8+x]
                px, py = left+x*size, top+(7-y)*size
                self.coords(item, px, py, px+size, py+size)
                self.itemconfigure(item, fill='#374c58' if (x+y)%2 == 0 else '#d9e1df')
        if self.snapshot is not None:
            self.render(self.snapshot, self.selected, self.moves)

    def position_piece(self, square, center):
        oval, label = self.pieces[square]
        x, y = center
        radius = self.geometry()[2] * .36
        self.coords(oval, x-radius, y-radius, x+radius, y+radius)
        self.coords(label, x, y)

    def render(self, game, selected=None, moves=()):
        self.snapshot, self.selected, self.moves = game, selected, list(moves)
        for square in list(self.pieces):
            if square not in game.board:
                for item in self.pieces.pop(square):
                    self.delete(item)
        for square, piece in game.board.items():
            if square not in self.pieces:
                self.pieces[square] = (self.create_oval(0,0,0,0,width=3), self.create_text(0,0))
            oval, label = self.pieces[square]
            self.position_piece(square, self.center(square))
            self.itemconfigure(oval, fill='#f4f2e9' if piece.color=='White' else '#17232b',
                               outline='#f5bd4f' if square==selected else '#91a5ad')
            self.itemconfigure(label, text='K' if piece.king else '',
                               fill='#17232b' if piece.color=='White' else '#f4f2e9',
                               font=('Segoe UI', max(10,int(self.geometry()[2]*.26)), 'bold'))
            self.tag_raise(oval)
            self.tag_raise(label)
        for item in self.overlays:
            self.delete(item)
        self.overlays = []
        for move in moves:
            x,y = self.center(move.end)
            radius = self.geometry()[2]*.12
            self.overlays.append(self.create_oval(x-radius,y-radius,x+radius,y+radius,fill='#f5bd4f',outline=''))
