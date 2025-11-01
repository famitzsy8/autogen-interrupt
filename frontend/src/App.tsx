import React from 'react'


function App(): React.ReactElement {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/research'
    return (
        <div>
            <h1>Generic Frontend</h1>
        </div>
    )
}

export default App