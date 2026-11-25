import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { API_BASE_URL } from './api.js'
import './styles.css'

async function prepararApp() {
  if (import.meta.env.DEV && !API_BASE_URL) {
    const { worker } = await import('./mocks/browser.js')
    await worker.start({
      onUnhandledRequest: 'bypass',
    })
  }
}

prepararApp().then(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
