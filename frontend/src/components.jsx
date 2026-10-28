import { useEffect } from 'react'
import {
  Loader, Eye, Check, CircleAlert, CircleCheck, CircleX, TriangleAlert,
  Inbox, Upload, List, LogOut,
} from 'lucide-react'
import logo from './assets/logo.png'

export function Logo({ size = 40 }) {
  return <img src={logo} width={size} height={size} alt="" aria-hidden="true" style={{ display: 'block' }} />
}

const ESTADOS = {
  procesando: ['b-info', Loader, 'Procesando'],
  revision: ['b-neutro', Eye, 'En revisión'],
  revisado: ['b-neutro', Check, 'Revisado'],
  error: ['b-error', CircleAlert, 'Error de procesamiento'],
}
const RESULTADOS = {
  aceptado: ['b-exito', CircleCheck, 'Aceptado'],
  rechazado: ['b-error', CircleX, 'Rechazado'],
  humana: ['b-adv', TriangleAlert, 'Requiere revisión humana'],
}

function BadgeDe({ mapa, valor }) {
  if (!valor) return <span className="muted">—</span>
  const [clase, Icono, texto] = mapa[valor]
  return <span className={`badge ${clase}`}><Icono size={16} />{texto}</span>
}
export const Estado = ({ valor }) => <BadgeDe mapa={ESTADOS} valor={valor} />
export const Resultado = ({ valor }) => <BadgeDe mapa={RESULTADOS} valor={valor} />

export function Banner({ tipo = 'info', icono: Icono = CircleAlert, children }) {
  return <div className={`banner ban-${tipo}`}><Icono size={20} /><div>{children}</div></div>
}

export function Shell({ activo, usuario, ir, onSalir, children }) {
  const nav = [
    ['casos', Inbox, 'Casos'],
    ['subir', Upload, 'Subir caso'],
    ['bitacora', List, 'Bitácora'],
  ]
  return (
    <div className="shell">
      <header className="topbar">
        <div className="marca"><Logo size={34} /><span className="sep" />Data Steward</div>
        <div className="usuario">
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className="avatar">{usuario.iniciales}</span>
            <div className="txt">
              <div className="nombre">{usuario.nombre}</div>
              <div className="rol">{usuario.rol}</div>
            </div>
          </div>
          <button className="salir" onClick={onSalir}><LogOut size={18} />Cerrar sesión</button>
        </div>
      </header>
      <div className="cuerpo">
        <nav className="sidebar">
          {nav.map(([id, Icono, texto]) => (
            <button key={id} className={`nav-item ${activo === id ? 'activo' : ''}`} onClick={() => ir(id)}>
              <Icono size={20} />{texto}
            </button>
          ))}
        </nav>
        {children}
      </div>
    </div>
  )
}

export function Dialogo({ titulo, children, onCancelar, onConfirmar }) {
  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onCancelar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onCancelar])
  return (
    <div className="velo" onClick={onCancelar}>
      <div className="dialogo" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h2>{titulo}</h2>
        {children}
        <div className="acc">
          <button className="btn" onClick={onCancelar}>Cancelar</button>
          <button className="btn btn-primario" onClick={onConfirmar} autoFocus>Confirmar</button>
        </div>
      </div>
    </div>
  )
}

export function Toast({ toast, onCerrar }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(onCerrar, 3200)
    return () => clearTimeout(t)
  }, [toast, onCerrar])
  if (!toast) return null
  const Icono = toast.icono || Check
  return (
    <div className="toast" role="status">
      <Icono size={18} color={toast.color || '#7fd3a5'} />{toast.texto}
    </div>
  )
}
