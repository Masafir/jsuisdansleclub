import { useState } from 'react';
import type { Chart } from '../chart/types';
import { KEY_BINDINGS } from '../config/gameplay';

interface HomeScreenProps {
  library: readonly Chart[];
  onPlay: (chart: Chart) => void;
}

export function HomeScreen({ library, onPlay }: HomeScreenProps) {
  const [url, setUrl] = useState('');

  return (
    <main className="screen screen--centered">
      <h1 className="title">j'suis dans le club</h1>
      <p className="subtitle">Survivrez-vous à la danse mortelle&nbsp;?</p>

      <section className="panel">
        <h2 className="panel__title">Coller un lien YouTube</h2>
        <form
          className="row"
          onSubmit={(event) => {
            event.preventDefault();
            // Branché à l'étape 2, quand le pipeline Python existera.
          }}
        >
          <input
            className="input"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <button className="button" type="submit" disabled>
            Générer
          </button>
        </form>
        <p className="hint">
          Disponible à l'étape 2, une fois le pipeline de partitions en place.
        </p>
      </section>

      <section className="panel">
        <h2 className="panel__title">Bibliothèque</h2>
        <ul className="library">
          {library.map((chart) => (
            <li key={chart.title}>
              <button className="button button--wide" onClick={() => onPlay(chart)}>
                <span>{chart.title}</span>
                <span className="library__meta">
                  {chart.bpm} BPM · {chart.notes.length} notes
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <footer className="keys">
        DON&nbsp;: {KEY_BINDINGS.DON.join(' / ').toUpperCase()} — KA&nbsp;:{' '}
        {KEY_BINDINGS.KA.join(' / ').toUpperCase()}
      </footer>
    </main>
  );
}
