import { useEffect, useState } from 'react'
import { Bell, ShieldCheck, UserPlus, Clock, Check, X, ArrowLeft, Search, LogOut } from 'lucide-react'
import { Logo } from '../components.jsx'
import './AccesoDemo.css'

const CLAVE = 'dsa-accesos-demo-v1'
const ETIQUETAS = { pendiente: 'Pendiente', aprobado: 'Aprobado', rechazado: 'Rechazado' }
const correoNormal = (valor) => valor.trim().toLowerCase()
function leer() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE) || '[]')
    return Array.isArray(datos) ? datos.filter(d => d && typeof d.id === 'string' && typeof d.correo === 'string' && ETIQUETAS[d.estado]) : []
  } catch { return [] }
}

export default function AccesoDemo({ onEntrar, onEntrarAdmin, panelAdmin = false, correoAdministrador = '', onVolver }) {
  const [vista, setVista] = useState(panelAdmin ? 'admin' : 'ingreso')
  const administrador = correoAdministrador || 'Administrador de demostración'
  const [correoAdmin, setCorreoAdmin] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [solicitudes, setSolicitudes] = useState(leer)
  const [correo, setCorreo] = useState('')
  const [nombre, setNombre] = useState('')
  const [area, setArea] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [filtro, setFiltro] = useState('pendiente')
  const [seleccionada, setSeleccionada] = useState(null)
  const [motivo, setMotivo] = useState('')
  const [confirmada, setConfirmada] = useState('')
  useEffect(() => {
    const sincronizar = (e) => { if (e.key === CLAVE || e.key === null) setSolicitudes(leer()) }
    window.addEventListener('storage', sincronizar)
    return () => window.removeEventListener('storage', sincronizar)
  }, [])
  function guardar(nuevas) {
    try { localStorage.setItem(CLAVE, JSON.stringify(nuevas)); setSolicitudes(nuevas); return true }
    catch { setMensaje('No pudimos guardar la demostración. Permite el almacenamiento del navegador e inténtalo otra vez.'); return false }
  }
  function cambiar(v) { setVista(v); setMensaje(''); setSeleccionada(null); setMotivo(''); setConfirmada('') }
  function registrar(e) {
    e.preventDefault()
    const email = correoNormal(correo)
    if (!nombre.trim() || !area.trim()) { setMensaje('Escribe tu nombre y área.'); return }
    const existentes = leer()
    const existente = existentes.find(s => s.correo === email)
    if (existente) {
      setSolicitudes(existentes)
      setMensaje(`Este correo ya tiene una solicitud: ${ETIQUETAS[existente.estado].toLowerCase()}. Puedes consultar su estado al iniciar sesión.`)
      return
    }
    if (guardar([{ id: crypto.randomUUID(), nombre: nombre.trim(), correo: email, area: area.trim(), estado: 'pendiente', fecha: new Date().toISOString(), rol: 'Analista', motivo: '' }, ...existentes])) {
      setVista('estado'); setMensaje('Solicitud enviada. El administrador ya tiene una notificación en su bandeja de demostración.')
    }
  }
  function ingresar(e) {
    e.preventDefault()
    const datos = leer()
    setSolicitudes(datos)
    const solicitud = datos.find(s => s.correo === correoNormal(correo))
    if (!solicitud) { setMensaje('Este correo aún no tiene acceso. Primero envía una solicitud.'); return }
    if (solicitud.estado === 'aprobado') { onEntrar(solicitud); return }
    setVista('estado'); setMensaje('')
  }
  function entrarAprobado() {
    const solicitud = leer().find(s => s.correo === correoNormal(correo))
    if (solicitud?.estado === 'aprobado') onEntrar(solicitud)
    else { setSolicitudes(leer()); setVista('ingreso'); setMensaje('Tu solicitud debe estar aprobada para entrar.') }
  }
  function resolver(estado) {
    if (estado === 'rechazado' && !motivo.trim()) { setMensaje('Escribe el motivo del rechazo.'); return }
    const datos = leer()
    const solicitud = datos.find(s => s.id === seleccionada)
    if (!solicitud || solicitud.estado !== 'pendiente') { setSolicitudes(datos); setSeleccionada(null); setMensaje('La solicitud ya fue atendida en otra pestaña.'); return }
    if (guardar(datos.map(s => s.id === seleccionada ? { ...s, estado, motivo: motivo.trim(), resueltoEn: new Date().toISOString(), revisadoPor: administrador } : s))) {
      setMensaje(`Solicitud de ${solicitud.nombre}: ${ETIQUETAS[estado].toLowerCase()}.`); setSeleccionada(null); setMotivo('')
    }
  }
  const pendientes = solicitudes.filter(s => s.estado === 'pendiente').length
  const actual = solicitudes.find(s => s.correo === correoNormal(correo))
  const detalle = solicitudes.find(s => s.id === seleccionada)
  const visibles = solicitudes.filter(s => (filtro === 'todos' || s.estado === filtro) && [s.nombre, s.correo, s.area].some(v => v.toLowerCase().includes(busqueda.trim().toLowerCase())))
  return (
    <main className={`acceso-demo ${panelAdmin ? 'acceso-integrado' : ''}`}>
      {!panelAdmin && <header className="acceso-cabecera"><div className="acceso-marca"><Logo size={40} /><strong>Data Steward</strong></div><span className="acceso-sello">Demostración · acceso simulado</span></header>}
      <p className="acceso-aviso">Prototipo para mostrar la aprobación de usuarios. No autentica identidades ni envía correos. Usa datos ficticios.</p>
      {vista === 'admin' ? <section className="acceso-admin" aria-label="Administración de accesos">
        <div className="acceso-admin-sesion"><span className="acceso-admin-avatar"><ShieldCheck size={24} /></span><div><strong>Administrador de accesos</strong><span>{administrador}</span></div><button className="btn" onClick={onVolver}><LogOut size={16} />Volver a casos</button></div>
        <div className="acceso-titulo"><div><p className="acceso-eyebrow">Administración de demostración</p><h1>Solicitudes de acceso</h1><p>Revisa quién solicita entrar y decide su acceso de prueba.</p></div><button className="btn" onClick={onVolver}><ArrowLeft size={17} />Volver a casos</button></div>
        <div className="acceso-resumen" role="status"><Bell size={22} /><strong>{pendientes}</strong> {pendientes === 1 ? 'solicitud pendiente' : 'solicitudes pendientes'}</div>
        <div className="acceso-estadisticas" aria-label="Resumen de accesos">{[['Registradas', solicitudes.length], ['Aprobadas', solicitudes.filter(s => s.estado === 'aprobado').length], ['Rechazadas', solicitudes.filter(s => s.estado === 'rechazado').length]].map(([texto, numero]) => <div key={texto}><span>{texto}</span><strong>{numero}</strong></div>)}</div>
        <label className="acceso-busqueda"><Search size={18} /><input aria-label="Buscar solicitudes" placeholder="Buscar por nombre, correo o área" value={busqueda} onChange={e => setBusqueda(e.target.value)} /></label>
        <label className="acceso-filtro">Mostrar<select value={filtro} onChange={e => setFiltro(e.target.value)}><option value="pendiente">Pendientes</option><option value="aprobado">Aprobadas</option><option value="rechazado">Rechazadas</option><option value="todos">Todas</option></select></label>
        {mensaje && <p role="status" className="acceso-mensaje">{mensaje}</p>}
        <div className="acceso-lista">{visibles.length === 0 ? <div className="acceso-vacio"><ShieldCheck size={36} /><h2>Sin solicitudes {filtro === 'pendiente' ? 'pendientes' : 'en esta vista'}</h2><p>Las solicitudes nuevas aparecerán aquí automáticamente, incluso si se registran en otra pestaña de este navegador.</p></div> : visibles.map(s => <article className="acceso-solicitud" key={s.id}>
          <div><h2>{s.nombre}</h2><p>{s.correo}</p><p>{s.area} · {new Date(s.fecha).toLocaleString('es-MX')}</p><span className={`acceso-estado ${s.estado}`}>{ETIQUETAS[s.estado]}</span>{s.motivo && <p>Motivo: {s.motivo}</p>}{s.resueltoEn && <p className="acceso-traza">Revisado por {s.revisadoPor || 'Administración de demostración'} · {new Date(s.resueltoEn).toLocaleString('es-MX')}</p>}</div>
          {s.estado === 'pendiente' && <button className="btn" onClick={() => { setSeleccionada(s.id); setMotivo(''); setMensaje('') }}>Revisar solicitud de {s.nombre}</button>}
        </article>)}</div>
        {detalle?.estado === 'pendiente' && <section className="acceso-revision" aria-label="Revisar solicitud"><h2>Revisar a {detalle.nombre}</h2><p>El acceso propuesto es de <strong>Analista</strong>. No otorga permisos de administrador.</p><label>Motivo (obligatorio si rechazas)<textarea maxLength={500} value={motivo} onChange={e => setMotivo(e.target.value)} rows={3} /></label><div className="acceso-botones"><button className="btn btn-primario" onClick={() => resolver('aprobado')}><Check size={17} />Aprobar acceso</button><button className="btn" onClick={() => resolver('rechazado')}><X size={17} />Rechazar solicitud</button><button className="btn" onClick={() => setSeleccionada(null)}>Cancelar</button></div></section>}
        <footer className="acceso-reinicio">{confirmada ? <><p>¿Borrar todas las solicitudes de esta demostración?</p><button className="btn" onClick={() => { if (guardar([])) { setConfirmada(''); setMensaje('Demostración reiniciada.') } }}>Confirmar reinicio</button><button className="btn" onClick={() => setConfirmada('')}>Conservar solicitudes</button></> : <button className="link" onClick={() => setConfirmada('si')}>Reiniciar datos de demostración</button>}</footer>
      </section> : <section className="acceso-tarjeta">
        {vista === 'admin-login' ? <><ShieldCheck size={32} /><h1>Inicia sesión como administrador</h1><p>Para esta demostración, ingresa cualquier correo válido. No necesitas contraseña.</p><form onSubmit={(e) => { e.preventDefault(); onEntrarAdmin(correoNormal(correoAdmin)) }}><label>Correo del administrador<input type="email" required maxLength={160} autoComplete="email" value={correoAdmin} onChange={e => setCorreoAdmin(e.target.value)} /></label><button type="submit" className="btn btn-primario">Iniciar sesión como administrador</button></form><button className="link" onClick={() => cambiar('ingreso')}>Volver al ingreso</button></> : vista === 'registro' ? <><UserPlus size={32} /><h1>Solicita tu acceso</h1><p>Tu registro quedará pendiente hasta que el administrador lo apruebe.</p><form onSubmit={registrar}><label>Nombre completo<input value={nombre} onChange={e => setNombre(e.target.value)} required maxLength={100} autoComplete="name" /></label><label>Correo<input type="email" value={correo} onChange={e => setCorreo(e.target.value)} required maxLength={160} autoComplete="email" /></label><label>Área o equipo<input value={area} onChange={e => setArea(e.target.value)} required maxLength={100} /></label><button className="btn btn-primario" type="submit">Enviar solicitud</button></form><button className="link" onClick={() => cambiar('ingreso')}>Ya solicité acceso</button></> : vista === 'estado' ? <><Clock size={32} /><h1>{actual?.estado === 'aprobado' ? 'Tu acceso fue aprobado' : actual?.estado === 'rechazado' ? 'Solicitud no aprobada' : 'Tu solicitud está pendiente'}</h1><p>{correoNormal(correo)}</p><p>{actual?.estado === 'aprobado' ? 'Ya puedes entrar a la demostración con este correo.' : actual?.estado === 'rechazado' ? 'El administrador revisó tu solicitud. Contacta al equipo para aclaraciones.' : 'Todavía no puedes entrar. Cuando el administrador decida, este estado se actualizará automáticamente.'}</p>{actual?.motivo && <p className="acceso-mensaje">Motivo: {actual.motivo}</p>}{actual?.estado === 'aprobado' && <button className="btn btn-primario" onClick={entrarAprobado}>Entrar a la demostración</button>}<button className="link" onClick={() => cambiar('ingreso')}>Volver al ingreso</button></> : <><ShieldCheck size={32} /><h1>Inicia sesión</h1><p>Para entrar necesitas una solicitud aprobada por el administrador.</p><form onSubmit={ingresar}><label>Correo<input type="email" required value={correo} onChange={e => setCorreo(e.target.value)} autoComplete="email" /></label><button type="submit" className="btn btn-primario">Iniciar sesión</button></form><button className="link" onClick={() => cambiar('registro')}>Solicitar acceso</button></>}
        {mensaje && <p className="acceso-mensaje" role="status">{mensaje}</p>}
        {vista !== 'admin-login' && <><hr /><button className="btn acceso-admin-entrada" onClick={() => cambiar('admin-login')}><ShieldCheck size={17} />Soy administrador</button></>}
      </section>}
    </main>
  )
}
