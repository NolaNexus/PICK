import { createRoot } from 'react-dom/client'

const rootEl = document.getElementById('root')
if (!rootEl) {
  console.error('root element not found')
} else {
  createRoot(rootEl).render(
    <div style={{ padding: '20px', color: 'red' }}>
      <h1>Hello from main.tsx directly</h1>
      <p>If you see this, React is working.</p>
    </div>
  )
}
