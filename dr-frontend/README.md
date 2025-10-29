# Debate Frontend

React + TypeScript frontend for the autogen debate team visualization with D3.js tree display and real-time chat interface.

## Features

- Real-time agent conversation display
- D3.js tree visualization of conversation flow
- User interrupt and message injection capabilities
- WebSocket-based communication with backend
- Dark theme UI with GitHub-inspired aesthetics

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **D3.js** for tree visualization
- **Zustand** for state management
- **WebSocket** for real-time communication

## Prerequisites

- Node.js 18+ and npm
- Backend server running at `ws://localhost:8001/ws/debate` (or configured URL)

## Installation

```bash
npm install
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` to configure the WebSocket endpoint:

```env
VITE_WS_URL=ws://localhost:8000/ws/debate
```

For production deployment, use `wss://` protocol:

```env
VITE_WS_URL=wss://your-production-domain.com/ws/debate
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Build

Create a production build:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Linting

Run ESLint to check for code issues:

```bash
npm run lint
```

## TypeScript Configuration

This project enforces strict TypeScript rules:

- No `any` types allowed (`noImplicitAny: true`)
- Strict null checks enabled
- Explicit function return types recommended
- All `@typescript-eslint/no-unsafe-*` rules enforced

## Project Structure

```
debate-frontend/
├── src/
│   ├── App.tsx           # Main application component
│   ├── main.tsx          # Application entry point
│   ├── index.css         # Global styles with Tailwind
│   ├── components/       # React components (to be added)
│   ├── stores/           # Zustand stores (to be added)
│   ├── types/            # TypeScript type definitions (to be added)
│   └── utils/            # Utility functions (to be added)
├── index.html            # HTML entry point
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── .eslintrc.cjs         # ESLint configuration
```

## Design Principles

- **No emojis** - Clean, professional UI
- **Sans-serif fonts** - System font stack for consistency
- **Dark theme** - GitHub dark color scheme (#0d1117 background, #c9d1d9 text)
- **Agent colors** - Opaque versions (40% opacity) of bright colors
- **GitHub-style branches** - Curved connections in tree visualization

## Next Steps

1. Implement Zustand store for state management (Task 2.3)
2. Build chat display components (Task 3.1)
3. Create D3.js tree visualization (Task 4.1)
4. Add WebSocket connection and message handling
5. Implement interrupt and user message features

## License

Part of the autogen-interrupt thesis project.
