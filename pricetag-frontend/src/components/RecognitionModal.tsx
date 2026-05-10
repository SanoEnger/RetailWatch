import { useEffect, useState } from "react";
import { fetchRecognitionDetail, sendFeedback } from "../lib/api";
import {
  formatConfidence,
  formatCurrency,
  formatDate,
  getStatusLabel,
  getStatusTone,
} from "../lib/format";
import type { HistoryDetailItem, HistoryItem } from "../types/api";

interface RecognitionModalProps {
  item: HistoryItem | null;
  onClose: () => void;
  onFeedbackSaved: () => void;
}

export function RecognitionModal({
  item,
  onClose,
  onFeedbackSaved,
}: RecognitionModalProps) {
  const [detail, setDetail] = useState<HistoryDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [correctPrice, setCorrectPrice] = useState("");

  useEffect(() => {
    if (!item) {
      return;
    }

    const currentItem = item;
    let isActive = true;

    async function loadDetail() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchRecognitionDetail(currentItem.id);

        if (!isActive) {
          return;
        }

        setDetail(response);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Не удалось загрузить детали распознавания.",
        );
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadDetail();

    return () => {
      isActive = false;
    };
  }, [item]);

  if (!item) {
    return null;
  }

  const activeItem: HistoryItem = item;

  async function handleFeedback(isValid: boolean) {
    setIsSaving(true);
    setError(null);

    try {
      await sendFeedback(activeItem.id, {
        is_valid: isValid,
        correct_price: isValid
          ? null
          : correctPrice.trim()
            ? Number(correctPrice.replace(",", "."))
            : null,
      });

      onFeedbackSaved();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось сохранить обратную связь.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="panel__header">
          <div>
            <p className="panel__eyebrow">Detail view</p>
            <h2>Карточка распознавания</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        {isLoading ? (
          <div className="modal__state">Загружаем детальную информацию...</div>
        ) : (
          <div className="modal__grid">
            <div className="modal__image">
              {detail?.image_base64 ? (
                <img
                  src={`data:image/jpeg;base64,${detail.image_base64}`}
                  alt="Оригинальное изображение"
                />
              ) : (
                <div className="result-card__empty">Изображение отсутствует</div>
              )}
            </div>

            <div className="modal__content">
              <div className="fact-list">
                <div>
                  <span>Дата</span>
                  <strong>{formatDate(activeItem.created_at)}</strong>
                </div>
                <div>
                  <span>Цена</span>
                  <strong>{formatCurrency(activeItem.extracted_price)}</strong>
                </div>
                <div>
                  <span>Уверенность</span>
                  <strong>{formatConfidence(activeItem.confidence)}</strong>
                </div>
                <div>
                  <span>Статус</span>
                  <strong className={`status-inline status-inline--${getStatusTone(activeItem.is_valid)}`}>
                    {getStatusLabel(activeItem.is_valid)}
                  </strong>
                </div>
              </div>

              <div className="result-card__text">
                <p>Сырой текст OCR</p>
                <pre>{detail?.raw_text ?? "OCR-текст не сохранен."}</pre>
              </div>

              <div className="feedback-box">
                <p>Оценка результата</p>
                <label className="input-group">
                  <span>Верная цена, если нужно скорректировать</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="Например, 129.90"
                    value={correctPrice}
                    onChange={(event) => setCorrectPrice(event.target.value)}
                  />
                </label>

                <div className="feedback-box__actions">
                  <button
                    type="button"
                    className="button button--ghost"
                    disabled={isSaving}
                    onClick={() => void handleFeedback(true)}
                  >
                    Подтвердить как OK
                  </button>
                  <button
                    type="button"
                    className="button button--danger"
                    disabled={isSaving}
                    onClick={() => void handleFeedback(false)}
                  >
                    Отметить ошибку
                  </button>
                </div>
              </div>

              {error && <p className="panel__error">{error}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
