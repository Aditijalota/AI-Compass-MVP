import { motion } from 'framer-motion';
import { useNeedle, EASE } from './needle';

// Persistent compass: one object carried through every cut.
// Pose per scene index: centre (% of frame), diameter (vmin), opacity, dark-field flag.
const POSES = [
  { x: 72, y: 50, d: 78, o: 1, dark: false, bezel: 0 },
  { x: 24, y: 52, d: 54, o: 1, dark: false, bezel: 40 },
  { x: 50, y: 54, d: 60, o: 1, dark: false, bezel: 90 },
  { x: 82, y: 70, d: 26, o: 1, dark: false, bezel: 150 },
  { x: 50, y: 118, d: 20, o: 0, dark: false, bezel: 200 },
  { x: 50, y: 38, d: 40, o: 1, dark: true, bezel: 270 },
];

const TICKS = Array.from({ length: 72 }, (_, i) => i);

export function Compass({ sceneIndex }: { sceneIndex: number }) {
  const angle = useNeedle();
  const p = POSES[Math.max(0, sceneIndex)] ?? POSES[0];
  const stroke = p.dark ? '#f3ede1' : '#152238';

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ zIndex: 20, left: 0, top: 0, width: '78vmin', height: '78vmin', marginLeft: '-39vmin', marginTop: '-39vmin' }}
      initial={false}
      animate={{ left: `${p.x}%`, top: `${p.y}%`, scale: p.d / 78, opacity: p.o }}
      transition={{ duration: 0.85, ease: EASE }}
    >
      <svg viewBox="0 0 200 200" width="100%" height="100%" style={{ overflow: 'visible' }}>
        <motion.g
          initial={false}
          animate={{ rotate: p.bezel }}
          transition={{ duration: 1.4, ease: EASE }}
          style={{ originX: '100px', originY: '100px' }}
        >
          <motion.circle
            cx="100" cy="100" r="96" fill="none" stroke={stroke} strokeWidth="0.8"
            initial={{ pathLength: 0 }} animate={{ pathLength: 1, stroke }} transition={{ duration: 1.2, ease: EASE }}
          />
          <circle cx="100" cy="100" r="84" fill="none" stroke={stroke} strokeWidth="0.35" opacity="0.5" />
          {TICKS.map((i) => (
            <line
              key={i}
              x1="100" y1={i % 6 === 0 ? 4 : 6.5} x2="100" y2="11"
              stroke={i % 18 === 0 ? '#e2502c' : stroke}
              strokeWidth={i % 6 === 0 ? 0.9 : 0.4}
              transform={`rotate(${i * 5} 100 100)`}
            />
          ))}
          {['N', 'E', 'S', 'W'].map((l, i) => (
            <text
              key={l} x="100" y="24" textAnchor="middle" fontSize="8" fill={stroke}
              fontFamily="Spline Sans Mono, monospace" transform={`rotate(${i * 90} 100 100)`}
            >{l}</text>
          ))}
        </motion.g>
        <motion.g
          initial={false}
          animate={{ rotate: angle }}
          transition={{ type: 'spring', stiffness: 120, damping: 14, mass: 0.9 }}
          style={{ originX: '100px', originY: '100px' }}
        >
          <polygon points="100,30 106,100 94,100" fill="#e2502c" />
          <polygon points="100,170 106,100 94,100" fill={stroke} opacity="0.9" />
        </motion.g>
        <circle cx="100" cy="100" r="4.2" fill={p.dark ? '#152238' : '#efe8da'} stroke={stroke} strokeWidth="1.2" />
      </svg>
    </motion.div>
  );
}

// Faint survey grid behind everything; drifts per scene for parallax.
export function ChartGrid({ sceneIndex }: { sceneIndex: number }) {
  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{
        inset: '-10%',
        backgroundImage:
          'linear-gradient(rgba(21,34,56,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(21,34,56,0.07) 1px, transparent 1px)',
        backgroundSize: '6vmin 6vmin',
      }}
      initial={false}
      animate={{ x: `${-sceneIndex * 1.4}%`, y: `${(sceneIndex % 2) * 1.2}%` }}
      transition={{ duration: 1.4, ease: EASE }}
    />
  );
}
