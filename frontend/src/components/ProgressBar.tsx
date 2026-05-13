/** ProgressBar — smooth animated progress bar. */

import { motion } from 'framer-motion'

interface Props {
  value: number
  max?: number
  color?: string
  height?: number
  showLabel?: boolean
}

export default function ProgressBar({ value, max = 100, color, height = 6, showLabel = false }: Props) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: '100%',
        height,
        background: 'var(--bg-hover)',
        borderRadius: height / 2,
        overflow: 'hidden',
      }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{
            height: '100%',
            background: color || 'var(--accent)',
            borderRadius: height / 2,
          }}
        />
      </div>
      {showLabel && (
        <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 36 }}>
          {pct.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
