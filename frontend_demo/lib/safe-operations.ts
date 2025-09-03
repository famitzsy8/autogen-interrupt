/**
 * Safe JSON and data operations to prevent frontend crashes
 * These utilities handle common error scenarios that cause application crashes
 */

// Safe JSON parsing with fallback
export function safeJSONParse<T = any>(jsonString: string, fallback: T): T {
  try {
    const parsed = JSON.parse(jsonString);
    return parsed !== null && parsed !== undefined ? parsed : fallback;
  } catch (error) {
    console.warn('Failed to parse JSON:', error, 'Input:', jsonString);
    return fallback;
  }
}

// Safe JSON stringification
export function safeJSONStringify(obj: any, fallback: string = '{}'): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (error) {
    console.warn('Failed to stringify object:', error);
    return fallback;
  }
}

// Safe object property access with dot notation
export function safeGet<T = any>(obj: any, path: string, fallback: T): T {
  try {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : fallback;
    }, obj);
  } catch (error) {
    console.warn(`Failed to access property "${path}":`, error);
    return fallback;
  }
}

// Safe array operations
export function safeArrayOperation<T>(
  array: any,
  operation: (arr: T[]) => T[],
  fallback: T[] = []
): T[] {
  try {
    if (!Array.isArray(array)) {
      console.warn('Expected array but got:', typeof array);
      return fallback;
    }
    return operation(array);
  } catch (error) {
    console.warn('Array operation failed:', error);
    return fallback;
  }
}

// Safe state update for React
export function safeStateUpdate<T>(
  setState: React.Dispatch<React.SetStateAction<T>>,
  newValue: T | ((prev: T) => T),
  validator?: (value: T) => boolean
): void {
  try {
    if (typeof newValue === 'function') {
      setState((prev: T) => {
        try {
          const computed = (newValue as (prev: T) => T)(prev);
          if (validator && !validator(computed)) {
            console.warn('State update failed validation, keeping previous state');
            return prev;
          }
          return computed;
        } catch (error) {
          console.warn('State update function failed:', error);
          return prev;
        }
      });
    } else {
      if (validator && !validator(newValue)) {
        console.warn('State update failed validation, ignoring update');
        return;
      }
      setState(newValue);
    }
  } catch (error) {
    console.error('Failed to update state:', error);
  }
}

// Safe WebSocket message validation
export function validateWebSocketMessage(message: any): boolean {
  try {
    return (
      message &&
      typeof message === 'object' &&
      typeof message.type === 'string' &&
      typeof message.timestamp === 'string'
    );
  } catch (error) {
    console.warn('WebSocket message validation failed:', error);
    return false;
  }
}

// Rate limiting for API calls (prevents spam and 429 errors)
export class RateLimiter {
  private lastCall: number = 0;
  private callCount: number = 0;
  private resetTime: number = 0;

  constructor(
    private maxCalls: number = 10,
    private windowMs: number = 60000, // 1 minute
    private cooldownMs: number = 5000 // 5 seconds between calls
  ) {}

  canMakeCall(): boolean {
    const now = Date.now();
    
    // Reset counter if window has passed
    if (now - this.resetTime > this.windowMs) {
      this.callCount = 0;
      this.resetTime = now;
    }

    // Check if we're under rate limit
    if (this.callCount >= this.maxCalls) {
      console.warn(`Rate limit exceeded. ${this.callCount}/${this.maxCalls} calls made in window.`);
      return false;
    }

    // Check cooldown between calls
    if (now - this.lastCall < this.cooldownMs) {
      console.warn(`Cooldown active. ${this.cooldownMs - (now - this.lastCall)}ms remaining.`);
      return false;
    }

    return true;
  }

  recordCall(): void {
    this.lastCall = Date.now();
    this.callCount++;
  }

  getRemainingCalls(): number {
    return Math.max(0, this.maxCalls - this.callCount);
  }

  getTimeUntilReset(): number {
    return Math.max(0, this.windowMs - (Date.now() - this.resetTime));
  }
}

// Error classification for better handling
export function classifyError(error: any): {
  type: 'network' | 'validation' | 'authentication' | 'rate_limit' | 'server' | 'client' | 'unknown';
  isRetryable: boolean;
  userMessage: string;
  technicalMessage: string;
} {
  const errorString = String(error?.message || error || '').toLowerCase();
  
  if (errorString.includes('429') || errorString.includes('too many requests') || errorString.includes('rate limit')) {
    return {
      type: 'rate_limit',
      isRetryable: true,
      userMessage: 'The service is temporarily overloaded. Please wait a moment and try again.',
      technicalMessage: 'Rate limit exceeded (429)'
    };
  }
  
  if (errorString.includes('network') || errorString.includes('connection') || errorString.includes('timeout')) {
    return {
      type: 'network',
      isRetryable: true,
      userMessage: 'Connection problem. Please check your internet and try again.',
      technicalMessage: 'Network connectivity issue'
    };
  }
  
  if (errorString.includes('401') || errorString.includes('unauthorized') || errorString.includes('authentication')) {
    return {
      type: 'authentication',
      isRetryable: false,
      userMessage: 'Authentication required. Please refresh the page.',
      technicalMessage: 'Authentication failure'
    };
  }
  
  if (errorString.includes('400') || errorString.includes('validation') || errorString.includes('invalid')) {
    return {
      type: 'validation',
      isRetryable: false,
      userMessage: 'Invalid request. Please check your input and try again.',
      technicalMessage: 'Request validation failed'
    };
  }
  
  if (errorString.includes('500') || errorString.includes('server error') || errorString.includes('internal')) {
    return {
      type: 'server',
      isRetryable: true,
      userMessage: 'Server error occurred. Please try again in a few moments.',
      technicalMessage: 'Internal server error'
    };
  }
  
  return {
    type: 'unknown',
    isRetryable: false,
    userMessage: 'An unexpected error occurred. Please refresh the page if the problem persists.',
    technicalMessage: errorString || 'Unknown error'
  };
}

// Safe async operation wrapper
export async function safeAsyncOperation<T>(
  operation: () => Promise<T>,
  fallback: T,
  onError?: (error: any) => void
): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    console.warn('Async operation failed:', error);
    if (onError) {
      onError(error);
    }
    return fallback;
  }
}

// Memory management for large arrays (prevents memory leaks)
export function limitArraySize<T>(array: T[], maxSize: number = 1000): T[] {
  if (array.length <= maxSize) {
    return array;
  }
  
  // Keep newest items, remove oldest
  const removed = array.length - maxSize;
  console.info(`Trimming array from ${array.length} to ${maxSize} items (removed ${removed} oldest items)`);
  return array.slice(-maxSize);
}

// Debounce function to prevent rapid successive calls
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): T {
  let timeoutId: NodeJS.Timeout;
  
  return ((...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  }) as T;
}