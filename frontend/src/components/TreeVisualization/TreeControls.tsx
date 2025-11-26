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
  isNavigationMode = false,
  onEnableAutoCenter,
}: TreeControlsProps): React.ReactElement {
  return (
    <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
      {/* Navigation mode indicator */}
      {isNavigationMode && onEnableAutoCenter && (
        <div className="bg-orange-900 bg-opacity-30 border border-orange-500 rounded-lg p-3 shadow-lg">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
            <span className="text-xs font-semibold text-orange-400">Navigation Mode</span>
          </div>
          <p className="text-xs text-gray-400 mb-2">
            Auto-centering paused
          </p>
          <button
            onClick={onEnableAutoCenter}
            className="w-full px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-xs font-medium rounded transition-colors"
            title="Resume auto-centering to new messages"
          >
            Resume Auto-Center
          </button>
        </div>
      )}
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
