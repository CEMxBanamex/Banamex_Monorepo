import { test, expect } from '@playwright/test'

test('la rueda gira durante la subida y respeta movimiento reducido', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('navigation').getByRole('button', { name: 'Subir caso', exact: true }).click()
  const rueda = page.locator('.archivo .girando').first()
  await expect(rueda).toBeVisible()
  const antes = await rueda.evaluate(e => getComputedStyle(e).transform)
  await expect.poll(() => rueda.evaluate(e => getComputedStyle(e).transform)).not.toBe(antes)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(rueda).toHaveCSS('animation-name', 'none')
  await expect(page.getByText('Subiendo…').first()).toBeVisible()
})
