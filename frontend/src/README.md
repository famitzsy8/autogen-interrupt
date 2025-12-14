# Frontend Source

This directory contains the React application source code.


## Subdirectories

- `components/`: All React components including tree visualization and UI elements
- `hooks/`: Custom React hooks for WebSocket and state management
- `store/`: Zustand store for global application state
- `types/`: TypeScript type definitions
- `utils/`: Utility functions for tree manipulation and data transformation
- `constants/`: Application constants


## Files

### Main Application (`App.tsx`)
Root component managing the entire application flow. Establishes WebSocket connection on mount, coordinates between ConfigForm (initialization), TreeVisualization (conversation display), and various control components (InterruptButton, FloatingInputPanel, AgentInputModal). Handles interrupt/message sending, tracks edge interrupts for branching, and manages modal states for agent input and termination.

### Entry Point (`main.tsx`)
Application bootstrap. Creates React root, wraps App in StrictMode, and mounts to the DOM root element.

### Global Styles (`index.css`)
Tailwind CSS configuration with custom dark theme colors (dark-bg, dark-border, dark-hover, dark-text, dark-accent).
