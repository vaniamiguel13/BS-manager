/* Synthetic local acceptance only; never points at a configured public URL. */
const {chromium, webkit} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const base = process.env.BS_BROWSER_BASE;
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(base), 'Disposable loopback fixture required');
const screenshots = process.env.BS_BROWSER_ARTIFACTS || fs.mkdtempSync(path.join(os.tmpdir(), 'bs-manager-browser-screens-'));
fs.mkdirSync(screenshots, {recursive: true, mode: 0o700});

async function login(page, name, language='pt') {
  await page.goto(base + '/login');
  await page.locator('input[name=email]').fill(name + '@example.invalid');
  await page.locator('input[name=password]').fill('browser-synthetic-password');
  await Promise.all([page.waitForURL(base + '/'),page.getByRole('button', {name:language === 'en' ? 'Sign in' : 'Entrar',exact:true}).click()]);
}
async function screenshot(page, name) {
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(screenshots,name+'.png'),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth+2);
  assert(!overflow, name+' overflows viewport');
}
let scenario=0;
async function run(engine, name, width, height) {
  const number=scenario++;
  const taskTitle="Browser workflow task "+number;
  const leaveDay=["07","09","14","16"][number];
  const attendanceDay=20+number;
  const eventMonth=new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Lisbon'}).slice(0,7);
  const browser=await engine.launch({headless:true});
  try {
    const context=await browser.newContext({viewport:{width,height}, timezoneId:'Europe/Lisbon', colorScheme:number%2?'dark':'light', reducedMotion:'reduce'});
    const page=await context.newPage();page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(15000);const failures=[];
    page.on('pageerror',e=>failures.push(e.message));
    page.on('console',message=>{if(message.type()==='error') failures.push(message.text());});
    page.on('dialog',async dialog=>dialog.accept());
    page.on('request',r=>{assert(r.url().startsWith(base), 'Unexpected third-party browser request: '+r.url());});
    await page.goto(base+'/login');
    assert.equal(await page.locator('.login-identity h1').innerText(),'Gestão da equipa');
    await screenshot(page,name+'-'+width+'-login-pt');
    await page.getByRole('button',{name:'English',exact:true}).click();
    await page.getByRole('heading',{name:'Team workspace',exact:true}).waitFor();
    await screenshot(page,name+'-'+width+'-login-en');
    await page.getByRole('button',{name:'Português',exact:true}).click();
    await login(page,'worker');
    await screenshot(page,name+'-'+width+'-dashboard');
    const privateAbsence=page.locator('.absence-item').filter({hasText:'Synthetic availability'});
    await privateAbsence.waitFor();
    assert((await privateAbsence.innerText()).includes('Indisponível'), 'Employee dashboard must show availability only');
    assert(!(await privateAbsence.innerText()).includes('Baixa médica'), 'Employee dashboard must not show private leave category');
    assert(!(await privateAbsence.innerText()).includes('Private synthetic medical detail'), 'Employee dashboard must not show private leave reason');
    await page.locator('form[action="/picagens/entrada"] button').click();
    await page.getByText('A trabalhar desde as',{exact:false}).waitFor();
    await page.locator('form[action="/picagens/saida"] button').click();
    await page.getByText('Fora de serviço',{exact:false}).waitFor();
    await page.goto(base+'/tarefas/nova');
    await page.locator('[name=date]').fill('2026-10-29');
    await page.locator('[name=title]').fill(taskTitle);
    await page.locator('[name=project]').fill('Synthetic project');
    await page.locator('[name=hours]').fill('2.5');
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    await page.getByText(taskTitle,{exact:true}).waitFor();
    await screenshot(page,name+'-'+width+'-worklogs');
    const taskRow=page.locator('tr').filter({hasText:taskTitle});
    await taskRow.getByRole('link',{name:/^Editar/}).click();
    await page.locator('[name=description]').fill('Edited in a real browser');
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    await page.getByText('Edited in a real browser',{exact:true}).waitFor();
    const download=page.waitForEvent('download');
    await page.getByRole('link',{name:'Exportar CSV',exact:true}).click();
    assert((await download).suggestedFilename().startsWith('tarefas-'));
    await page.locator('tr').filter({hasText:taskTitle}).getByRole('button',{name:/^Apagar/}).click();
    await page.getByText('Tarefa apagada.',{exact:true}).waitFor();

    await page.goto(base+'/ferias/?ano=2026');
    assert((await page.locator('#leave-request select').boundingBox()).height >= 40, 'Leave selector touch target');
    await page.locator('form[action="/ferias/pedir"] [name=start_date]').fill('2026-12-'+leaveDay);
    await page.locator('form[action="/ferias/pedir"] [name=end_date]').fill('2026-12-'+leaveDay);
    await page.locator('#estimate-days').getByText('1 dia de trabalho',{exact:true}).waitFor();
    assert((await page.locator('#estimate-detail').innerText()).includes('disponíveis após o pedido'));
    await screenshot(page,name+'-'+width+'-leave-plan');
    await page.getByRole('button',{name:'Submeter pedido'}).click();
    await page.getByText('Pedido submetido',{exact:false}).waitFor();
    await screenshot(page,name+'-'+width+'-leave');
    // A successful preview did not reserve an extra request: there is one new vacation item.
    assert.equal(await page.locator('.request-item').filter({hasText: 'Férias'}).count(), number+1);
    await page.goto(base+'/calendario/');
    await page.locator('.fc-toolbar-title').waitFor();
    if (width < 700) assert(await page.locator('.fc-list').isVisible(), 'Mobile calendar should use list view');
    else assert(await page.locator('.fc-daygrid').isVisible(), 'Desktop calendar should use month grid');
    for(const [label,view] of [['Semana','.fc-timegrid'],['Mês','.fc-daygrid'],['Agenda','.fc-list']]) {
      await page.getByRole('button',{name:label,exact:true}).click();
      await page.locator(view).waitFor();
      assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2)), 'Calendar '+label+' overflows');
    }
    await page.getByRole('button',{name:width<700?'Agenda':'Mês',exact:true}).click();
    await page.getByRole('button',{name:'+ Novo evento'}).click();
    await page.locator('#event-dialog [name=title]').fill('Browser calendar event '+number);
    await page.locator('#event-dialog [name=start]').fill(eventMonth+'-10T10:00');
    await page.locator('#event-dialog [name=end]').fill(eventMonth+'-10T11:00');
    await page.locator('#event-dialog button[type=submit], #event-dialog button.btn-primary').click();
    await page.getByText('Evento criado.',{exact:true}).waitFor();
    await page.locator('.fc-toolbar-title').waitFor();
    await screenshot(page,name+'-'+width+'-calendar');
    await page.locator('.fc-event').filter({hasText:'Browser calendar event '+number}).click();
    await page.locator('#detail-dialog').waitFor({state:'visible'});
    await page.locator('#detail-edit').click();
    await page.getByRole('heading',{name:'Editar evento',exact:true}).waitFor();
    assert(await page.locator('.timed').isVisible());
    assert(!await page.locator('.allday').isVisible());
    await page.locator('[name=title]').fill('Updated calendar event '+number);
    await page.locator('#all-day').check();
    assert(!await page.locator('.timed').isVisible());
    assert(await page.locator('.allday').isVisible());
    await page.locator('#ev-start-date').fill(eventMonth+'-12');
    await page.locator('#ev-end-date').fill(eventMonth+'-13');
    await screenshot(page,name+'-'+width+'-calendar-edit');
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    await page.getByText('Evento guardado.',{exact:true}).waitFor();
    // A multi-day event has one row per date in the mobile agenda.
    await page.locator('.fc-event').filter({hasText:'Updated calendar event '+number}).first().click();
    await page.locator('#detail-dialog').waitFor({state:'visible'});
    await page.locator('#detail-delete button').click();
    await page.getByText('Evento apagado.',{exact:true}).waitFor();

    await page.locator('.account-menu summary').click();
    await page.locator('form[action="/logout"] button').click();
    await login(page,'admin');
    const adminAbsence=page.locator('.absence-item').filter({hasText:'Synthetic availability'});
    await adminAbsence.waitFor();
    assert((await adminAbsence.innerText()).includes('Baixa médica'), 'Administrator dashboard should show the leave category');
    await page.goto(base+'/admin/utilizadores');
    await page.evaluate(()=>document.fonts.ready);
    if(width>1100) {
      const rows=await page.locator('.user-table tbody tr').evaluateAll(rows=>rows.map(row=>[...row.cells].map(cell=>cell.getBoundingClientRect().bottom)));
      for(const bottoms of rows)assert(Math.max(...bottoms)-Math.min(...bottoms)<1,'User row borders are misaligned');
    }
    await screenshot(page,name+'-'+width+'-users');
    await page.getByRole('link',{name:'+ Novo utilizador'}).click();
    await page.locator('[name=name]').fill('Browser employee '+number);
    await page.locator('[name=email]').fill('browser'+number+'@example.invalid');
    await page.locator('[name=password]').fill('browser-synthetic-password');
    await page.locator('[name=vacation_days]').fill('15');
    await screenshot(page,name+'-'+width+'-user-form');
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    const employeeRow=page.locator('tr').filter({hasText:'browser'+number+'@example.invalid'});
    await employeeRow.getByRole('link',{name:/^Editar/}).click();
    await page.locator('[name=active]').uncheck();
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    await employeeRow.getByText('Inativo',{exact:true}).waitFor();

    await page.goto(base+'/ferias/?ano=2026');
    const form=page.locator('.review-form').filter({has:page.locator('[name=decision][value=aprovar]')}).first();
    await form.locator('[name=review_note]').fill('Browser approval');
    await form.locator('[name=decision][value=aprovar]').click();
    await page.getByText('Decisão guardada com histórico.',{exact:true}).waitFor();
    await page.goto(base+'/picagens/nova');
    await page.locator('[name=start]').fill('2026-10-'+attendanceDay+'T09:00');
    await page.locator('[name=end]').fill('2026-10-'+attendanceDay+'T10:00');
    await page.locator('[name=reason]').fill('Synthetic browser correction');
    await page.getByRole('button',{name:'Guardar',exact:true}).click();
    await page.getByText('Picagem guardada com histórico.',{exact:true}).waitFor();
    await screenshot(page,name+'-'+width+'-attendance');
    await page.getByRole('combobox',{name:'Colaborador',exact:true}).waitFor();
    await page.goto(base+'/tarefas/?mes=2026-10');
    await page.getByRole('combobox',{name:'Colaborador',exact:true}).selectOption({label:'Synthetic worker'});
    await page.getByRole('button',{name:'Filtrar',exact:true}).click();
    assert(new URL(page.url()).searchParams.get('user'));
    await page.getByRole('combobox',{name:'Projeto',exact:true}).waitFor();
    await page.getByRole('link',{name:'Limpar filtros',exact:true}).click();
    assert(!new URL(page.url()).searchParams.has('user'));
    assert.deepEqual(failures,[],name+' JavaScript errors');
    // Locale changes use the real CSRF-protected form, retain filters and preserve login.
    await page.getByRole('button',{name:'English',exact:true}).click();
    assert.equal(new URL(page.url()).searchParams.get('mes'),'2026-10');
    await page.getByRole('heading',{name:'Work logs',exact:true}).waitFor();
    for (const [endpoint,heading] of [['/','Hello, Synthetic'],['/picagens/','Attendance'],['/tarefas/nova','Log work'],['/ferias/','Leave and absences'],['/calendario/','Team calendar'],['/perfil','My profile'],['/admin/utilizadores','Users'],['/admin/utilizadores/novo','New user']]) {
      await page.goto(base+endpoint);
      if(endpoint==='/') await page.getByRole('heading').filter({hasText:'Hello,'}).first().waitFor();
      else await page.getByRole('heading',{name:heading,exact:true}).waitFor();
      assert.equal(await page.locator('html').getAttribute('lang'),'en');
      await screenshot(page,name+'-'+width+'-en-'+endpoint.replace(/[^a-z]/g,'-'));
    }
    await page.goto(base+'/ferias/?ano=2026');
    await page.locator('#leave-request [name=start_date]').fill('2026-12-29');
    await page.locator('#estimate-days').getByText('1 working day',{exact:true}).waitFor();
    assert((await page.locator('#estimate-detail').innerText()).includes('available after this request'));
    await screenshot(page,name+'-'+width+'-leave-plan-en');
    await page.goto(base+'/calendario/');
    await page.getByRole('button',{name:'Month',exact:true}).waitFor();
    await page.getByRole('button',{name:'+ New event',exact:true}).click();
    await page.locator('#event-dialog').getByLabel('Start',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Cancel',exact:true}).click();
    await page.getByRole('button',{name:'Português',exact:true}).click();
    await page.getByRole('heading',{name:'Calendário da equipa',exact:true}).waitFor();
    assert.deepEqual(failures,[],name+' translated JavaScript errors');
    await context.close();
    if (number === 0) {
      const noScript=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
      const fallback=await noScript.newPage();
      await fallback.goto(base+'/login');
      await fallback.getByRole('button',{name:'English',exact:true}).click();
      await login(fallback,'colleague','en');
      await fallback.goto(base+'/ferias/?ano=2026');
      await fallback.locator('#leave-request [name=start_date]').fill('2026-12-30');
      await fallback.getByRole('button',{name:'Submit request',exact:true}).click();
      await fallback.getByText('Request submitted',{exact:false}).waitFor();
      assert(!(await fallback.locator('.theme-switch').isVisible()));
      await fallback.locator('.account-menu summary').click();
      await fallback.getByRole('link',{name:'My profile',exact:true}).click();
      await fallback.getByRole('heading',{name:'My profile',exact:true}).waitFor();
      await noScript.close();
    }
  } finally {await browser.close();}
}
(async()=>{
  for (const [name,engine] of [['chromium',chromium],['webkit',webkit]]) {
    for(const [width,height] of [[1440,1000],[390,844]]) await run(engine,name,width,height);
  }
  console.log('PASS: Chromium/WebKit desktop/mobile workflows, CSRF login, attendance, work logs, leave, calendar and administrator forms, PT/EN switching and English no-JavaScript submission.');
  console.log('Screenshots: '+screenshots);
})().catch(e=>{console.error(e);process.exitCode=1;});
