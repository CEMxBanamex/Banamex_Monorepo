import { API_BASE_URL } from './api.js'

export const CHAT_REAL = import.meta.env.VITE_CHAT_REAL === 'true'
// Misma URL que el resto de la API (en *.vercel.app, el mismo origen; ver api.js).
export const CHAT_API = API_BASE_URL
