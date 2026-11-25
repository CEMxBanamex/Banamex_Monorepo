export const CHAT_REAL = import.meta.env.VITE_CHAT_REAL === 'true'
export const CHAT_API = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
