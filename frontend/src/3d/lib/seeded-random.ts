const RANDOM_MODULUS = 2147483647;
const RANDOM_MULTIPLIER = 16807;

function normalizeSeed(seed: number): number {
  const normalized = Math.floor(seed) % RANDOM_MODULUS;
  return normalized > 0 ? normalized : normalized + RANDOM_MODULUS - 1;
}

export function createDeterministicRandom(seed: number): () => number {
  let state = normalizeSeed(seed);

  return () => {
    state = (state * RANDOM_MULTIPLIER) % RANDOM_MODULUS;
    return (state - 1) / (RANDOM_MODULUS - 1);
  };
}

export function randomInRange(random: () => number, min: number, max: number): number {
  return min + random() * (max - min);
}

export function randomSigned(random: () => number, magnitude: number): number {
  return (random() - 0.5) * 2 * magnitude;
}
