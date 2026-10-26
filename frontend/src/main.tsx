import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div style={{ padding: '20px' }}>
      <h1>Hello from main.tsx directly</h1>
      <p>If you see this, React is working.</p>
    </div>
  </StrictMode>,
)
