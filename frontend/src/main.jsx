import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

async function iniciar() {
  if (import.meta.env.DEV) {
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