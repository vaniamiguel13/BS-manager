/* Read-only layout checks against the disposable local browser fixture. */
const {chromium,webkit}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const base=process.env.BS_BROWSER_BASE;
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(base),'Disposable loopback fixture required');
const artifacts=process.env.BS_BROWSER_ARTIFACTS || fs.mkdtempSync(path.join(os.tmpdir(),'management-responsive-'));
fs.mkdirSync(artifacts,{recursive:true,mode:0o700});
const widths=[320,390,700,760,761,768,1024,1240,1241,1280,1440,1920];
async function login(page,role) {
  await page.goto(base+'/login');
  await page.locator('[name=email]').fill(role+'@example.invalid');
  await page.locator('[name=password]').fill('browser-synthetic-password');
  await page.getByRole('button',{name:'Entrar',exact:true}).click();
  await page.waitForURL(base+'/');
}
async function capture(page,name) {
  await page.screenshot({path:path.join(artifacts,name+'.png'),fullPage:true});
}
async function geometry(page,width,role,label) {
  await page.waitForLoadState('load');
  await page.evaluate(()=>document.fonts.ready);
  const data=await page.evaluate(()=>{
    const rect=selector=>{
      const element=document.querySelector(selector),r=element.getBoundingClientRect();
      return {left:r.left,right:r.right,bottom:r.bottom,height:r.height,width:r.width};
    };
    const main=document.querySelector('main');
    return {
      overflow:document.documentElement.scrollWidth>innerWidth+2,
      availableWidth:document.documentElement.clientWidth,
      brand:rect('.brand'), language:rect('.header-tools .language-switch'), theme:rect('.header-tools .theme-switch'),
      main:rect('main'), contentLeft:main.getBoundingClientRect().left+parseFloat(getComputedStyle(main).paddingLeft),
      heading:rect('h1'), toolbar:rect('.report-toolbar'),
      controls:[...document.querySelectorAll('.report-toolbar select, .report-toolbar .btn')].map(element=>{const r=element.getBoundingClientRect();return{bottom:r.bottom,height:r.height,left:r.left,right:r.right};}),
      lastNav:rect('#workspace-nav .nav-item:last-child'),
      nav:rect('#workspace-nav'), navFixed:getComputedStyle(document.querySelector('#workspace-nav')).position==='fixed',
      navItems:[...document.querySelectorAll('#workspace-nav .nav-item')].filter(element=>element.getClientRects().length).map(element=>{const r=element.getBoundingClientRect();return{left:r.left,right:r.right,clipped:element.scrollWidth>element.clientWidth+1};}),
      viewportHeight:innerHeight, bottomPadding:parseFloat(getComputedStyle(main).paddingBottom),
    };
  });
  assert(!data.overflow,label+' page overflows');
  assert(Math.abs(data.main.width-data.availableWidth)<2 && Math.abs(data.main.left)<2,label+' does not fill the available width: '+JSON.stringify({main:data.main,availableWidth:data.availableWidth,viewport:width}));
  assert(Math.abs(data.brand.left-data.contentLeft)<2,label+' brand/content gutters differ');
  assert(Math.abs(data.heading.left-data.toolbar.left)<2,label+' heading/filter gutters differ');
  assert(data.brand.right+3<=data.language.left,label+' brand overlaps language');
  assert(data.language.right+3<=data.theme.left,label+' language overlaps theme');
  for(const control of data.controls){
    assert(control.height>=43,label+' report control shorter than 44px');
    assert(control.left>=data.contentLeft-2 && control.right<=data.availableWidth-data.contentLeft+2,label+' report control clipped');
  }
  if(width>700 && role==='admin') {
    const bottoms=data.controls.map(control=>control.bottom);
    assert(Math.max(...bottoms)-Math.min(...bottoms)<2,label+' filter and export controls have different baselines');
  }
  assert.equal(data.navFixed,width<=760,label+' incorrect responsive navigation');
  if(data.navFixed) {
    // Phone dock: inside the viewport, labels unclipped, and page content can scroll clear of it.
    assert(data.nav.left>=0 && data.nav.right<=data.availableWidth+1 && data.nav.bottom<=data.viewportHeight,label+' dock leaves the viewport');
    assert(data.bottomPadding>=data.nav.height,label+' content can hide under the dock');
    data.navItems.forEach((item,index)=>{
      assert(!item.clipped,label+' dock label clipped');
      if(index)assert(item.left+1>=data.navItems[index-1].right,label+' dock items overlap');
    });
  } else if(Math.abs(data.lastNav.bottom-data.language.bottom)<20) assert(data.lastNav.right+4<=data.language.left,label+' navigation overlaps toolbar');
}
async function stableNavigation(browser,name) {
  const context=await browser.newContext({viewport:{width:1440,height:900}});
  const page=await context.newPage();
  try {
    await login(page,'admin');
    // Delay the exact resources that previously moved the visible header after paint.
    await page.route('**/theme.js',async route=>{await new Promise(resolve=>setTimeout(resolve,300));await route.continue();});
    await page.route('**/*.woff2',async route=>{await new Promise(resolve=>setTimeout(resolve,500));await route.continue();});
    await page.addInitScript(()=>{
      window.headerFrames=[];let frames=0;
      const sample=()=>{
        const header=document.querySelector('.workspace-header');
        if(header) window.headerFrames.push([header,...header.querySelectorAll('.brand,.nav-item,.language-switch,.theme-switch,.account-menu')].flatMap(element=>{
          const rect=element.getBoundingClientRect();return [rect.x,rect.y,rect.width,rect.height];
        }));
        if(frames++<120)requestAnimationFrame(sample);
      };requestAnimationFrame(sample);
    });
    for(const width of [320,1024,1440]) {
      await page.setViewportSize({width,height:900});
      let previous;
      for(const endpoint of ['/','/picagens/','/tarefas/','/ferias/','/calendario/','/admin/utilizadores']) {
        await page.goto(base+endpoint);await page.waitForTimeout(100);
        assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2)),name+' page overflows at '+width+': '+endpoint);
        const samples=await page.evaluate(()=>headerFrames);
        assert(samples.length>1,name+' missing navigation frames');
        for(const sample of samples) {
          assert.equal(sample.length,samples[0].length);
          sample.forEach((value,index)=>assert(Math.abs(value-samples[0][index])<1,name+' header moves during loading: '+endpoint+' at '+width));
        }
        const latest=samples.at(-1);
        if(previous)latest.forEach((value,index)=>assert(Math.abs(value-previous[index])<1,name+' header moves between pages at '+width));
        previous=latest;
      }
      // A long report must not move the header when a scrollbar becomes necessary.
      const before=await page.locator('.workspace-header').boundingBox();
      await page.evaluate(()=>document.querySelector('main').style.minHeight='2400px');
      const after=await page.locator('.workspace-header').boundingBox();
      assert(Math.abs(before.x-after.x)<1 && Math.abs(before.width-after.width)<1,name+' scrollbar moves header');
    }
  } finally {await context.close();}
}
async function run(engine,name) {
  const browser=await engine.launch({headless:true});
  try {
    await stableNavigation(browser,name);
    for(const role of ['admin','worker']) {
      const context=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'reduce'});
      const page=await context.newPage();page.setDefaultTimeout(12000);
      const errors=[];page.on('pageerror',error=>errors.push(error.message));
      page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
      page.on('request',request=>assert(request.url().startsWith(base),'Unexpected external request'));
      await login(page,role);
      assert.equal(await page.locator('.brand-product').innerText(),'Management');
      assert.equal(await page.title(),'Management');
      for(const width of widths) {
        await page.setViewportSize({width,height:width<761?844:1000});
        for(const language of ['pt','en']) {
          await page.goto(base+'/picagens/?mes=2026-11');
          await page.getByRole('button',{name:language==='pt'?'Português':'English',exact:true}).click();
          assert.equal(await page.locator('html').getAttribute('lang'),language==='pt'?'pt-PT':'en');
          const label=`${name}-${role}-${width}-${language}`;
          await geometry(page,width,role,label+'-light');
          await page.locator('.theme-switch').click();
          assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
          assert.equal(await page.locator('.theme-switch').getAttribute('aria-pressed'),'true');
          await geometry(page,width,role,label+'-dark');
          if(role==='admin' && [320,390,768,1440,1920].includes(width)) await capture(page,label+'-attendance-dark');
          if(width===390 || width===1440) {
            for(const endpoint of ['/','/tarefas/','/ferias/','/calendario/','/perfil']) {
              await page.goto(base+endpoint);
              assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
              assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2)),label+endpoint+' dark overflow');
              if(role==='admin') await capture(page,label+endpoint.replace(/[^a-z]/g,'-')+'-dark');
            }
            await page.locator('.account-menu summary').click();
            await page.getByRole('link',{name:language==='pt'?'O meu perfil':'My profile',exact:true}).waitFor();
            await page.keyboard.press('Escape');
            assert.equal(await page.locator('.account-menu').getAttribute('open'),null);
            if(width===390) {
              assert(await page.locator('#workspace-nav').isVisible());
              assert.equal(await page.locator('#workspace-nav .nav-item:visible').count(),5);
              assert.equal(await page.locator('.account-dropdown a[href="/admin/utilizadores"]').count(),role==='admin'?1:0);
              await page.locator('#workspace-nav a[href="/picagens/"]').click();
              await page.waitForURL(base+'/picagens/');
            }
          }
          await page.goto(base+'/picagens/?mes=2026-11');
          await page.locator('.theme-switch').click();
          assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
          if(role==='admin' && [390,1440].includes(width)) await capture(page,label+'-attendance-light');
        }
      }
      assert.deepEqual(errors,[],name+' '+role+' runtime errors');
      await context.close();
    }
    // OS fallback, manual override, cross-tab synchronization and unavailable storage.
    const system=await browser.newContext({colorScheme:'dark',viewport:{width:390,height:844}});
    const page=await system.newPage();page.setDefaultTimeout(12000);
    await page.goto(base+'/login');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    await capture(page,name+'-login-dark');
    await page.locator('.theme-switch').click();
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    const second=await system.newPage();await second.goto(base+'/login');
    await second.locator('.theme-switch').click();
    await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
    await system.close();
    const restricted=await browser.newContext({colorScheme:'light'});
    await restricted.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Unavailable','SecurityError');}}));
    const noStorage=await restricted.newPage();await noStorage.goto(base+'/login');
    await noStorage.locator('.theme-switch').click();
    assert.equal(await noStorage.locator('html').getAttribute('data-theme'),'dark');
    await restricted.close();
  } finally { await browser.close(); }
}
(async()=>{
  for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]) await run(engine,name);
  console.log('PASS: Chromium/WebKit stable page navigation with delayed fonts/theme, responsive navbar and report alignment at 320–1920px, PT/EN, admin/employee, light/dark, keyboard menus, theme persistence, OS preference, tab sync and unavailable storage.');
  console.log('Screenshots: '+artifacts);
})().catch(error=>{console.error(error);process.exitCode=1;});
