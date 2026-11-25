import { test, expect } from '@playwright/test'

async function contraste(elemento, fondo = elemento) {
  const color = await elemento.evaluate(e => getComputedStyle(e).color)
  const background = await fondo.evaluate(e => getComputedStyle(e).backgroundColor)
  const luz = texto => {
    const rgb = texto.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => {
      const n = v / 255
      return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4
    })
    return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722
  }
  const a = luz(color), b = luz(background)
  expect((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)).toBeGreaterThanOrEqual(4.5)
}

for (const ancho of [1280, 390]) {
test(`estados legibles y acciones sin solapamiento, ancho ${ancho}`, async ({ page }) => {
  await page.setViewportSize({ width: ancho, height: 800 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('button', { name: 'Activar modo oscuro' }).click()
  await page.getByRole('button', { name: 'Subir caso', exact: true }).first().click()
  const seleccion = page.locator('.opcion.sel')
  await contraste(seleccion.locator('strong'), seleccion)
  await contraste(seleccion.locator('span').last(), seleccion)
  for (const fila of await page.locator('.archivo.err').all()) {
    await contraste(fila.locator('.nombre'), fila)
    await contraste(fila.locator('.estado-arch'), fila)
  }
  await page.getByRole('button', { name: 'Iniciar revisión', exact: true }).scrollIntoViewIfNeeded()
  const flotante = await page.getByRole('button', { name: 'Abrir asistente' }).boundingBox()
  const accion = await page.getByRole('button', { name: 'Iniciar revisión', exact: true }).boundingBox()
  expect(flotante.y + flotante.height <= accion.y || flotante.x + flotante.width <= accion.x || flotante.x >= accion.x + accion.width).toBe(true)
  await page.getByRole('button', { name: 'Casos', exact: true }).click()
  await page.getByRole('row').filter({ hasText: 'F-1042' }).click()
  const campo = page.locator('input.dudoso').first()
  await contraste(campo)
  for (const boton of await page.locator('.barra-acciones button').all()) {
    if (!await boton.isVisible()) continue
    await boton.scrollIntoViewIfNeeded()
    const a = await boton.boundingBox()
    const b = await page.getByRole('button', { name: 'Abrir asistente' }).boundingBox()
    expect(b.y + b.height <= a.y || b.x + b.width <= a.x || b.x >= a.x + a.width || b.y >= a.y + a.height).toBe(true)
  }
  await page.screenshot({ path: 'test-results/contraste-caso-oscuro.png', fullPage: true })
})
}
