import { useState } from 'react';
import { motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { needle, EASE } from '../needle';

export function Scene6() {
  const [beat, setBeat] = useState(0);
  useSceneTimer([
    { time: 300, callback: () => needle.set(1440) },
    { time: 1100, callback: () => setBeat(1) },
    { time: 1700, callback: () => setBeat(2) },
    { time: 3300, callback: () => setBeat(3) },
  ]);
  const out = beat === 3;

  return (
    <motion.section className="absolute inset-0" exit={{ opacity: 0, transition: { duration: 0.3 } }}>
      <motion.div
        className="absolute inset-0" style={{ background: 'var(--ink)' }}
        initial={{ clipPath: 'circle(0% at 50% 38%)' }}
        animate={{ clipPath: 'circle(120% at 50% 38%)', opacity: out ? 0 : 1 }}
        transition={{ clipPath: { duration: 0.7, ease: EASE }, opacity: { duration: 0.6 } }}
      />
      <div className="absolute" style={{ left: 0, right: 0, top: '62%', textAlign: 'center', color: 'var(--paper)' }}>
        <span className="mask">
          <motion.div className="f-display" style={{ fontSize: '11vmin', lineHeight: 1, fontWeight: 460 }}
            initial={{ y: '110%' }} animate={{ y: out ? '-110%' : '0%' }} transition={{ delay: out ? 0 : 0.45, duration: 0.7, ease: EASE }}>
            AI <em style={{ fontWeight: 340 }}>Compass</em>
          </motion.div>
        </span>
        <motion.div style={{ fontSize: '3.4vmin', marginTop: '2.4vmin' }}
          initial={{ opacity: 0, y: 14 }} animate={{ opacity: beat >= 1 && !out ? 1 : 0, y: beat >= 1 ? 0 : 14 }} transition={{ duration: 0.5, ease: EASE }}>
          Find the fit before you build.
        </motion.div>
        <motion.div className="f-mono" style={{ fontSize: '2vmin', marginTop: '2vmin', color: 'var(--glass)' }}
          initial={{ opacity: 0 }} animate={{ opacity: beat >= 2 && !out ? 1 : 0 }} transition={{ duration: 0.5 }}>
          Discovery &amp; assessment · humans decide
        </motion.div>
      </div>
    </motion.section>
  );
}
