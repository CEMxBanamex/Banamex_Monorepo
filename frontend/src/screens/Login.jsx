import { LogIn, TriangleAlert } from 'lucide-react'
import { Logo, Banner } from '../components.jsx'

export default function Login({ expirada, onEntrar }) {
  return (
    <div className="login">
      <aside className="login-marca">
        <div className="logo-fila"><Logo size={60} />Data Steward</div>
        <Logo size={360} />
        <p>El agente extrae, consulta reglas y explica cada hallazgo con evidencia. Tú revisas y decides.</p>
      </aside>
      <main className="login-form">
        <div className="login-caja">
          <h1>Data Steward</h1>
          <p className="desc">
            Revisión de facturas y validación de registros contra políticas, con un agente de IA que
            recomienda y una persona que decide.
          </p>
          {expirada && (
            <div style={{ marginBottom: 24 }}>
              <Banner tipo="adv" icono={TriangleAlert}>Tu sesión expiró. Inicia sesión de nuevo</Banner>
            </div>
          )}
          <button className="btn btn-primario btn-bloque" onClick={onEntrar}>
            <LogIn size={20} />Iniciar sesión
          </button>
          <p className="nota">El acceso lo gestiona el proveedor de identidad de la institución.</p>
          <p className="proto">Prototipo · todos los datos son ficticios</p>
        </div>
      </main>
    </div>
  )
}
