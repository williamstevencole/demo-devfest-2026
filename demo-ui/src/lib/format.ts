export const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function signedMoney(value: number): string {
  const formatted = money.format(Math.abs(value));
  return `${value >= 0 ? "+" : "−"}${formatted}`;
}
