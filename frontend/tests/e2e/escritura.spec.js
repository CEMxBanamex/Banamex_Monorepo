import { test, expect } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`escritura crece, se contrae y envía con Enter a ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('button', { name: 'Abrir asistente', exact: true }).click()
    const caja = page.getByLabel('Tu pregunta', { exact: true })
    const inicial = (await caja.boundingBox()).height
    const label = await page.locator('label[for="mensaje-asistente"]').boundingBox()
    expect((await caja.boundingBox()).y - label.y - label.height).toBeGreaterThanOrEqual(8)
    await caja.fill('Primera línea')
    await caja.press('Shift+Enter')
    await caja.press('Shift+Enter')
    await caja.press('Shift+Enter')
    await expect(caja).toHaveValue('Primera línea\n\n\n')
    expect((await caja.boundingBox()).height).toBeGreaterThan(inicial)
    await caja.fill(Array(25).fill('Texto de varias líneas').join('\n'))
    expect((await caja.boundingBox()).height).toBeLessThanOrEqual(180)
    await expect(caja).toHaveCSS('overflow-y', 'auto')
    await caja.fill('Hola')
    expect((await caja.boundingBox()).height).toBe(inicial)
    await caja.press('Enter')
    await expect(page.locator('.asistente-pregunta')).toHaveCount(1)
    await expect(page.locator('.asistente-pregunta')).toContainText('Hola')
    await expect(caja).toHaveValue('')
    await expect(page.locator('.asistente-respuesta')).toContainText('respuesta simulada')
    await caja.press('Enter')
    await expect(page.locator('.asistente-pregunta')).toHaveCount(1)
  })
}
