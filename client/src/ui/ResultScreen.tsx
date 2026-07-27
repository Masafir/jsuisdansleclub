import type { Chart } from '../chart/types';
import type { SessionSnapshot } from '../game/session';
import { JUDGEMENTS } from '../config/gameplay';

interface ResultScreenProps {
  chart: Chart;
  snapshot: SessionSnapshot;
  onRetry: () => void;
  onAnotherSong: () => void;
}

const PERCENT = 100;

export function ResultScreen({
  chart,
  snapshot,
  onRetry,
  onAnotherSong,
}: ResultScreenProps) {
  const survived = snapshot.status === 'survived';

  return (
    <main className="screen screen--centered">
      <h1 className={`title ${survived ? '' : 'title--dead'}`}>
        {survived ? 'Vous avez survécu à la danse mortelle' : 'Game over'}
      </h1>
      <p className="subtitle">{chart.title}</p>

      <section className="panel">
        <dl className="stats">
          <div className="stats__item">
            <dt>Score</dt>
            <dd>{snapshot.score.score.toLocaleString('fr-FR')}</dd>
          </div>
          <div className="stats__item">
            <dt>Réussite</dt>
            <dd>{Math.round(snapshot.successRatio * PERCENT)}%</dd>
          </div>
          <div className="stats__item">
            <dt>Meilleur combo</dt>
            <dd>{snapshot.score.maxCombo}</dd>
          </div>
          {JUDGEMENTS.map((judgement) => (
            <div className="stats__item" key={judgement}>
              <dt>{judgement}</dt>
              <dd>{snapshot.score.counts[judgement]}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="row">
        <button className="button" onClick={onRetry}>
          Rejouer le morceau
        </button>
        <button className="button button--ghost" onClick={onAnotherSong}>
          Un autre morceau
        </button>
      </div>
    </main>
  );
}
