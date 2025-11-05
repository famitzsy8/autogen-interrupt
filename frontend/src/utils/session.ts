/**
 * Session management utilities for isolated tab sessions.
 *
 * Each tab/browser window gets its own unique session_id to ensure
 * complete isolation - no cross-tab interference whatsoever.
 */

/**
 * Generate a simple UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Generate a new unique session ID for this tab.
 *
 * Each tab gets a fresh session_id, ensuring complete isolation.
 * No localStorage is used - tabs do NOT share sessions.
 *
 * @returns {string} A new unique session ID
 */
export function getOrCreateSessionId(): string {
  const newSessionId = `session_${generateUUID()}`
  console.log(`[Session] Created fresh session ID for this tab: ${newSessionId}`)
  return newSessionId
}
