/**
 * Connection component manages the WebSocket connection and displays connection status.
 *
 * This component automatically connects when mounted and disconnects when unmounted.
 */

import React, { useEffect } from 'react'
import {
  useConnectionState,
  useConnectionActions,
  useError,
  useErrorActions,
} from '../hooks/useStore'
import { ConnectionState } from '../types'

export function Connection(): React.ReactElement {
  const connectionState = useConnectionState()
  const error = useError()
  const { clearError } = useErrorActions()

  // NOTE: Connection management is handled by App.tsx on initial mount.
  // This component is only responsible for displaying status, not managing the connection.

  const getStatusColor = (): string => {
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        return 'text-green-500'
      case ConnectionState.CONNECTING:
      case ConnectionState.RECONNECTING:
        return 'text-yellow-500'
      case ConnectionState.DISCONNECTED:
        return 'text-gray-500'
      case ConnectionState.ERROR:
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getStatusText = (): string => {
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        return 'Connected'
      case ConnectionState.CONNECTING:
        return 'Connecting...'
      case ConnectionState.RECONNECTING:
        return 'Reconnecting...'
      case ConnectionState.DISCONNECTED:
        return 'Disconnected'
      case ConnectionState.ERROR:
        return 'Connection Error'
      default:
        return 'Unknown'
    }
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
      <span className={getStatusColor()}>{getStatusText()}</span>

      {error && (
        <div className="ml-4 flex items-center gap-2">
          <span className="text-red-500 text-xs">
            {error.code}: {error.message}
          </span>
          <button
            onClick={clearError}
            className="text-xs text-gray-400 hover:text-gray-200 underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  )
}
