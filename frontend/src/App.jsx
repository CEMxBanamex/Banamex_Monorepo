import AccesoDemo from './screens/AccesoDemo.jsx'
import { useCallback, useEffect, useState } from 'react'
import { LayoutGrid, Bot, X, Moon, Sun } from 'lucide-react'
import { Shell, Toast } from './components.jsx'
import { USUARIOS, CASOS } from './data.js'
import Login from './screens/Login.jsx'
import Bandeja from './screens/Bandeja.jsx'
import Subir from './screens/Subir.jsx'
import { CASOS_REALES } from './api.js'
import DetalleReal from './screens/DetalleReal.jsx'
import DetalleFactura from './screens/Detalle.jsx'
import Validacion from './screens/Validacion.jsx'
import Bitacora from './screens/Bitacora.jsx'
import Asistente from './screens/Asistente.jsx'
import './interfaz.css'

const caso = (id) => CASOS.find((c) => c.id === id)
const NUEVO = { id: 'F-1043', archivo: 'factura_1043.pdf', tipo: 'Factura', estado: 'revision', resultado: 'humana' }

// Atajos para enseñar cada pantalla y sus estados sin recorrer el flujo completo.
const DEMO = [
  ['Inicio de sesión', [
    ['Normal', { pantalla: 'login' }],
    ['Sesión expirada', { pantalla: 'login', expirada: true }],
  ]],
  ['Bandeja de casos', [
    ['Con casos', { pantalla: 'casos', variante: 'normal' }],
    ['Vacía', { pantalla: 'casos', variante: 'vacio' }],
    ['Cargando', { pantalla: 'casos', variante: 'cargando' }],
    ['Error al cargar', { pantalla: 'casos', variante: 'error' }],
  ]],
  ['Subir caso', [['Formulario', { pantalla: 'subir' }]]],
  ['Detalle de factura', [
    ['Con hallazgos (F-1042)', { pantalla: 'factura', caso: 'F-1042', variante: 'normal' }],
    ['Procesando', { pantalla: 'factura', caso: 'F-1042', variante: 'procesando' }],
    ['Sin hallazgos', { pantalla: 'factura', caso: 'F-1041', variante: 'sinHallazgos' }],
    ['Falta evidencia o política', { pantalla: 'factura', caso: 'F-1042', variante: 'faltaPolitica' }],
    ['Error de procesamiento', { pantalla: 'factura', caso: 'V-0206', variante: 'error' }],
  ]],
  ['Validación con políticas', [['Rechazado (V-0207)', { pantalla: 'validacion', caso: 'V-0207' }]]],
  ['Bitácora', [['Eventos', { pantalla: 'bitacora' }]]],
]

