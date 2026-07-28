import { useState } from 'react';
import type { Chart } from '../chart/types';
import type { SessionSnapshot } from '../game/session';
import { CALIBRATION, JUDGEMENTS } from '../config/gameplay';
import { readCalibrationOffsetMs, writeCalibrationOffsetMs } from '../game/calibration';

interface ResultScreenProps {
  chart: Chart;
  snapshot: SessionSnapshot;
  onRetry: () => void;
  onAnotherSong: () => void;
}

const PERCENT = 100;

/**
 * Diagnostic de décalage systématique.
 *
 * Un joueur imprécis se trompe dans les deux sens et sa moyenne reste proche de
 * zéro. Une moyenne franchement décalée trahit autre chose : la latence de
 * sortie audio du matériel, ou des notes générées légèrement tardives. C'est
 * corrigeable d'un coup, alors qu'élargir les fenêtres ne ferait que le
 * dissimuler.
 */
function TimingAdvice({ meanDeltaMs }: { meanDeltaMs: number | null }) {
  const [applied, setApplied] = useState<number | null>(null);

  if (meanDeltaMs === null) return null;

  const rounded = Math.round(meanDeltaMs);
  const isLate = rounded > 0;
  const matters = Math.abs(rounded) >= CALIBRATION.SUGGEST_THRESHOLD_MS;

  return (
    <section className="panel">
      <h2 className="panel__title">Timing</h2>
      <p className="timing">
        Tu frappes en moyenne{' '}
        <strong>
          {Math.abs(rounded)} ms {isLate ? 'en retard' : 'en avance'}
        </strong>
        .
      </p>

      {!matters && (
        <p className="hint">
          C'est négligeable : ton décalage vient de toi, pas de ton matériel.
        </p>
      )}

      {matters && applied === null && (
        <>
          <p className="hint">
            Assez régulier pour venir de ta latence audio plutôt que de ton jeu.
            La corriger décalera les fenêtres de jugement d'autant.
          </p>
          <button
            className="button"
            onClick={() =>
              setApplied(writeCalibrationOffsetMs(readCalibrationOffsetMs() + rounded))
            }
          >
            Corriger ce décalage
          </button>
        </>
      )}

      {applied !== null && (
        <p className="hint">
          Décalage enregistré ({applied > 0 ? '+' : ''}
          {applied} ms). Il s'appliquera dès la prochaine partie.
        </p>
      )}
    </section>
  );
}

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

      <TimingAdvice meanDeltaMs={snapshot.meanDeltaMs} />

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
