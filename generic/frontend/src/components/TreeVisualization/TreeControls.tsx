/**
 * TreeControls component provides navigation and interaction controls for the tree visualization.
 *
 * Features:
 * - Recenter button to reset view to last user message
 * - Zoom in/out controls
 * - Reset zoom button
 * - Tree statistics display
 * - Accessibility support with keyboard shortcuts
 */

import React from 'react'

/**
 * Props for TreeControls component.
 */
interface TreeControlsProps {
  isNavigationMode?: boolean
  onEnableAutoCenter?: () => void
}

/**
 * TreeControls component for tree navigation and zoom controls.
 */
export function TreeControls({
  isNavigationMode: _isNavigationMode = false,
  onEnableAutoCenter: _onEnableAutoCenter,
}: TreeControlsProps): React.ReactElement {
  // Navigation mode popup removed - auto-centering still works in the background
  return (
    <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
      {/* Navigation mode popup removed */}
    </div>
  )
}

/**
 * Hook for keyboard shortcuts.
 */
export function useTreeKeyboardShortcuts(controls: {
  onRecenter: () => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
}): void {
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      // Ignore if user is typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      switch (event.key.toLowerCase()) {
        case 'c':
          event.preventDefault()
          controls.onRecenter()
          break
        case '+':
        case '=':
          event.preventDefault()
          controls.onZoomIn()
          break
        case '-':
        case '_':
          event.preventDefault()
          controls.onZoomOut()
          break
        case '0':
          event.preventDefault()
          controls.onResetZoom()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [controls])
}
