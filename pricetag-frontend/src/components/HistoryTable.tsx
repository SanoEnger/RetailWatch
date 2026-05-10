import { formatConfidence, formatCurrency, formatDate, getStatusLabel, getStatusTone } from "../lib/format";
import type { HistoryItem } from "../types/api";

interface HistoryTableProps {
  items: HistoryItem[];
  isLoading: boolean;
  error: string | null;
  offset: number;
  total: number;
  onOpen: (item: HistoryItem) => void;
}

export function HistoryTable({
  items,
  isLoading,
  error,
  offset,
  total,
  onOpen,
}: HistoryTableProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">History</p>
          <h2>Последние распознавания</h2>
        </div>
        <span className="panel__tag">{total} записей</span>
      </div>

      {error && <p className="panel__error">{error}</p>}

      <div className="history-table">
        <div className="history-table__head">
          <span>ID</span>
          <span>Дата</span>
          <span>Цена</span>
          <span>Уверенность</span>
          <span>Статус</span>
        </div>

        {isLoading ? (
          <div className="history-table__state">Загружаем историю...</div>
        ) : items.length === 0 ? (
          <div className="history-table__state">Пока нет распознаваний по выбранному фильтру.</div>
        ) : (
          items.map((item, index) => (
            <button
              type="button"
              key={item.id}
              className="history-row"
              onClick={() => onOpen(item)}
            >
              <span>#{offset + index + 1}</span>
              <span>{formatDate(item.created_at)}</span>
              <span>{formatCurrency(item.extracted_price)}</span>
              <span>{formatConfidence(item.confidence)}</span>
              <span>
                <span className={`status-pill status-pill--${getStatusTone(item.is_valid)}`}>
                  {getStatusLabel(item.is_valid)}
                </span>
              </span>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
