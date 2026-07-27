import type { SessionSnapshot } from '../game/session';

interface HudProps {
  snapshot: SessionSnapshot;
  survivalThreshold: number;
  title: string;
}

const PERCENT = 100;

export function Hud({ snapshot, survivalThreshold, title }: HudProps) {
  const ratioPercent = Math.round(snapshot.successRatio * PERCENT);
  const inDanger = snapshot.successRatio < survivalThreshold;

  return (
    <div className="hud">
      <div className="hud__row">
        <span className="hud__label">{title}</span>
        <span className="hud__score">{snapshot.score.score.toLocaleString('fr-FR')}</span>
      </div>

      <div className="hud__row">
        <span className={`hud__combo ${snapshot.score.combo > 0 ? 'is-active' : ''}`}>
          {snapshot.score.combo} combo
        </span>
        <span className={`hud__ratio ${inDanger ? 'is-danger' : ''}`}>
          {ratioPercent}%
        </span>
      </div>

      <div className="gauge">
        <div
          className="gauge__marker"
          style={{ left: `${survivalThreshold * PERCENT}%` }}
        />
        <div
          className={`gauge__fill ${inDanger ? 'is-danger' : ''}`}
          style={{ width: `${ratioPercent}%` }}
        />
      </div>

      {snapshot.lastJudgement && (
        <div className={`judgement judgement--${snapshot.lastJudgement.toLowerCase()}`}>
          {snapshot.lastJudgement}
        </div>
      )}
    </div>
  );
}
