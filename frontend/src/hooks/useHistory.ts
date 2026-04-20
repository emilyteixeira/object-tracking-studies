import { useCallback, useEffect, useState } from "react";
import { TruckHistoryRecord } from "../types";

const POLL_INTERVAL_MS = 10_000; // atualiza o histórico a cada 10 segundos

export function useHistory(limit = 100) {
  const [records, setRecords] = useState<TruckHistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`/api/history?limit=${limit}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: TruckHistoryRecord[] = await res.json();
      setRecords(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar histórico");
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchHistory();
    const timer = setInterval(fetchHistory, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchHistory]);

  return { records, loading, error, refresh: fetchHistory };
}
