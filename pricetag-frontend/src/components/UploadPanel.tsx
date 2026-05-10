import { useRef, useState } from "react";
import { recognizePrice } from "../lib/api";
import { formatConfidence, formatCurrency } from "../lib/format";
import type { RecognizeResponse } from "../types/api";

interface UploadPanelProps {
  onRecognized: () => void;
}

export function UploadPanel({ onRecognized }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<RecognizeResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultTone =
    result == null
      ? "muted"
      : result.detected
        ? (result.confidence ?? 0) >= 0.75
          ? "success"
          : "warning"
        : "danger";
  const resultLabel =
    result == null
      ? "Ожидает анализа"
      : result.detected
        ? (result.confidence ?? 0) >= 0.75
          ? "Уверенное распознавание"
          : "Нужна проверка оператора"
        : "Цена не найдена";

  function handleFileSelection(file: File | null) {
    setSelectedFile(file);
    setResult(null);
    setError(null);

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  }

  function clearSelection() {
    handleFileSelection(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleSubmit() {
    if (!selectedFile) {
      setError("Сначала выберите изображение ценника.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await recognizePrice(selectedFile);
      setResult(response);
      onRecognized();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Не удалось обработать изображение.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel panel--hero">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Live test</p>
          <h2>Быстрая проверка одного изображения</h2>
        </div>
        <span className="panel__tag">POST /recognize</span>
      </div>

      <div className="uploader">
        <button
          type="button"
          className="uploader__dropzone"
          onClick={() => inputRef.current?.click()}
        >
          <span className="uploader__title">Выберите фото ценника для распознавания</span>
          <span className="uploader__hint">
            Лучше всего работают четкие снимки без сильного наклона, бликов и
            обрезанных краев ценника.
          </span>
        </button>

        <input
          ref={inputRef}
          hidden
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) =>
            handleFileSelection(event.target.files?.[0] ?? null)
          }
        />

        <div className="uploader__actions">
          <div className="uploader__meta">
            <strong>{selectedFile?.name ?? "Файл не выбран"}</strong>
            <span>
              {selectedFile
                ? `${Math.round(selectedFile.size / 1024)} KB`
                : "После выбора здесь появятся данные загруженного файла"}
            </span>
          </div>

          <div className="uploader__action-group">
            <button
              type="button"
              className="button button--ghost"
              disabled={!selectedFile || isSubmitting}
              onClick={clearSelection}
            >
              Очистить
            </button>
            <button
              type="button"
              className="button button--primary"
              disabled={isSubmitting}
              onClick={() => void handleSubmit()}
            >
              {isSubmitting ? "Анализируем..." : "Распознать цену"}
            </button>
          </div>
        </div>

        <div className="uploader__tips">
          <span>Форматы: JPEG, PNG, WEBP</span>
          <span>Лучше крупный кадр ценника</span>
          <span>Проверьте итоговую цену и OCR-текст</span>
        </div>
      </div>

      {(previewUrl || result) && (
        <div className="result-grid">
          <div className="result-card result-card--image">
            {previewUrl ? (
              <img src={previewUrl} alt="Предпросмотр ценника" />
            ) : (
              <div className="result-card__empty">Изображение появится здесь</div>
            )}
          </div>

          <div className="result-card">
            <div className="result-card__topline">
              <p className="result-card__label">Распознанная цена</p>
              <span className={`result-card__status result-card__status--${resultTone}`}>
                {resultLabel}
              </span>
            </div>
            <h3 className="result-card__price">
              {formatCurrency(result?.price ?? null)}
            </h3>

            <div className="result-card__facts">
              <div>
                <span>Уверенность</span>
                <strong>{formatConfidence(result?.confidence)}</strong>
              </div>
              <div>
                <span>Запрос</span>
                <strong>{result?.request_id.slice(0, 8) ?? "—"}</strong>
              </div>
              <div>
                <span>OCR-движок</span>
                <strong>{result?.engine ?? "—"}</strong>
              </div>
              <div>
                <span>Проверка</span>
                <strong>{result?.detected ? "найдена цена" : "нет цены"}</strong>
              </div>
            </div>

            <div className="result-card__text">
              <p>Сырой текст OCR</p>
              <pre>
                {result?.raw_text ??
                  "После анализа здесь появится текст, который увидела OCR-модель."}
              </pre>
            </div>

            {result?.message && (
              <p className="result-card__message">{result.message}</p>
            )}
          </div>
        </div>
      )}

      {error && <p className="panel__error">{error}</p>}
    </section>
  );
}
