import { useState, useCallback } from 'react';

export function useApi<T>(fn: (...args: never[]) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(
    async (...args: Parameters<typeof fn>) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn(...(args as never[]));
        setData(result);
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [fn],
  );

  return { data, loading, error, execute };
}
