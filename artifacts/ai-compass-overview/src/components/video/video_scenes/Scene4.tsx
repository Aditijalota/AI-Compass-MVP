import { useState } from 'react';
import { motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { needle, EASE } from '../needle';

const PATTERNS = [
  'Process improvement',
  'Existing AI tool',
  'AI-assisted automation',
  'Knowledge assistant (RAG)',
  'Agentic candidate',
];
const PICK = 3;
const SCAN = [0, 1, 2, 3, 4, 3];

export function Scene4() {
  const [scan, setScan] = useState(-1);
  const [beat, setBeat] = useState(0);
  useSceneTimer([
    ...SCAN.map((row, i) => ({ time: 200 + i * 230, callback: () => setScan(row) })),
    { time: 1700, callback: () => setBeat(1) },
    { time: 2400, callback: () => setBeat(2) },
    { time: 3150, callback: () => { setBeat(3); needle.set(1080); } },
    { time: 3750, callback: () => setBeat(4) },
    { time: 4400, callback: () => setBeat(5) },
  ]);
  const out = beat === 5;

  return (
    <motion.section className="absolute inset-0" exit={{ opacity: 0, transition: { duration: 0.2 } }}>
      <motion.div
        className="absolute" style={{ left: '6%', top: '12%', width: '42%' }}
        animate={{ opacity: out ? 0 : 1, y: out ? -30 : 0 }} transition={{ duration: 0.4, ease: EASE }}
      >
        <div className="f-mono" style={{ fontSize: '2vmin', color: 'var(--signal)' }}>Transparent Python rules</div>
        <div className="f-display" style={{ fontSize: '7.6vmin', lineHeight: 1, fontWeight: 430, margin: '1.2vmin 0 4vmin' }}>Solution fit</div>
        {PATTERNS.map((p, i) => {
          const picked = beat >= 1 && i === PICK;
          const lit = scan === i;
          return (
            <motion.div
              key={p}
              style={{ position: 'relative', fontSize: '3.6vmin', padding: '1.5vmin 2vmin', borderTop: '1px solid rgba(21,34,56,0.2)' }}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: beat >= 1 && !picked ? 0.35 : 1, x: 0 }}
              transition={{ delay: beat >= 1 ? 0 : i * 0.05, duration: 0.35, ease: EASE }}
            >
              <motion.div
                className="absolute inset-0"
                style={{ background: picked ? 'var(--ink)' : 'rgba(226,80,44,0.16)', originX: 0 }}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: lit || picked ? 1 : 0 }}
                transition={{ duration: 0.2 }}
              />
              <span style={{ position: 'relative', color: picked ? 'var(--paper)' : 'var(--ink)' }}>{p}</span>
            </motion.div>
          );
        })}
      </motion.div>

      <motion.div
        className="absolute" style={{ left: '55%', top: '16%', width: '40%' }}
        animate={{ opacity: out ? 0 : 1 }} transition={{ duration: 0.35 }}
      >
        <motion.div className="f-mono" style={{ fontSize: '2vmin', color: 'var(--ink-soft)' }}
          initial={{ opacity: 0 }} animate={{ opacity: beat >= 1 ? 1 : 0 }}>Recommended pattern</motion.div>
        <span className="mask">
          <motion.div className="f-display" style={{ fontSize: '7vmin', lineHeight: 1.04, fontWeight: 460 }}
            initial={{ y: '110%' }} animate={{ y: beat >= 1 ? '0%' : '110%' }} transition={{ duration: 0.6, ease: EASE }}>
            Knowledge assistant
          </motion.div>
        </span>
        <motion.div
          className="f-display" style={{ fontSize: '4.4vmin', fontStyle: 'italic', color: 'var(--signal)', marginTop: '3.4vmin' }}
          initial={{ opacity: 0, y: 14 }} animate={{ opacity: beat >= 2 ? 1 : 0, y: beat >= 2 ? 0 : 14 }} transition={{ duration: 0.45, ease: EASE }}
        >
          AI explains. Rules decide.
        </motion.div>
        <motion.div
          style={{ fontSize: '3vmin', color: 'var(--ink-soft)', marginTop: '14vmin', width: '50%', lineHeight: 1.3 }}
          initial={{ opacity: 0 }} animate={{ opacity: beat >= 4 ? 1 : 0 }} transition={{ duration: 0.4 }}
        >
          Preliminary. Validate with process owners.
        </motion.div>
      </motion.div>

      {/* Review seal ring around the persistent compass (82% / 70%, 26vmin) */}
      <motion.svg
        className="absolute" viewBox="0 0 200 200"
        style={{ left: '82%', top: '70%', width: '40vmin', height: '40vmin', marginLeft: '-20vmin', marginTop: '-20vmin', overflow: 'visible' }}
        initial={{ opacity: 0, scale: 1.5, rotate: -30 }}
        animate={beat >= 3 && !out ? { opacity: 1, scale: 1, rotate: 0 } : { opacity: 0, scale: beat >= 3 ? 0.8 : 1.5, rotate: -30 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        <defs>
          <path id="seal" d="M100,100 m-88,0 a88,88 0 1,1 176,0 a88,88 0 1,1 -176,0" />
        </defs>
        <circle cx="100" cy="100" r="97" fill="none" stroke="var(--signal)" strokeWidth="2.5" />
        <text fontSize="13" fill="var(--signal)" fontFamily="Spline Sans Mono, monospace" letterSpacing="3.2">
          <textPath href="#seal">HUMAN REVIEW REQUIRED · HUMAN REVIEW REQUIRED · </textPath>
        </text>
      </motion.svg>
    </motion.section>
  );
}
