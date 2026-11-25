import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

import { CHAT_REAL } from './chatConfig.js'
import './styles.css'

async function iniciar() {
  // MSW solo en desarrollo: simula casos y bitácora si no hay VITE_API_URL, y el chat si VITE_CHAT_REAL no es true.
  if (import.meta.env.DEV && !CHAT_REAL) {
    const { worker } = await import('./mocks/browser.js')
    await worker.start({
      onUnhandledRequest: 'bypass',
    })
  }

  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

iniciar().catch((error) => {
  console.error('No se pudo iniciar la aplicación:', error)
  document.getElementById('root').textContent =
    'No se pudo iniciar la aplicación. Revisa la consola del navegador.'
})
