"""Plot repeated benchmark summary; requires matplotlib only for plotting."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('experiment', type=Path)
args = p.parse_args()
rows = json.loads((args.experiment / 'summary.json').read_text())
stages = list(dict.fromkeys(r['stage'] for r in rows))
algorithms = list(dict.fromkeys(r['algorithm'] for r in rows))
out = args.experiment / 'figures'
out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
plots = [('search_time_ms', 'Search time (ms, median +/- half IQR)', 1, True),
         ('peak_memory_bytes', 'Python peak allocation (MiB, median)', 2**20, True),
         ('expanded_nodes', 'Expanded non-goal states (median)', 1, True),
         ('solution_length', 'Directional moves / cost (median)', 1, False)]
for ax, (key, title, divisor, logarithmic) in zip(axes.flat, plots):
    for algo in algorithms:
        selected = {r['stage']: r for r in rows if r['algorithm'] == algo}
        ys = [selected[s][key + '_median'] / divisor if selected[s][key + '_median'] is not None else float('nan') for s in stages]
        if key == 'search_time_ms':
            errors = [(selected[s][key + '_iqr'] or 0) / 2 for s in stages]
            ax.errorbar(range(1, len(stages) + 1), ys, yerr=errors, label=algo, linewidth=1.3, marker='.', capsize=2)
        else:
            ax.plot(range(1, len(stages) + 1), ys, label=algo, linewidth=1.3, marker='.')
    if logarithmic:
        ax.set_yscale('log')
    ax.set(title=title, xlabel='Original stage ID')
    ax.grid(alpha=.2)
    ax.legend(ncol=4, fontsize=8)
fig.suptitle('Bloxorz: 33 fixed stages, 5 runs per solver/stage; tracemalloc enabled\nA* search time includes heuristic graph construction; each solver runs in a fresh process', fontsize=13)
fig.savefig(out / 'four-solvers.png', dpi=180)
fig.savefig(out / 'four-solvers.pdf')
plt.close(fig)

astar = [r for r in rows if r['algorithm'] == 'ASTAR']
fig, ax = plt.subplots(figsize=(13, 4), constrained_layout=True)
x = range(1, len(astar) + 1)
ax.bar(x, [r['heuristic_preprocessing_time_ms_median'] for r in astar], label='Heuristic preprocessing')
ax.bar(x, [r['astar_search_time_ms_median'] for r in astar],
       bottom=[r['heuristic_preprocessing_time_ms_median'] for r in astar], label='A* heap search + reconstruction')
ax.set(xlabel='Original stage ID', ylabel='Time (ms)', title='A* cost breakdown: median of each component across 5 runs')
ax.text(.01, .98, 'Sum of component medians need not equal median total; small setup overhead is excluded here.',
        transform=ax.transAxes, va='top', fontsize=9)
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=.2)
fig.savefig(out / 'astar-breakdown.png', dpi=180)
fig.savefig(out / 'astar-breakdown.pdf')
print(out)
