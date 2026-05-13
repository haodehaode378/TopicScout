/** RichTextEditor — simple contenteditable with basic formatting. */

import { useRef, useCallback } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export default function RichTextEditor({ value, onChange, placeholder, className }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  const handleInput = useCallback(() => {
    if (ref.current) {
      onChange(ref.current.innerText)
    }
  }, [onChange])

  const execCommand = useCallback((cmd: string, val?: string) => {
    document.execCommand(cmd, false, val)
    ref.current?.focus()
  }, [])

  return (
    <div className={className}>
      <div style={{
        display: 'flex',
        gap: 4,
        padding: '4px 8px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
      }}>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => execCommand('bold')}
          title="加粗"
          style={{ fontWeight: 700 }}
        >
          B
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => execCommand('italic')}
          title="斜体"
          style={{ fontStyle: 'italic' }}
        >
          I
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => execCommand('insertUnorderedList')}
          title="列表"
        >
          •
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => execCommand('formatBlock', 'h2')}
          title="标题"
        >
          H
        </button>
      </div>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={handleInput}
        style={{
          padding: '8px 12px',
          minHeight: 80,
          outline: 'none',
          fontSize: 14,
          lineHeight: 1.6,
          color: 'var(--text)',
        }}
        dangerouslySetInnerHTML={{ __html: value }}
        data-placeholder={placeholder}
      />
    </div>
  )
}
