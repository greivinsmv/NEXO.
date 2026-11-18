#!/usr/bin/env python3
"""Plot measured replay speedup curves from two benchmark CSV files."""
import argparse
import csv
from pathlib import Path


def load(path):
    with Path(path).open(newline='', encoding='utf-8') as file:
        return list(csv.DictReader(file))


def series(rows, mode):
    key = 'ioWorkers' if mode == 'concurrent' else 'cpuWorkers'
    return sorted((int(row[key]), float(row['absoluteSpeedup']))
                  for row in rows if row['mode'] == mode)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixed', type=Path, required=True)
    parser.add_argument('--variable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--host-label', default='Entorno de medición indicado en el informe')
    args = parser.parse_args(argv)
    fixed, variable = load(args.fixed), load(args.variable)
    if not fixed or not variable:
        parser.error('Both CSV files need measurements')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    for axis, mode, title in zip(axes, ('concurrent', 'parallel'),
                                 ('Descarga con hilos', 'Emparejamiento con procesos')):
        for rows, label, color in ((fixed, 'Latencia fija', '#a7db35'),
                                   (variable, 'Latencia variable', '#56a8dd')):
            points = series(rows, mode)
            axis.plot([p[0] for p in points], [p[1] for p in points],
                      marker='o', linewidth=2.2, label=label, color=color)
        axis.axhline(1, color='#7b8176', linewidth=1, linestyle=':')
        axis.set_xscale('log', base=2)
        axis.set_xticks([p[0] for p in series(fixed, mode)])
        axis.set_xticklabels([str(p[0]) for p in series(fixed, mode)])
        axis.set_xlabel('Workers de E/S' if mode == 'concurrent' else 'Procesos de CPU')
        axis.set_ylabel('Speedup absoluto frente a secuencial')
        axis.set_title(title)
        axis.grid(alpha=.22)
        axis.legend(frameon=False)
    fig.suptitle(f'NEXO · Replay real de 500 juegos\n{args.host_label}', fontsize=12, weight='bold')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() not in ('.svg', '.png'):
        parser.error('--output must end in .svg or .png')
    fig.savefig(args.output, format=args.output.suffix.lower()[1:])
    print(f'Wrote {args.output}')


if __name__ == '__main__':
    main()
