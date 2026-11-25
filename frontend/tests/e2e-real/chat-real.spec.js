import { test, expect } from '@playwright/test'

for (const contextual of [false, true]) {
  test(contextual ? 'caso sin MSW y con historial' : 'chat global sin MSW y con historial', async ({ page, request }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    if (contextual) {
      await page.getByRole('row').filter({ hasText: 'F-1042' }).click()
    } else {
      await page.getByRole('button', { name: 'Asistente', exact: true }).click()
    }
    const panel = page.getByRole('region', { name: 'Asistente de consultas' })
    const creada = page.waitForResponse(r =>
      r.url() === 'http://127.0.0.1:8022/api/chat/conversaciones' && r.request().method() === 'POST',
    )
    await panel.getByLabel('Tu pregunta').fill('Hola')
    await panel.getByRole('button', { name: 'Enviar', exact: true }).click()
    const apertura = await creada
    expect(apertura.status()).toBe(201)
    const conversacion = await apertura.json()
    await expect(panel.locator('.asistente-respuesta')).toContainText('demostración')
    await expect(panel.getByRole('button', { name: /2 pasos/ })).toBeVisible()
    await expect(panel.getByRole('button', { name: 'Enviar', exact: true })).toBeDisabled()
    const ruta = `http://127.0.0.1:8022/api/chat/conversaciones/${conversacion.id}/mensajes`
    const historial = await request.get(ruta)
    expect(historial.status()).toBe(200)
    const mensajes = (await historial.json()).mensajes
    expect(mensajes.map(m => m.rol)).toEqual(['usuario', 'asistente'])
    expect(mensajes[1].pasos).toHaveLength(4)
    expect(conversacion.caso_id).toBe(contextual ? 'F-1042' : null)
    await panel.getByLabel('Tu pregunta').fill('Hola otra vez')
    await panel.getByRole('button', { name: 'Enviar', exact: true }).click()
    await expect(panel.locator('.asistente-respuesta')).toHaveCount(2)
    const continuacion = await request.get(ruta)
    expect((await continuacion.json()).mensajes).toHaveLength(4)
  })
}
