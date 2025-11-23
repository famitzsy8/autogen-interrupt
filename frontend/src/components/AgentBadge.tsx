/**
 * AgentBadge Component
 *
 * Displays an agent name in a colored box/badge using their assigned D3 color.
 * This makes it immediately clear which color is associated with each agent.
 *
 * Features:
 * - Uses D3 schemeDark2 colors via getAgentColorD3()
 * - Supports different sizes (sm, md, lg)
 * - Optional display of agent_name vs display_name
 * - Accessible with proper contrast
 */

import React from 'react'
import { getAgentColorD3 } from '../utils/colorSchemes'

interface AgentBadgeProps {
  agentName: string
  displayName?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function AgentBadge({
  agentName,
  displayName,
  size = 'md',
  className = '',
}: AgentBadgeProps): React.ReactElement {
  const color = getAgentColorD3(agentName)
  const label = displayName || agentName

  // Size-based styling
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  }

  const sizeClass = sizeClasses[size]

  return (
    <span
      className={`inline-flex items-center justify-center font-semibold rounded-xl ${sizeClass} ${className}`}
      style={{
        backgroundColor: color,
        color: '#ffffff',
        opacity: 0.9,
        lineHeight: 1,
      }}
      title={agentName !== label ? agentName : undefined}
    >
      {label}
    </span>
  )
}
