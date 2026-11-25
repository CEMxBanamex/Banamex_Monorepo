import { test, expect } from '@playwright/test'

const chat = (page) =>
  page.getByRole('region', { name: 'Asistente de consultas' })

async function enviar(page, mensaje) {
  const panel = chat(page)
  await panel.getByLabel('Tu pregunta').fill(mensaje)
  await panel.getByRole('button', {
    name: 'Enviar',
    exact: true,
  }).click()
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', {
    name: 'Iniciar sesión',
    exact: true,
  }).click()
  await page.getByRole('button', {
    name: 'Abrir asistente',
    exact: true,
  }).click()
})

test('muestra respuesta, actualiza pasos por id y despliega el resumen', async ({ page }) => {
  await enviar(page, 'Hola')
  const panel = chat(page)

  await expect(panel.locator('.asistente-respuesta'))
    .toContainText('respuesta simulada')

  const resumen = panel.getByRole('button', { name: /2 pasos/ })
  await expect(resumen).toHaveAttribute('aria-expanded', 'false')
  await resumen.click()
  await expect(resumen).toHaveAttribute('aria-expanded', 'true')

  await expect(panel.locator('.asistente-pasos li')).toHaveCount(2)
  await expect(panel.locator('.asistente-pasos li').nth(0))
    .toContainText('Completado')
  await expect(panel.locator('.asistente-pasos li').nth(1))
    .toContainText('Completado')

  await expect(panel.getByRole('region', {
    name: 'Fuentes de la respuesta',
  })).toHaveCount(0)
})

test('muestra fuentes cuando llegan en la respuesta', async ({ page }) => {
  await enviar(page, 'fuentes')

  await expect(chat(page).getByRole('region', {
    name: 'Fuentes de la respuesta',
  })).toContainText('Fuente ficticia para probar la pantalla')
})

test('permite recuperar la pregunta y continuar después de un error', async ({ page }) => {
  await enviar(page, 'error')
  const panel = chat(page)

  await expect(panel.getByRole('alert')).toContainText('Un paso falló')
  await panel.getByRole('button', {
    name: 'Recuperar pregunta',
  }).click()
  await expect(panel.getByLabel('Tu pregunta')).toHaveValue('error')

  await enviar(page, 'Hola')

  await expect(
    panel.locator('.asistente-turno').last()
      .locator('.asistente-respuesta'),
  ).toContainText('respuesta simulada')
})

test('cancela sin añadir una respuesta tardía y permite otra consulta', async ({ page }) => {
  await enviar(page, 'Cancelar esta consulta')
  const panel = chat(page)

  await panel.getByRole('button', {
    name: 'Cancelar',
    exact: true,
  }).click()

  await expect(panel.getByRole('alert'))
    .toContainText('Consulta cancelada')

  await enviar(page, 'Hola')

  await expect(
    panel.locator('.asistente-turno').last()
      .locator('.asistente-respuesta'),
  ).toContainText('respuesta simulada')

  await expect(
    panel.locator('.asistente-turno').first()
      .locator('.asistente-respuesta'),
  ).toHaveCount(0)
})

test('no permite enviar mensajes vacíos', async ({ page }) => {
  const panel = chat(page)
  const boton = panel.getByRole('button', {
    name: 'Enviar',
    exact: true,
  })

  await expect(boton).toBeDisabled()
  await panel.getByLabel('Tu pregunta').fill('   ')
  await expect(boton).toBeDisabled()
  await expect(panel.locator('.asistente-turno')).toHaveCount(0)
})

for (const ancho of [1280, 390]) {
  test('chat contextual con fuentes, ancho ' + ancho, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 800 })

    await page.getByRole('button', { name: 'Cerrar asistente' }).click()
    await page.getByRole('button', {
      name: 'Casos',
      exact: true,
    }).click()

    await page.getByRole('row').filter({
      hasText: 'F-1042',
    }).click()

    await page.getByRole('button', { name: 'Abrir asistente' }).click()
    const panel = chat(page)

    await expect(page.getByText('Caso F-1042', { exact: true })).toBeVisible()

    const solicitud = page.waitForRequest((r) =>
      r.url().endsWith('/api/chat/stream') &&
      r.method() === 'POST' &&
      r.postDataJSON()?.caso_id === 'F-1042',
    )

    await enviar(page, 'fuentes')
    await solicitud

    await expect(panel.locator('.asistente-respuesta'))
      .toContainText('caso F-1042')

    await expect(panel.getByRole('region', {
      name: 'Fuentes de la respuesta',
    })).toContainText('Fuente ficticia')
  })
}