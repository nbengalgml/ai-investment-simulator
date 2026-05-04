import { useState } from 'react'
import { getTickerInfo, googleFinanceUrl } from '../data/tickers'

interface Props {
  ticker: string
  className?: string
}

export function TickerBadge({ ticker, className = '' }: Props) {
  const [show, setShow] = useState(false)
  const info = getTickerInfo(ticker)

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <a
        href={googleFinanceUrl(ticker)}
        target="_blank"
        rel="noopener noreferrer"
        className={`font-mono font-bold text-blue-400 hover:text-blue-300 hover:underline transition-colors ${className}`}
        onClick={e => e.stopPropagation()}
      >
        {ticker}
      </a>

      {show && info && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-64 bg-gray-900 border border-gray-700 rounded-lg shadow-xl p-3 text-left pointer-events-none">
          <div className="flex items-start justify-between gap-2 mb-1.5">
            <div>
              <div className="text-xs font-bold text-gray-100">{ticker}</div>
              <div className="text-xs text-gray-400">{info.name}</div>
            </div>
            <span className="text-xs text-gray-600 flex-shrink-0 mt-0.5">{info.exchange}</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">{info.description}</p>
          <div className="mt-2 pt-2 border-t border-gray-800 text-xs text-blue-500">
            ↗ Click to open on Google Finance
          </div>
        </div>
      )}
    </div>
  )
}
