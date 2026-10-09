const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  fs.mkdirSync('evidence', { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(45000);
  const base = 'http://127.0.0.1:8069';
  try {
    await page.goto(base + '/web/login');
    await page.locator('input[name="login"]').fill(process.env.INITIAL_ADMIN_LOGIN);
    await page.locator('input[name="password"]').fill(process.env.INITIAL_ADMIN_PASSWORD);
    await page.getByRole('button', { name: 'Log in', exact: true }).click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 90000 });
    const rpc = async (model, method, args, kwargs = {}) => {
      const response = await page.request.post(base + '/web/dataset/call_kw/' + model + '/' + method,
        { data: { jsonrpc: '2.0', method: 'call', params: { model, method, args, kwargs }, id: 1 } });
      const body = await response.json();
      if (body.error) throw new Error(JSON.stringify(body.error));
      return body.result;
    };
    const action = async name => {
      const refs = await rpc('ir.model.data', 'search_read', [[['module', '=', 'auto_parts_dealer'], ['name', '=', name]]], { fields: ['res_id'] });
      assert.equal(refs.length, 1);
      await page.goto(base + '/odoo/action-' + refs[0].res_id);
    };
    await action('action_catalog_import');
    await page.getByRole('button', { name: 'New', exact: true }).click();
    await page.locator('[name="name"] input').fill('Browser acceptance — fictional catalog');
    await page.locator('input[type="file"]').setInputFiles('examples/catalog.csv');
    await page.getByRole('button', { name: 'Validate / Revalidate', exact: true }).click();
    await page.getByText('CREATE DEMO-OF-001', { exact: false }).waitFor();
    await page.screenshot({ path: 'evidence/catalog-review.png', fullPage: true });
    await page.getByRole('button', { name: 'Apply Reviewed Import', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Ok', exact: true }).click();
    await page.getByRole('tab', { name: 'Applied Products', exact: true }).waitFor();
    const batches = await rpc('ap.catalog.import', 'search_read', [[['name', '=', 'Browser acceptance — fictional catalog']]], { fields: ['state', 'row_count', 'product_ids'] });
    assert.equal(batches.length, 1); assert.equal(batches[0].state, 'applied'); assert.equal(batches[0].row_count, 2); assert.equal(batches[0].product_ids.length, 2);
    await page.reload();
    await page.getByRole('tab', { name: 'Applied Products', exact: true }).click();
    await page.screenshot({ path: 'evidence/catalog-applied.png', fullPage: true });
    await action('action_parts_catalog');
    await page.getByText('DEMO-OF-001', { exact: true }).waitFor();
    await page.screenshot({ path: 'evidence/parts-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: 'evidence/parts-mobile.png', fullPage: true });
    fs.writeFileSync('evidence/browser-result.json', JSON.stringify({ login: true, review: true, apply: true, persisted: true, products: 2 }, null, 2));
  } catch (error) {
    await page.screenshot({ path: 'evidence/browser-failure.png', fullPage: true }).catch(() => {});
    const body = await page.locator('body').innerText().catch(() => 'No body');
    fs.writeFileSync('evidence/browser-failure.txt', body);
    console.error(body);
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
