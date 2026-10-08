const {test, expect} = require('@playwright/test');

test('saved graph story advances in both directions without clicking controls', async ({page}) => {
  await page.setViewportSize({width:1280,height:900});
  await page.goto('/');
  await page.waitForFunction(() => window.researchReady && window.researchNetworkReady);
  await expect(page.locator('.network-chapter')).toHaveCount(4);
  await expect(page.locator('.walk-portrait')).toHaveCount(7);
  for (const index of [0,1,2,3,2,1,0]) {
    await page.evaluate(index => {
      const chapter = document.querySelectorAll('.network-chapter')[index];
      window.scrollTo(0, scrollY + chapter.getBoundingClientRect().top - innerHeight * .35);
    }, index);
    await expect(page.locator('#network-story')).toHaveAttribute('data-active', String(index));
    await expect(page.locator('#network-map .network-links path')).toHaveCount(3);
    await expect(page.locator('#network-current')).toBeInViewport();
  }
});

test('phone has a legible map for every scene without a blocking pinned panel', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await page.waitForFunction(() => window.researchReady && window.researchNetworkReady);
  await expect(page.locator('.network-map-panel')).not.toBeVisible();
  await expect(page.locator('.network-mobile-map')).toHaveCount(4);
  for (const article of await page.locator('.network-chapter').all()) {
    await article.locator('h3').scrollIntoViewIfNeeded();
    await expect(article.locator('h3')).toBeInViewport();
    await expect(article.locator('.network-mobile-map')).toBeVisible();
    expect(await article.locator('p:not(.network-mobile-caption)').first().evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(17);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test('network download failure preserves the story and offers a working retry', async ({page}) => {
  await page.route('**/data/network.json', route => route.abort());
  await page.goto('/');
  await page.waitForFunction(() => window.researchReady);
  await expect(page.locator('#network-status')).toContainText('Не удалось загрузить');
  await expect(page.locator('.walk-portrait')).toHaveCount(7);
  await page.unroute('**/data/network.json');
  await page.locator('#network-status button').click();
  await page.waitForFunction(() => window.researchNetworkReady);
  await expect(page.locator('.network-chapter')).toHaveCount(4);
});
