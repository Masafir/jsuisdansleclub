import { useCallback, useState } from 'react';
import { HomeScreen } from './HomeScreen';
import { GameScreen } from './GameScreen';
import { ResultScreen } from './ResultScreen';
import { TEST_CHART } from '../chart/testChart';
import type { Chart } from '../chart/types';
import type { SessionSnapshot } from '../game/session';

type Screen =
  | { name: 'home' }
  | { name: 'game'; chart: Chart }
  | { name: 'result'; chart: Chart; snapshot: SessionSnapshot };

export function App() {
  const [screen, setScreen] = useState<Screen>({ name: 'home' });

  const play = useCallback((chart: Chart) => {
    setScreen({ name: 'game', chart });
  }, []);

  const finish = useCallback((chart: Chart, snapshot: SessionSnapshot) => {
    setScreen({ name: 'result', chart, snapshot });
  }, []);

  const goHome = useCallback(() => setScreen({ name: 'home' }), []);

  switch (screen.name) {
    case 'home':
      return <HomeScreen library={[TEST_CHART]} onPlay={play} />;
    case 'game':
      return (
        <GameScreen
          chart={screen.chart}
          onFinished={(snapshot) => finish(screen.chart, snapshot)}
          onQuit={goHome}
        />
      );
    case 'result':
      return (
        <ResultScreen
          chart={screen.chart}
          snapshot={screen.snapshot}
          onRetry={() => play(screen.chart)}
          onAnotherSong={goHome}
        />
      );
  }
}
