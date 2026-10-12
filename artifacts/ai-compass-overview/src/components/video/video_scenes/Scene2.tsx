import { useState } from 'react';
import { motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { needle, EASE, SNAP } from '../needle';

const PATHS = [
  { n: '01', t: 'I have a business problem', d: 'Describe a current bottleneck or inefficient process.' },
  { n: '02', t: 'Explore my department', d: 'Start with common opportunities in a team or function.' },
  { n: '03', t: "I'm new to AI", d: 'Use your role and weekly responsibilities to find a start.' },
];

export function Scene2() {
  const [active, setActive] = useState(-1);
  const [out, setOut] = useState(false);
  useSceneTimer([
    { time: 350, callback: () => { setActive(0); needle.set(420); } },
    { time: 1950, callback: () => { setActive(1); needle.set(450); } },
    { time: 3550, callback: () => { setActive(2); needle.set(480); } },
    { time: 4700, callback: () => setOut(true) },
  ]);

  return (
    <motion.section className="absolute inset-0" exit={{ opacity: 0, transition: { duration: 0.25 } }}>
      <motion.div
        className="absolute f-mono" style={{ left: '46%', top: '12%', fontSize: '2vmin', color: 'var(--signal)' }}
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: out ? 0 : 1, y: 0 }} transition={{ duration: 0.4, ease: EASE }}
      >
        Three ways in
      </motion.div>
      <div className="absolute" style={{ left: '46%', top: '19%', width: '48%' }}>
        {PATHS.map((p, i) => {
          const shown = active >= i;
          const isActive = active === i;
          return (
            <motion.div
              key={p.n}
              style={{ borderTop: '1px solid rgba(21,34,56,0.25)', padding: '2.4vmin 0 2.6vmin', display: 'flex', gap: '3vmin' }}
              initial={{ opacity: 0, x: 60 }}
              animate={{ opacity: out ? 0 : shown ? (isActive ? 1 : 0.32) : 0, x: out ? 120 : shown ? 0 : 60 }}
              transition={out ? { duration: 0.4, delay: i * 0.06, ease: EASE } : SNAP}
            >
              <div className="f-mono" style={{ fontSize: '2.2vmin', color: isActive ? 'var(--signal)' : 'var(--ink)', paddingTop: '1.6vmin' }}>{p.n}</div>
              <div>
                <div className="f-display" style={{ fontSize: '6.4vmin', lineHeight: 1.04, fontWeight: 440 }}>{p.t}</div>
                <motion.div
                  style={{ fontSize: '3vmin', color: 'var(--ink-soft)', marginTop: '1vmin' }}
                  animate={{ opacity: isActive ? 1 : 0.6 }}
                >{p.d}</motion.div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.section>
  );
}
