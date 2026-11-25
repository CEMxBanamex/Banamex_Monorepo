import { test, expect } from '@playwright/test'

for (const caso of [false, true]) {
  test(caso ? 'caso con evidencia real y persistencia' : 'gobernanza real con pasos y persistencia', async ({ page, request }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    if (caso) {
      await page.getByRole('row').filter({ hasText: 'F-1042' }).click()
      await page.getByRole('button', { name: 'Abrir asistente' }).click()
    } else {
      await page.getByRole('button', { name: 'Abrir asistente', exact: true }).click()
    }
    const panel = page.getByRole('region', { name: 'Asistente de consultas' })
    const apertura = page.waitForResponse(r => r.url().endsWith('/api/chat/conversaciones') && r.request().method() === 'POST')
    const transmision = page.waitForResponse(r => r.url().endsWith('/api/chat/stream') && r.request().method() === 'POST')
    const pregunta = caso ? '¿Por qué se rechazó la factura F-1042?' : 'Consulta las reglas de calidad de datos'
    await panel.getByLabel('Tu pregunta').fill(pregunta)
    await panel.getByRole('button', { name: 'Enviar', exact: true }).click()
    const creada = await apertura
    expect(creada.status()).toBe(201)
    const conversacion = await creada.json()
    const respuesta = await transmision
    expect(respuesta.status()).toBe(200)
    const salida = panel.locator('.asistente-respuesta')
    await expect(salida).toContainText(caso ? 'R-014' : 'Reglas evaluadas:')
    await expect(salida).not.toContainText('simulación')
    await expect(salida).not.toContainText('atenci?n')
    const textoSSE = await respuesta.text()
    const eventos = textoSSE.trim().split(/\r?\n\r?\n/).map(b => {
      const linea = b.split(/\r?\n/).find(l => l.startsWith('data:'))
      return { nombre: b.split(/\r?\n/).find(l => l.startsWith('event:'))?.slice(6).trim(), datos: JSON.parse(linea.slice(5).trim()) }
    })
    expect(eventos.filter(e => e.nombre === 'paso')).toHaveLength(4)
    const final = eventos.find(e => e.nombre === 'respuesta').datos
    expect(final.simulado).toBe(false)
    expect(final.fuentes).toContain(caso ? 'consultar_caso' : 'consultar_calidad')
    await panel.getByRole('button', { name: /2 pasos/ }).click()
    await expect(panel.locator('.asistente-pasos')).toBeVisible()
    await expect(panel.locator('.asistente-pasos li')).toHaveCount(2)
    if (caso) {
      await expect(salida).toContainText('400.00')
      await expect(salida).toContainText('página 1, total')
      expect(final.caso_id).toBe('F-1042')
    }
    const historial = await request.get(`/api/chat/conversaciones/${conversacion.id}/mensajes`)
    expect(historial.status()).toBe(200)
    const mensajes = (await historial.json()).mensajes
    expect(mensajes.map(m => m.rol)).toEqual(['usuario', 'asistente'])
    expect(mensajes[0].contenido).toBe(pregunta)
    expect(mensajes[1].contenido).toBe(final.respuesta)
    expect(mensajes[1].pasos).toHaveLength(4)
  })
}
