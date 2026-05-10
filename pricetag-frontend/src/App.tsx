import { useMemo, useState } from "react";
import { HistoryTable } from "./components/HistoryTable";
import { RecognitionModal } from "./components/RecognitionModal";
import { StatCard } from "./components/StatCard";
import { UploadPanel } from "./components/UploadPanel";
import { formatCurrency } from "./lib/format";
import { useHistory } from "./hooks/useHistory";
import type { HistoryItem, HistoryStatus } from "./types/api";

const PAGE_SIZE = 20;

export default function App() {
  const [status, setStatus] = useState<HistoryStatus>("all");
  const [offset, setOffset] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const { items, total, isLoading, error } = useHistory({
    limit: PAGE_SIZE,
    offset,
    status,
    refreshKey,
  });

  const stats = useMemo(() => {
    const okCount = items.filter((item) => item.is_valid === true).length;
    const errorCount = items.filter((item) => item.is_valid === false).length;
    const pendingCount = items.filter((item) => item.is_valid == null).length;
    const confidenceItems = items.filter((item) => item.confidence != null);
    const avgConfidence =
      confidenceItems.length > 0
        ? confidenceItems.reduce(
            (sum, item) => sum + (item.confidence ?? 0),
            0,
          ) / confidenceItems.length
        : 0;

    const topPrice = items.reduce<number | null>((currentMax, item) => {
      if (item.extracted_price == null) {
        return currentMax;
      }

      if (currentMax == null || item.extracted_price > currentMax) {
        return item.extracted_price;
      }

      return currentMax;
    }, null);

    return {
      okCount,
      errorCount,
      pendingCount,
      topPrice,
      avgConfidence,
    };
  }, [items]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  function refreshHistory() {
    setRefreshKey((value) => value + 1);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__mark">RW</div>
          <div>
            <p>RetailWatch</p>
            <span>Dashboard</span>
          </div>
        </div>

        <nav className="sidebar__nav">
          <a href="#overview">Обзор</a>
          <a href="#manual-test">Ручной тест</a>
          <a href="#history">История</a>
        </nav>
      </aside>

      <main className="content">
        <section id="overview" className="hero">
          <div className="hero__copy">
            <p className="hero__eyebrow">RetailWatch</p>
            <h1>Контроль качества распознавания ценников</h1>
            <p className="hero__text">
              Загружайте изображения, проверяйте OCR-результат и быстро
              размечайте ошибки в одном рабочем интерфейсе.
            </p>
            <div className="hero__highlights">
              <span>Быстрый тест фото</span>
              <span>История распознаваний</span>
              <span>Операторская валидация</span>
            </div>
          </div>

          <div className="stats-grid">
            <StatCard
              eyebrow="Подтверждено"
              value={String(stats.okCount)}
              caption="результатов отмечены как корректные"
            />
            <StatCard
              eyebrow="Ошибки"
              value={String(stats.errorCount)}
              caption="записей требуют исправления"
            />
            <StatCard
              eyebrow="На проверке"
              value={String(stats.pendingCount)}
              caption="результатов без ручной валидации"
            />
            <StatCard
              eyebrow="Средняя уверенность"
              value={`${Math.round(stats.avgConfidence * 100)}%`}
              caption="по текущему списку истории"
            />
          </div>
        </section>

        <section className="overview-strip">
          <article className="overview-note">
            <p className="overview-note__label">Шаг 1</p>
            <strong>Загрузите фото</strong>
            <span>Проверьте цену сразу после распознавания.</span>
          </article>
          <article className="overview-note">
            <p className="overview-note__label">Шаг 2</p>
            <strong>Откройте историю</strong>
            <span>Просмотрите спорные записи и сырой OCR-текст.</span>
          </article>
          <article className="overview-note">
            <p className="overview-note__label">Шаг 3</p>
            <strong>Сохраните feedback</strong>
            <span>Подтвердите результат или укажите верную цену.</span>
          </article>
          <article className="overview-note">
            <p className="overview-note__label">Максимум</p>
            <strong>{formatCurrency(stats.topPrice)}</strong>
            <span>самая высокая цена в текущей выборке.</span>
          </article>
        </section>

        <section id="manual-test">
          <UploadPanel onRecognized={refreshHistory} />
        </section>

        <section id="history" className="panel">
          <div className="panel__header panel__header--space">
            <div>
              <p className="panel__eyebrow">Review queue</p>
              <h2>История и ручная валидация</h2>
            </div>

            <div className="toolbar">
              {(["all", "pending", "ok", "error"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`filter-chip ${status === option ? "filter-chip--active" : ""}`}
                  onClick={() => {
                    setStatus(option);
                    setOffset(0);
                  }}
                >
                  {option === "all" && "Все"}
                  {option === "pending" && "На проверке"}
                  {option === "ok" && "OK"}
                  {option === "error" && "Ошибки"}
                </button>
              ))}
            </div>
          </div>

          <HistoryTable
            items={items}
            isLoading={isLoading}
            error={error}
            offset={offset}
            total={total}
            onOpen={setSelectedItem}
          />

          <div className="pagination">
            <button
              type="button"
              className="button button--ghost"
              disabled={offset === 0}
              onClick={() =>
                setOffset((value) => Math.max(0, value - PAGE_SIZE))
              }
            >
              Назад
            </button>
            <span>
              Страница {currentPage} из {totalPages}
            </span>
            <button
              type="button"
              className="button button--ghost"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset((value) => value + PAGE_SIZE)}
            >
              Дальше
            </button>
          </div>
        </section>
      </main>

      <RecognitionModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onFeedbackSaved={refreshHistory}
      />
    </div>
  );
}
