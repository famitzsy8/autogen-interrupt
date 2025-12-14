# Thesis Frontend

This is the React frontend that provides the user interface for interacting with dynamic agent teams. It visualizes agent conversations as a tree structure and enables real-time user intervention.


## Subdirectories

- `src/components`: Contains all React components including the tree visualization, agent input modals, configuration forms, and control elements

- `src/components/TreeVisualization`: D3-based visualization components for rendering the conversation tree

- `src/components/StateDisplay`: Components for displaying agent and conversation state

- `src/hooks`: Custom React hooks for WebSocket connections and state management

- `src/store`: Zustand store for global application state

- `src/types`: TypeScript type definitions for messages, agents, and tree structures

- `src/utils`: Utility functions for tree manipulation and data transformation

- `src/constants`: Application constants and configuration values


## Files

The application entry point is `main.tsx`, which renders `App.tsx`. The app uses Vite as the build tool and Tailwind CSS for styling. To run the frontend, use the following command:

`docker build -t frontend .`
