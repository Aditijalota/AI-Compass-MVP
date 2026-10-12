import { useState } from 'react';
import { motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { EASE } from '../needle';

const ROWS = [
  { t: 'Purchase-order exceptions', d: 'Operations', p: 'Agentic candidate' },
  { t: 'HR policy lookup', d: 'HR', p: 'Knowledge assistant (RAG)' },
  { t: 'Weekly reporting', d: 'Marketing', p: 'AI-assisted automation' },
];
const QUERY = 'policy';

export function Scene5() {
  const [typed, setTyped] = useState(0);
  const [beat, setBeat] = useState(0);
  useSceneTimer([
    ...QUERY.split('').map((_, i) => ({ time: 1500 + i * 110, callback: () => setTyped(i + 1) })),
    { time: 2350, callback: () => setBeat(1) },
    { time: 3100, callback: () => setBeat(2) },
    { time: 3900, callback: () => setBeat(3) },
    { time: 4750, callback: () => setBeat(4) },
  ]);
  const out = beat === 4;

  return (
    <motion.section className="absolute inset-0" style={{ perspective: '1600px' }} exit={{ opacity: 0, transition: { duration: 0.3 } }}>
      <motion.div
        className="absolute"
        style={{ left: '8%', right: '8%', top: '10%', background: '#f6f1e7', border: '1px solid rgba(21,34,56,0.25)', boxShadow: '0 3vmin 6vmin rgba(21,34,56,0.14)', padding: '4vmin 4.5vmin', originY: '40%' }}
        initial={{ y: '70%', rotateX: 24, opacity: 0 }}
        animate={out ? { y: '-4%', scale: 1.18, opacity: 0, rotateX: 0 } : { y: '0%', rotateX: beat >= 1 ? 0 : 7, opacity: 1, scale: 1 }}
        transition={{ duration: out ? 0.6 : 0.9, ease: EASE }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <div className="f-mono" style={{ fontSize: '1.9vmin', color: 'var(--signal)' }}>Saved assessments</div>
            <div className="f-display" style={{ fontSize: '6.4vmin', lineHeight: 1.05, fontWeight: 440 }}>Opportunity Dashboard</div>
          </div>
          <div className="f-mono" style={{ fontSize: '1.9vmin', color: 'var(--ink-soft)', textAlign: 'right', lineHeight: 1.7 }}>
            3 opportunities<br />3 departments · 3 patterns
          </div>
        </div>
        <div
          className="f-mono"
          style={{ marginTop: '3vmin', border: '1px solid var(--ink)', padding: '1.4vmin 2vmin', fontSize: '2.2vmin', display: 'flex', gap: '1.6vmin', textTransform: 'none' }}
        >
          <span style={{ color: 'var(--ink-soft)' }}>Search</span>
          <span>{QUERY.slice(0, typed)}</span>
          <motion.span style={{ width: '0.25vmin', background: 'var(--signal)' }} animate={{ opacity: [1, 0, 1] }} transition={{ duration: 0.8, repeat: Infinity }} />
        </div>
        <div style={{ marginTop: '2vmin' }}>
          {ROWS.map((r, i) => {
            const match = i === 1;
            const dim = beat >= 1 && !match;
            return (
              <motion.div
                key={r.t}
                style={{ display: 'grid', gridTemplateColumns: '1.6fr 0.8fr 1.4fr 1fr', alignItems: 'center', padding: '2vmin 1.6vmin', borderTop: '1px solid rgba(21,34,56,0.18)', position: 'relative' }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: dim ? 0.22 : 1, y: 0, scale: beat >= 2 && match ? 1.025 : 1 }}
                transition={{ delay: beat === 0 ? 0.5 + i * 0.15 : 0, duration: 0.45, ease: EASE }}
              >
                <motion.div className="absolute inset-0" style={{ border: '2px solid var(--signal)' }}
                  initial={{ opacity: 0 }} animate={{ opacity: beat >= 1 && match ? 1 : 0 }} />
                <span className="f-display" style={{ fontSize: '3.4vmin' }}>{r.t}</span>
                <span style={{ fontSize: '2.6vmin', color: 'var(--ink-soft)' }}>{r.d}</span>
                <span style={{ fontSize: '2.6vmin' }}>{r.p}</span>
                <span style={{ justifySelf: 'end', position: 'relative', height: '4vmin', width: '24vmin' }}>
                  <motion.span className="f-mono absolute" style={{ right: 0, top: '0.8vmin', fontSize: '1.6vmin', color: 'var(--ink-soft)' }}
                    animate={{ opacity: beat >= 2 && match ? 0 : 1 }}>Fictional example</motion.span>
                  <motion.span className="f-mono absolute"
                    style={{ right: 0, top: 0, fontSize: '1.7vmin', background: 'var(--ink)', color: 'var(--paper)', padding: '1vmin 1.6vmin', whiteSpace: 'nowrap' }}
                    initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: beat >= 2 && match ? 1 : 0, scale: beat >= 2 && match ? 1 : 0.7 }}
                    transition={{ type: 'spring', stiffness: 320, damping: 20 }}>Reopen assessment</motion.span>
                </span>
              </motion.div>
            );
          })}
        </div>
        <motion.div
          style={{ marginTop: '2.6vmin', fontSize: '2.6vmin', color: 'var(--ink-soft)', fontStyle: 'italic' }}
          initial={{ opacity: 0 }} animate={{ opacity: beat >= 3 ? 1 : 0 }} transition={{ duration: 0.4 }}
        >
          Readiness and effort ranges are scenarios — not promised savings.
        </motion.div>
      </motion.div>
    </motion.section>
  );
}