export default function App() {
  const [vista, setVista] = useState({ pantalla: 'login' })
  const [usuarioDemo, setUsuarioDemo] = useState(null)
  const [toast, setToast] = useState(null)
  const [menu, setMenu] = useState(false)
  const [chatAbierto, setChatAbierto] = useState(false)
  const [tema, setTema] = useState(() => {
    try { return localStorage.getItem('dsa-tema') || 'claro' } catch { return 'claro' }
  })
  useEffect(() => {
    document.documentElement.dataset.tema = tema
    document.documentElement.style.colorScheme = tema === 'oscuro' ? 'dark' : 'light'
    try { localStorage.setItem('dsa-tema', tema) } catch { /* Almacenamiento no disponible. */ }
  }, [tema])
  useEffect(() => {
    const cerrar = (e) => { if (e.key === 'Escape') setChatAbierto(false) }
    window.addEventListener('keydown', cerrar)
    return () => window.removeEventListener('keydown', cerrar)
  }, [])
  const cerrarToast = useCallback(() => setToast(null), [])

  const ir = (pantalla) => { if (pantalla === 'asistente') { setChatAbierto(true); return }; setVista({ pantalla, variante: 'normal' }); window.scrollTo(0, 0) }
  const abrirCaso = (c) => {
    if (CASOS_REALES) { setVista({ pantalla: 'factura', caso: c.id }); return }
    setVista(c.tipo === 'Factura' || c.variante === 'error'
      ? { pantalla: 'factura', caso: c.id, variante: c.variante || 'normal' }
      : { pantalla: 'validacion', caso: c.id })
    window.scrollTo(0, 0)
  }
  const iniciar = (tipo, nuevoCaso) => {
    if (CASOS_REALES) { abrirCaso(nuevoCaso); return }
    const idCaso = nuevoCaso?.id || (tipo === 'factura' ? 'F-1043' : 'V-0207')
    setVista(tipo === 'factura'
      ? { pantalla: 'factura', caso: idCaso, variante: 'procesando' }
      : { pantalla: 'validacion', caso: idCaso })
    window.scrollTo(0, 0)
  }

  const { pantalla } = vista
  let contenido
  if (pantalla === 'login') {
    contenido = import.meta.env.VITE_ACCESO_DEMO === 'true'
      ? <AccesoDemo onEntrarAdmin={(correoAdmin) => {
          setUsuarioDemo({ nombre: 'Administrador', iniciales: 'AD', rol: 'Administrador', correo: correoAdmin, esAdmin: true })
          ir('casos')
        }} onEntrar={(solicitud) => {
          const palabras = solicitud.nombre.trim().split(/\s+/)
          const iniciales = (palabras[0][0] + (palabras.length > 1 ? palabras[palabras.length - 1][0] : '')).toUpperCase()
          setUsuarioDemo({ nombre: solicitud.nombre, iniciales, rol: 'Analista', correo: solicitud.correo })
          ir('casos')
        }} />
      : <Login expirada={vista.expirada} onEntrar={() => ir('casos')} />
  } else {
    const usuario = usuarioDemo || (pantalla === 'validacion' ? USUARIOS.diego : USUARIOS.ana)
    const activo = pantalla === 'factura' || pantalla === 'validacion' ? 'casos' : pantalla
    let pagina
    if (pantalla === 'administrador' && usuarioDemo?.esAdmin && import.meta.env.VITE_ACCESO_DEMO === 'true') {
      pagina = <AccesoDemo panelAdmin correoAdministrador={usuarioDemo.correo} onVolver={() => ir('casos')} />
    } else if (pantalla === 'casos') {
      pagina = <Bandeja variante={vista.variante} abrirCaso={abrirCaso} ir={ir} setVariante={(v) => setVista({ ...vista, variante: v })} />
      } else if (pantalla === 'asistente') {
      pagina = <Asistente />
    } else if (pantalla === 'subir') {
      pagina = <Subir ir={ir} iniciar={iniciar} />
    } else if (pantalla === 'factura' && CASOS_REALES) {
      pagina = <DetalleReal key={vista.caso} casoId={vista.caso} ir={ir} toast={setToast} />
    } else if (pantalla === 'factura') {
      const c = vista.caso === 'F-1043' ? NUEVO : caso(vista.caso)
      pagina = (
        <DetalleFactura
          key={`${c.id}-${vista.variante}`}
          caso={c}
          variante={vista.variante}
          setVariante={(v) => setVista({ ...vista, variante: v })}
          usuario={usuario}
          ir={ir}
          toast={setToast}
        />
      )
    } else if (pantalla === 'validacion') {
      pagina = <Validacion caso={caso(vista.caso)} ir={ir} toast={setToast} />
    } else {
      pagina = <Bitacora toast={setToast} />
    }
    contenido = (
      <Shell activo={activo} usuario={usuario} ir={ir} onSalir={() => { setUsuarioDemo(null); setChatAbierto(false); setVista({ pantalla: 'login' }) }}>
        <div className={`espacio-trabajo ${chatAbierto ? 'chat-abierto' : ''}`}>
          <div className="pagina-trabajo">{pagina}</div>
          <aside className="chat-panel" hidden={!chatAbierto} aria-label="Panel del asistente">
            <div className="chat-panel-barra">
              <div><Bot size={22} /><strong>Asistente</strong><span>{vista.caso ? 'Caso ' + vista.caso : 'Data Steward'}</span></div>
              <button className="btn btn-icono" aria-label="Cerrar asistente" onClick={() => setChatAbierto(false)}><X size={19} /></button>
            </div>
            <Asistente key={vista.caso || 'general'} casoId={vista.caso || null} />
          </aside>
        </div>
            </Shell>
    )
  }

  return (
    <>
      {contenido}
      <button className="tema-boton" aria-label={tema === 'oscuro' ? 'Activar modo claro' : 'Activar modo oscuro'} onClick={() => setTema(tema === 'oscuro' ? 'claro' : 'oscuro')}>
        {tema === 'oscuro' ? <Sun size={19} /> : <Moon size={19} />}
      </button>
      {pantalla !== 'login' && !chatAbierto && <button className="chat-lanzador" aria-label="Abrir asistente" aria-expanded={false} onClick={() => setChatAbierto(true)}><Bot size={23} /><span>Asistente</span></button>}
      <Toast toast={toast} onCerrar={cerrarToast} />
      {!CASOS_REALES && import.meta.env.VITE_ACCESO_DEMO !== 'true' && !chatAbierto && <div className="demo">
        {menu && (
          <div className="demo-menu">
            {DEMO.map(([grupo, items]) => (
              <div key={grupo}>
                <h5>{grupo}</h5>
                {items.map(([texto, v]) => (
                  <button key={texto} onClick={() => { setVista(v); setMenu(false); window.scrollTo(0, 0) }}>{texto}</button>
                ))}
              </div>
            ))}
          </div>
        )}
        <button className="demo-btn" onClick={() => setMenu((m) => !m)}><LayoutGrid size={14} />Pantallas</button>
      </div>}
    </>
  )
}
