"""Reproducible fixed-position comparison; results are not a strength tournament."""
import argparse
import csv
import platform
from pathlib import Path
from random import Random
from statistics import median
from checkers.model import Game, Piece
from checkers.ai import search


def positions():
    game=Game.standard()
    rng=Random(499)
    for _ in range(18):
        if game.winner: break
        game.apply(rng.choice(game.legal_moves()))
    return {'opening':Game.standard(),'seeded_midgame':game,
            'capture_chain':Game({(0,0):Piece('White'),(1,1):Piece('Black'),(3,3):Piece('Black')})}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='benchmarks/search_results.csv')
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    if args.repeats<1: parser.error('repeats must be positive')
    rows=[]
    for name,game in positions().items():
        for depth in (2,3,4):
            pair=[]
            for pruning in (False,True):
                runs=[search(game,depth,pruning=pruning) for _ in range(args.repeats)]
                result=runs[0]
                pair.append(result)
                rows.append(dict(position=name,depth=depth,algorithm='alpha_beta' if pruning else 'minimax',
                                 score=result.score,move=str(result.move),nodes=result.stats.nodes,
                                 leaves=result.stats.leaves,cutoffs=result.stats.cutoffs,
                                 median_seconds=round(median(r.stats.elapsed_seconds for r in runs),6),
                                 repeats=args.repeats,python=platform.python_version(),platform=platform.platform()))
            assert (pair[0].score,pair[0].move)==(pair[1].score,pair[1].move)
            print(f'{name} depth {depth}: {pair[0].stats.nodes} -> {pair[1].stats.nodes} nodes; scores/moves agree')
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(path)


if __name__=='__main__': main()
