import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input:not([disabled]), select, [tabindex]:not([tabindex="-1"])'

/**
 * モーダル/ダイアログ共通のアクセシビリティ挙動。
 * Escで閉じる・開いた際に初期フォーカス・Tabでのフォーカストラップ・閉じた際に元の要素へフォーカスを戻す。
 */
export function useDialogA11y<T extends HTMLElement>(isOpen: boolean, onClose: () => void) {
  const containerRef = useRef<T | null>(null)

  useEffect(() => {
    if (!isOpen) return
    const container = containerRef.current
    const previouslyFocused = document.activeElement as HTMLElement | null
    const focusable = container ? Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)) : []
    focusable[0]?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key === 'Tab' && container) {
        const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
        if (items.length === 0) return
        const first = items[0]
        const last = items[items.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [isOpen, onClose])

  return containerRef
}
