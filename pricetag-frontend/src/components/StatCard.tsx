interface StatCardProps {
  eyebrow: string;
  value: string;
  caption: string;
}

export function StatCard({ eyebrow, value, caption }: StatCardProps) {
  return (
    <article className="stat-card">
      <p className="stat-card__eyebrow">{eyebrow}</p>
      <h3 className="stat-card__value">{value}</h3>
      <p className="stat-card__caption">{caption}</p>
    </article>
  );
}
