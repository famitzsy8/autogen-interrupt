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
import { ZoomIn, ZoomOut, Maximize2, Focus } from 'lucide-react'

/**
 * Props for TreeControls component.
 */
interface TreeControlsProps {
  onRecenter: () => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
  nodeCount?: number
  treeDepth?: number
}

/**
 * TreeControls component for tree navigation and zoom controls.
 */
export function TreeControls({
  onRecenter,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  nodeCount = 0,
  treeDepth = 0,
}: TreeControlsProps): React.ReactElement {
  return (
    <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
      {/* Stats panel */}
      <div className="bg-dark-hover border border-dark-border rounded-lg p-3 shadow-lg">
        <h3 className="text-xs font-semibold text-gray-400 mb-2">Tree Stats</h3>
        <div className="space-y-1 text-xs text-gray-500">
          <div className="flex items-center justify-between gap-4">
            <span>Nodes:</span>
            <span className="text-dark-text font-medium">{nodeCount}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span>Depth:</span>
            <span className="text-dark-text font-medium">{treeDepth}</span>
          </div>
        </div>
      </div>

      {/* Control buttons */}
      <div className="bg-dark-hover border border-dark-border rounded-lg p-2 shadow-lg">
        <div className="flex flex-col gap-1">
          {/* Recenter button */}
          <ControlButton
            onClick={onRecenter}
            icon={<Focus size={16} />}
            label="Recenter (C)"
            title="Recenter view on last user message"
          />

          {/* Zoom controls */}
          <div className="h-px bg-dark-border my-1" />

          <ControlButton
            onClick={onZoomIn}
            icon={<ZoomIn size={16} />}
            label="Zoom In (+)"
            title="Zoom in"
          />

          <ControlButton
            onClick={onZoomOut}
            icon={<ZoomOut size={16} />}
            label="Zoom Out (-)"
            title="Zoom out"
          />

          <ControlButton
            onClick={onResetZoom}
            icon={<Maximize2 size={16} />}
            label="Reset (0)"
            title="Reset zoom to default"
          />
        </div>
      </div>

      {/* Keyboard shortcuts help */}
      <div className="bg-dark-hover border border-dark-border rounded-lg p-3 shadow-lg">
        <h3 className="text-xs font-semibold text-gray-400 mb-2">Shortcuts</h3>
        <div className="space-y-1 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-dark-bg border border-dark-border rounded text-xs">
              C
            </kbd>
            <span>Recenter</span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-dark-bg border border-dark-border rounded text-xs">
              +
            </kbd>
            <span>Zoom in</span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-dark-bg border border-dark-border rounded text-xs">
              -
            </kbd>
            <span>Zoom out</span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-dark-bg border border-dark-border rounded text-xs">
              0
            </kbd>
            <span>Reset zoom</span>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-dark-bg border border-dark-border rounded text-xs">
              Drag
            </kbd>
            <span>Pan view</span>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Props for ControlButton component.
 */
interface ControlButtonProps {
  onClick: () => void
  icon: React.ReactNode
  label: string
  title: string
}

/**
 * Reusable button component for tree controls.
 */
function ControlButton({
  onClick,
  icon,
  label,
  title,
}: ControlButtonProps): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded text-gray-400 hover:text-dark-text hover:bg-dark-bg transition-colors"
      title={title}
      aria-label={label}
    >
      {icon}
      <span className="text-xs font-medium">{label}</span>
    </button>
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
