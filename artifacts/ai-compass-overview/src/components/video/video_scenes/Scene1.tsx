import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { needle, EASE } from '../needle';

const LINES = [
  <>Discover where AI</>,
  <>can create <em style={{ color: 'var(--signal)', fontStyle: 'italic' }}>value</em></>,
  <>in your business.</>,
];

export function Scene1() {
  const [beat, setBeat] = useState(0);
  const [bearing, setBearing] = useState('000° N');
  useEffect(() => { needle.set(0); }, []);
  useSceneTimer([
    { time: 80, callback: () => { needle.set(405); setBearing('045° NE'); } },
    { time: 2200, callback: () => setBeat(1) },
    { time: 3000, callback: () => { needle.set(380); setBearing('020° NNE'); } },
    { time: 3900, callback: () => setBeat(2) },
  ]);
  const out = beat === 2;

  return (
    <motion.section className="absolute inset-0" exit={{ opacity: 0, transition: { duration: 0.3 } }}>
      <div className="absolute" style={{ left: '7%', top: '50%', transform: 'translateY(-54%)', width: '52%' }}>
        <motion.div
          className="f-mono" style={{ fontSize: '2vmin', color: 'var(--ink-soft)', marginBottom: '3vmin' }}
          initial={{ opacity: 0, x: -20 }} animate={{ opacity: out ? 0 : 1, x: 0 }} transition={{ delay: out ? 0 : 0.2, duration: 0.5, ease: EASE }}
        >
          AI Compass · Opportunity discovery
        </motion.div>
        {LINES.map((l, i) => (
          <span key={i} className="mask">
            <motion.span
              className="f-display block"
              style={{ fontSize: '9.4vmin', lineHeight: 1.02, fontWeight: 420 }}
              initial={{ y: '108%' }}
              animate={{ y: out ? '-110%' : '0%' }}
              transition={{ delay: out ? i * 0.07 : 0.45 + i * 0.5, duration: out ? 0.45 : 0.75, ease: EASE }}
            >
              {l}
            </motion.span>
          </span>
        ))}
        <svg width="40vmin" height="3vmin" viewBox="0 0 400 30" style={{ marginLeft: '24vmin', overflow: 'visible' }}>
          <motion.path
            d="M4 18 C 90 6, 220 28, 396 12" fill="none" stroke="var(--signal)" strokeWidth="5" strokeLinecap="round"
            initial={{ pathLength: 0 }} animate={{ pathLength: beat >= 1 && !out ? 1 : 0, opacity: out ? 0 : 1 }}
            transition={{ duration: 0.6, ease: EASE }}
          />
        </svg>
      </div>
      <motion.div
        className="absolute f-mono" style={{ left: '7%', bottom: '8%', fontSize: '1.9vmin', color: 'var(--ink-soft)' }}
        initial={{ opacity: 0 }} animate={{ opacity: out ? 0 : 1 }} transition={{ delay: 0.6, duration: 0.4 }}
      >
        Bearing · <span style={{ color: 'var(--signal)' }}>{bearing}</span>
      </motion.div>
    </motion.section>
  );
}
