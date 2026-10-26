import { createRoot } from 'react-dom/client'

const rootEl = document.getElementById('root')
if (rootEl) {
  rootEl.textContent = 'JS bundle executing!'
  createRoot(rootEl).render(
    <div style={{ padding: '20px', color: 'red' }}>
      <h1>Hello from React</h1>
      <p>If you see this, React is mounting.</p>
    </div>
  )
} else {
  document.body.innerHTML = '<div style="color:red;padding:20px">Root element not found!</div>'
}
