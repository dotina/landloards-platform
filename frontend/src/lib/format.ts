// Intl.NumberFormat with currency=KES emits "Ksh" in en-KE; the design spec
// in §5.4 calls for the literal prefix "KES", so format the number neutrally
// and prepend ourselves.
const _numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
});

/** Format a Number or numeric string as e.g. "KES 25,000".
 *
 * Returns "KES 0" for invalid input rather than throwing — UIs always render. */
export function formatKES(value: number | string | null | undefined): string {
  const n =
    typeof value === "number"
      ? value
      : typeof value === "string"
      ? Number(value)
      : 0;
  if (!Number.isFinite(n)) return "KES 0";
  return `KES ${_numberFormatter.format(n)}`;
}

const _dateFormatter = new Intl.DateTimeFormat("en-KE", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

export function formatDate(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "";
  return _dateFormatter.format(d);
}
