export const fmt = {
  usd: (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n),

  pnl: (n: number) => {
    const abs = Math.abs(n)
    const sign = n >= 0 ? '+' : '-'
    return `${sign}${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(abs)}`
  },

  pct: (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`,

  date: (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
}
