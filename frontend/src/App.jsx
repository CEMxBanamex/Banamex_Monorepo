import { useCallback, useState } from 'react'
import { LayoutGrid } from 'lucide-react'
import { Shell, Toast } from './components.jsx'
import { USUARIOS, CASOS } from './data.js'
import Login from './screens/Login.jsx'
import Bandeja from './screens/Bandeja.jsx'
import Subir from './screens/Subir.jsx'
import DetalleFactura from './screens/Detalle.jsx'
import Validacion from './screens/Validacion.jsx'
import Bitacora from './screens/Bitacora.jsx'

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
  const [toast, setToast] = useState(null)
  const [menu, setMenu] = useState(false)
  const cerrarToast = useCallback(() => setToast(null), [])

  const ir = (pantalla) => { setVista({ pantalla, variante: 'normal' }); window.scrollTo(0, 0) }
  const abrirCaso = (c) => {
    setVista(c.tipo === 'Factura' || c.variante === 'error'
      ? { pantalla: 'factura', caso: c.id, variante: c.variante || 'normal' }
      : { pantalla: 'validacion', caso: c.id })
    window.scrollTo(0, 0)
  }
  const iniciar = (tipo) => {
    setVista(tipo === 'factura'
      ? { pantalla: 'factura', caso: 'F-1043', variante: 'procesando' }
      : { pantalla: 'validacion', caso: 'V-0207' })
    window.scrollTo(0, 0)
  }

  const { pantalla } = vista
  let contenido
  if (pantalla === 'login') {
    contenido = <Login expirada={vista.expirada} onEntrar={() => ir('casos')} />
  } else {
    const usuario = pantalla === 'validacion' ? USUARIOS.diego : USUARIOS.ana
    const activo = pantalla === 'factura' || pantalla === 'validacion' ? 'casos' : pantalla
    let pagina
    if (pantalla === 'casos') {
      pagina = <Bandeja variante={vista.variante} abrirCaso={abrirCaso} ir={ir} setVariante={(v) => setVista({ ...vista, variante: v })} />
    } else if (pantalla === 'subir') {
      pagina = <Subir ir={ir} iniciar={iniciar} />
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
      <Shell activo={activo} usuario={usuario} ir={ir} onSalir={() => setVista({ pantalla: 'login' })}>
        {pagina}
      </Shell>
    )
  }

  return (
    <>
      {contenido}
      <Toast toast={toast} onCerrar={cerrarToast} />
      <div className="demo">
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
      </div>
    </>
  )
}
