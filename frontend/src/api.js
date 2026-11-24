/**
 * Cliente de API para el frontend del Data Steward.
 * Consume los endpoints REST de FastAPI interceptados por MSW en desarrollo.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export async function apiFetch(endpoint, opciones = {}) {
  const resp = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...opciones.headers,
    },
    ...opciones,
  })
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detalle: resp.statusText }))
    throw new Error(error.detalle || error.message || `Error ${resp.status}`)
  }
  return resp.json()
}

// --- Endpoints de Casos ---

export async function obtenerCasos(filtros = {}) {
  const params = new URLSearchParams()
  if (filtros.tipo) params.append('tipo', filtros.tipo)
  if (filtros.estado) params.append('estado', filtros.estado)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/casos${qs}`)
}

export async function obtenerDetalleCaso(casoId) {
  return apiFetch(`/api/casos/${casoId}`)
}

export async function crearCaso(datos) {
  return apiFetch('/api/casos', {
    method: 'POST',
    body: JSON.stringify(datos),
  })
}

export async function obtenerUrlSubida(nombreArchivo, tipoDocumento) {
  return apiFetch('/api/casos/url-subida', {
    method: 'POST',
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_documento: tipoDocumento }),
  })
}

export async function registrarDecisionCaso(casoId, decision) {
  return apiFetch(`/api/casos/${casoId}/decision`, {
    method: 'POST',
    body: JSON.stringify(decision),
  })
}

// --- Endpoints de Bitácora ---

export async function obtenerBitacora(filtros = {}) {
  const params = new URLSearchParams()
  if (filtros.caso) params.append('caso', filtros.caso)
  if (filtros.quien) params.append('quien', filtros.quien)
  if (filtros.accion) params.append('accion', filtros.accion)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/bitacora${qs}`)
}
