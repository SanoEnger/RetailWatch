import { useEffect, useState } from "react";
import { fetchHistory } from "../lib/api";
import type { HistoryItem, HistoryStatus } from "../types/api";

interface UseHistoryOptions {
  limit: number;
  offset: number;
  status: HistoryStatus;
  refreshKey: number;
}

export function useHistory({
  limit,
  offset,
  status,
  refreshKey,
}: UseHistoryOptions) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchHistory({ limit, offset, status });

        if (!isActive) {
          return;
        }

        setItems(response.items);
        setTotal(response.total);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Не удалось загрузить историю распознаваний.",
        );
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      isActive = false;
    };
  }, [limit, offset, refreshKey, status]);

  return { items, total, isLoading, error };
}
