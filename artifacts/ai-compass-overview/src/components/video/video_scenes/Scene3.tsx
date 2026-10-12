import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useSceneTimer } from '@/lib/video';
import { needle, EASE } from '../needle';

const QUESTIONS = [
  'What triggers this work each week?',
  'Which tools hold the data today?',
  'Where do exceptions need human judgment?',
  'How often does it happen, and for how long?',
  'Which rules must never bend?',
  'Who reviews the result before it is used?',
];

// Six arc segments around the persistent compass (centre 50%/54%, 60vmin).
function arc(i: number) {
  const r = 112;
  const a0 = ((i * 60 + 4 - 90) * Math.PI) / 180;
  const a1 = ((i * 60 + 56 - 90) * Math.PI) / 180;
  return `M ${120 + r * Math.cos(a0)} ${120 + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${120 + r * Math.cos(a1)} ${120 + r * Math.sin(a1)}`;
}

export function Scene3() {
  const [step, setStep] = useState(-1);
  const [out, setOut] = useState(false);
  useSceneTimer([
    ...QUESTIONS.map((_, i) => ({
      time: 250 + i * 780,
      callback: () => { setStep(i); needle.set(510 + i * 60); },
    })),
    { time: 4850, callback: () => setOut(true) },
  ]);

  return (
    <motion.section className="absolute inset-0" exit={{ opacity: 0, transition: { duration: 0.25 } }}>
      <motion.div
        className="absolute" style={{ left: '6%', top: '9%' }}
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: out ? 0 : 1, y: out ? -20 : 0 }} transition={{ duration: 0.5, ease: EASE }}
      >
        <div className="f-mono" style={{ fontSize: '2vmin', color: 'var(--signal)', marginBottom: '1.4vmin' }}>Discovery Studio</div>
        <div className="f-display" style={{ fontSize: '8.6vmin', lineHeight: 1, fontWeight: 430 }}>
          Six <em>exchanges.</em>
        </div>
      </motion.div>
      <motion.div
        className="absolute" style={{ left: '6%', bottom: '10%', width: '28%', fontSize: '3vmin', lineHeight: 1.3, color: 'var(--ink-soft)' }}
        initial={{ opacity: 0 }} animate={{ opacity: out ? 0 : 1 }} transition={{ delay: 0.9, duration: 0.5 }}
      >
        Each follow-up builds on your earlier answers.
      </motion.div>

      <svg
        className="absolute" viewBox="0 0 240 240"
        style={{ left: '50%', top: '54%', width: '72vmin', height: '72vmin', marginLeft: '-36vmin', marginTop: '-36vmin', overflow: 'visible' }}
      >
        {QUESTIONS.map((_, i) => (
          <g key={i}>
            <path d={arc(i)} fill="none" stroke="rgba(21,34,56,0.15)" strokeWidth="5" strokeLinecap="round" />
            <motion.path
              d={arc(i)} fill="none" stroke={i === step ? 'var(--signal)' : 'var(--ink)'} strokeWidth="5" strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: step >= i && !out ? 1 : 0 }}
              transition={{ duration: out ? 0.3 : 0.5, ease: EASE }}
            />
          </g>
        ))}
      </svg>

      <motion.div
        className="absolute" style={{ left: '69.5%', top: '30%', width: '25%' }}
        initial={{ opacity: 0, x: 40 }} animate={{ opacity: out ? 0 : 1, x: out ? 60 : 0 }} transition={{ duration: 0.5, ease: EASE }}
      >
        <div
          className="f-mono"
          style={{ fontSize: '1.7vmin', lineHeight: 1.5, color: 'var(--paper)', background: 'var(--ink)', padding: '0.8vmin 1.4vmin', display: 'inline-block', letterSpacing: '0.06em' }}
        >
          AI-selected follow-up · OpenAI
        </div>
        <div className="f-mono" style={{ fontSize: '2vmin', marginTop: '2.4vmin', color: 'var(--ink-soft)' }}>
          Exchange <span style={{ color: 'var(--signal)' }}>{Math.max(1, step + 1)}</span> of 6
        </div>
        <div style={{ position: 'relative', height: '26vmin', marginTop: '1.6vmin' }}>
          <AnimatePresence mode="popLayout">
            {step >= 0 && (
              <motion.div
                key={step}
                className="f-display absolute"
                style={{ fontSize: '5vmin', lineHeight: 1.1, fontWeight: 400, top: 0, left: 0, right: 0 }}
                initial={{ opacity: 0, y: '40%', filter: 'blur(6px)' }}
                animate={{ opacity: 1, y: '0%', filter: 'blur(0px)' }}
                exit={{ opacity: 0, y: '-30%', filter: 'blur(6px)', transition: { duration: 0.22 } }}
                transition={{ duration: 0.4, ease: EASE }}
              >
                {QUESTIONS[step]}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="f-mono" style={{ fontSize: '1.7vmin', color: 'var(--ink-soft)', borderTop: '1px solid rgba(21,34,56,0.25)', paddingTop: '1.4vmin' }}>
          Chosen from a reviewed question set
        </div>
      </motion.div>
    </motion.section>
  );
}
