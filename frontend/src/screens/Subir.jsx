import { useEffect, useRef, useState } from 'react'
import {
  FlaskConical, ReceiptText, Table, CircleCheck, Upload, File, Image,
  X, Check, CircleAlert, Play,
} from 'lucide-react'

const ADMITIDOS = ['pdf', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'csv', 'md', 'txt']
const INICIALES = [
  { nombre: 'factura_1043.pdf', tam: '1.2 MB', progreso: 100 },
  { nombre: 'factura_1043_anexo.png', tam: '3.4 MB', progreso: 64 },
  { nombre: 'contrato_proveedor.docx', tam: '220 KB', error: 'tipo' },
  { nombre: 'estado_cuenta_anual.pdf', tam: '48 MB', error: 'tamano' },
  { nombre: 'factura_1044.jpg', tam: '2.1 MB', progreso: 38, error: 'subida' },
]
const ERRORES = {
  tipo: 'Este tipo de archivo no está admitido. Usa PDF, imagen, Excel, CSV, Markdown o texto',
  tamano: 'El archivo supera el máximo de 20 MB. Divide el archivo o reduce su tamaño',
  subida: 'No se pudo subir',
}

function tamano(bytes) {
  return bytes > 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1e3))} KB`
}

export default function Subir({ ir, iniciar }) {
  const [tipo, setTipo] = useState('factura')
  const [archivos, setArchivos] = useState(INICIALES)
  const [arrastrando, setArrastrando] = useState(false)
  const input = useRef(null)

  // Simula el avance de las subidas en curso.
  useEffect(() => {
    const t = setInterval(() => {
      setArchivos((as) => as.map((a) =>
        !a.error && a.progreso < 100 ? { ...a, progreso: Math.min(100, a.progreso + 6) } : a))
    }, 400)
    return () => clearInterval(t)
  }, [])

  function agregar(lista) {
    const nuevos = [...lista].map((f) => {
      const ext = f.name.split('.').pop().toLowerCase()
      const error = !ADMITIDOS.includes(ext) ? 'tipo' : f.size > 20e6 ? 'tamano' : null
      return { nombre: f.name, tam: tamano(f.size), progreso: error ? 0 : 5, error }
    })
    setArchivos((as) => [...as, ...nuevos])
  }

  const reintentar = (i) => setArchivos((as) => as.map((a, j) => (j === i ? { ...a, error: null, progreso: 5 } : a)))
  const listos = archivos.some((a) => !a.error && a.progreso === 100)

  return (
    <main className="main">
      <div className="subir">
        <div className="cabecera">
          <div>
            <h1>Subir caso</h1>
            <p>Elige el tipo de revisión y agrega los archivos.</p>
          </div>
          <span className="badge b-neutro"><FlaskConical size={16} />Estás usando datos de prueba</span>
        </div>

        <div className="paso"><span className="n">1</span>Tipo de revisión</div>
        <div className="opciones">
          {[
            ['factura', ReceiptText, 'Revisión de factura', 'Extrae los datos de una factura y revisa sus reglas.'],
            ['politicas', Table, 'Validación con políticas', 'Valida documentos o registros contra políticas internas.'],
          ].map(([id, Icono, titulo, texto]) => (
            <button key={id} className={`opcion ${tipo === id ? 'sel' : ''}`} onClick={() => setTipo(id)} aria-pressed={tipo === id}>
              <span className="ico-cuad"><Icono size={26} /></span>
              <div><strong>{titulo}</strong><span>{texto}</span></div>
              {tipo === id && <CircleCheck className="check" size={26} fill="var(--marca)" color="#fff" />}
            </button>
          ))}
        </div>

        <div className="paso"><span className="n">2</span>Archivos</div>
        <div
          className={`zona ${arrastrando ? 'arrastrando' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => { e.preventDefault(); setArrastrando(false); agregar(e.dataTransfer.files) }}
        >
          <span className="ico-circ" style={{ width: 76, height: 76 }}><Upload size={30} /></span>
          <div className="titulo">Arrastra y suelta tus archivos aquí</div>
          <div className="muted">o</div>
          <button className="btn" style={{ marginTop: 12 }} onClick={() => input.current.click()}>Elegir archivo</button>
          <input ref={input} type="file" multiple hidden onChange={(e) => { agregar(e.target.files); e.target.value = '' }} />
          <div className="tipos">
            Tipos admitidos:
            {['.pdf', '.jpg', '.png', '.xls', '.xlsx', '.csv', '.md', 'texto'].map((t) => <code key={t}>{t}</code>)}
          </div>
          <div className="muted" style={{ marginTop: 14, fontSize: 14 }}>Tamaño máximo por archivo: 20 MB</div>
        </div>

        {archivos.length > 0 && (
          <div className="archivos">
            {archivos.map((a, i) => {
              const esImagen = /\.(png|jpe?g)$/i.test(a.nombre)
              const Icono = esImagen ? Image : File
              const fallo = a.error === 'tipo' || a.error === 'tamano'
              const colorBarra = a.error ? 'var(--error)' : a.progreso === 100 ? 'var(--exito)' : 'var(--info)'
              return (
                <div key={a.nombre + i} className={`archivo ${a.error ? 'err' : ''}`}>
                  <Icono size={24} color={a.error ? 'var(--error)' : 'var(--texto-2)'} />
                  <div className="info">
                    <div className="fila">
                      <span className="nombre">{a.nombre}</span>
                      <span className="muted num">{a.tam}{!fallo && ` · ${a.progreso} %`}</span>
                    </div>
                    {fallo ? (
                      <div className="estado-arch" style={{ color: 'var(--error)', marginTop: 6 }}>
                        <CircleAlert size={16} />{ERRORES[a.error]}
                      </div>
                    ) : (
                      <>
                        <div className="barra"><div style={{ width: `${a.progreso}%`, background: colorBarra }} /></div>
                        {a.error === 'subida' ? (
                          <div className="fila" style={{ alignItems: 'center' }}>
                            <span className="estado-arch" style={{ color: 'var(--error)' }}><CircleAlert size={16} />{ERRORES.subida}</span>
                            <button className="btn" style={{ minHeight: 36 }} onClick={() => reintentar(i)}>Reintentar</button>
                          </div>
                        ) : a.progreso === 100 ? (
                          <span className="estado-arch" style={{ color: 'var(--exito)' }}><Check size={16} />Listo</span>
                        ) : (
                          <span className="estado-arch" style={{ color: 'var(--info)', fontWeight: 500 }}>Subiendo…</span>
                        )}
                      </>
                    )}
                  </div>
                  <button className="x" aria-label={`Quitar ${a.nombre}`} onClick={() => setArchivos((as) => as.filter((_, j) => j !== i))}>
                    <X size={20} />
                  </button>
                </div>
              )
            })}
          </div>
        )}

        <p style={{ margin: '24px 0 10px', fontWeight: 600 }}>O pega el texto <span className="muted" style={{ fontWeight: 400 }}>(opcional)</span></p>
        <textarea className="area" placeholder="Pega aquí el contenido del documento o registro" />

        <div className="acciones-fin">
          <button className="btn" onClick={() => ir('casos')}>Cancelar</button>
          <button className="btn btn-primario" disabled={!listos} onClick={() => iniciar(tipo)}>
            <Play size={18} />Iniciar revisión
          </button>
        </div>
      </div>
    </main>
  )
}
