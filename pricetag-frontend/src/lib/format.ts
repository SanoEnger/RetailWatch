export function formatCurrency(value: number | null | undefined): string {
  if (value == null) {
    return "Не найдено";
  }

  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatConfidence(value: number | null | undefined): string {
  if (value == null) {
    return "n/a";
  }

  return `${Math.round(value * 100)}%`;
}

export function getStatusLabel(isValid: boolean | null): string {
  if (isValid === true) {
    return "OK";
  }

  if (isValid === false) {
    return "Ошибка";
  }

  return "На проверке";
}

export function getStatusTone(
  isValid: boolean | null,
): "success" | "danger" | "muted" {
  if (isValid === true) {
    return "success";
  }

  if (isValid === false) {
    return "danger";
  }

  return "muted";
}
