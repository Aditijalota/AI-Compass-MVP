import { useSyncExternalStore } from 'react';

// Tiny store so scenes can steer the persistent compass needle on their own beats.
let angle = 0;
const subs = new Set<() => void>();

export const needle = {
  get: () => angle,
  set: (a: number) => {
    angle = a;
    subs.forEach((f) => f());
  },
  subscribe: (f: () => void) => {
    subs.add(f);
    return () => {
      subs.delete(f);
    };
  },
};

export function useNeedle() {
  return useSyncExternalStore(needle.subscribe, needle.get, needle.get);
}

export const EASE = [0.22, 1, 0.36, 1] as const;
export const SNAP = { type: 'spring', stiffness: 260, damping: 22 } as const;
