/**
 * Example component demonstrating how to use the debate store.
 *
 * This component manages the WebSocket connection and displays connection status.
 */

import React, { useEffect } from 'react'
import {
  useConnectionState,
  useConnectionActions,
  useError,
  useErrorActions,
} from '../hooks/useDebateStore'
import { ConnectionState } from '../types'

export function DebateConnection(): React.ReactElement {
  const connectionState = useConnectionState()
  const { connect, disconnect } = useConnectionActions()
  const error = useError()
  const { clearError } = useErrorActions()

  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:5173/ws/debate'

  useEffect(() => {
    // Connect when component mounts
    connect(wsUrl)

    // Disconnect when component unmounts
    return () => {
      disconnect()
    }
  }, [wsUrl, connect, disconnect])

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
