/** Lightbox — image preview with left/right navigation. */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  images: string[]
  startIndex?: number
  onClose: () => void
}

export default function Lightbox({ images, startIndex = 0, onClose }: Props) {
  const [index, setIndex] = useState(startIndex)

  const prev = useCallback(() => setIndex(i => (i - 1 + images.length) % images.length), [images.length])
  const next = useCallback(() => setIndex(i => (i + 1) % images.length), [images.length])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') prev()
      if (e.key === 'ArrowRight') next()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose, prev, next])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.85)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'default',
      }}
      onClick={onClose}
    >
      <AnimatePresence mode="wait">
        <motion.img
          key={index}
          src={images[index]}
          alt=""
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.2 }}
          style={{
            maxWidth: '90vw',
            maxHeight: '90vh',
            objectFit: 'contain',
            borderRadius: 8,
          }}
          onClick={e => e.stopPropagation()}
        />
      </AnimatePresence>

      {images.length > 1 && (
        <>
          <button
            onClick={e => { e.stopPropagation(); prev() }}
            style={{
              position: 'absolute',
              left: 20,
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              fontSize: 24,
              width: 48,
              height: 48,
              borderRadius: '50%',
              cursor: 'pointer',
            }}
          >
            ‹
          </button>
          <button
            onClick={e => { e.stopPropagation(); next() }}
            style={{
              position: 'absolute',
              right: 20,
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              fontSize: 24,
              width: 48,
              height: 48,
              borderRadius: '50%',
              cursor: 'pointer',
            }}
          >
            ›
          </button>
        </>
      )}

      <div style={{
        position: 'absolute',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        color: 'rgba(255,255,255,0.7)',
        fontSize: 14,
      }}>
        {index + 1} / {images.length}
      </div>

      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: 20,
          right: 20,
          background: 'rgba(255,255,255,0.2)',
          border: 'none',
          color: 'white',
          fontSize: 20,
          width: 40,
          height: 40,
          borderRadius: '50%',
          cursor: 'pointer',
        }}
      >
        ×
      </button>
    </motion.div>
  )
}
