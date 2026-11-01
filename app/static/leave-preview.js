(() => {
  const form = document.getElementById('leave-request');
  if (!form) return;
  const box = document.getElementById('leave-estimate');
  const heading = document.getElementById('estimate-days');
  const detail = document.getElementById('estimate-detail');
  const messages = JSON.parse(document.getElementById('ui-translations').textContent);
  const translate = (message, values = {}) => (messages[message] || message).replace(/\{(\w+)\}/g, (match, key) => values[key] ?? match);
  let timer, controller, revision = 0;

  function show(title, description, error = false) {
    heading.textContent = title;
    detail.textContent = description;
    box.classList.toggle('estimate-error', error);
  }

  async function preview(current) {
    controller = new AbortController();
    const payload = new FormData();
    for (const name of ['csrf_token', 'kind', 'start_date', 'end_date']) {
      payload.set(name, form.elements.namedItem(name).value);
    }
    try {
      const response = await fetch(form.dataset.previewUrl, {
        method: 'POST', body: payload, signal: controller.signal,
        headers: {'Accept': 'application/json'},
      });
      if (current !== revision) return;
      if (response.redirected) {
        show(translate('Sessão expirada'), translate('Guarda as tuas observações e volta a iniciar sessão.'), true);
        return;
      }
      const result = await response.json();
      if (current !== revision) return;
      if (!response.ok) {
        show(translate('Revê as datas'), result.error || translate('Não foi possível calcular este período. Atualiza a página e tenta novamente.'), true);
        return;
      }
      const summary = result.vacation
        ? result.years.map(item => {
          const message = item.days === 1
            ? (item.remaining === 1 ? '{year}: {days} dia de férias · {remaining} dia disponível após o pedido.' : '{year}: {days} dia de férias · {remaining} dias disponíveis após o pedido.')
            : (item.remaining === 1 ? '{year}: {days} dias de férias · {remaining} dia disponível após o pedido.' : '{year}: {days} dias de férias · {remaining} dias disponíveis após o pedido.');
          return translate(message, item);
        }).join(' ')
        : translate('Este tipo de ausência não desconta dias do saldo de férias.');
      show(translate(result.working_days === 1 ? '{days} dia de trabalho' : '{days} dias de trabalho', {days: result.working_days}), summary);
    } catch (error) {
      if (error.name !== 'AbortError' && current === revision) {
        show(translate('Resumo indisponível'), translate('Podes continuar a preencher. As datas e o saldo serão verificados ao submeter.'));
      }
    } finally {
      if (current === revision) box.removeAttribute('aria-busy');
    }
  }

  function schedule() {
    const current = ++revision;
    clearTimeout(timer);
    controller?.abort();
    box.removeAttribute('aria-busy');
    if (!form.elements.namedItem('start_date').value) {
      show(translate('Escolhe as datas'), translate('Vamos contar os teus dias de trabalho e mostrar o efeito no saldo.'));
      return;
    }
    show(translate('A calcular…'), translate('A verificar os dias de trabalho, feriados e saldo disponível.'));
    box.setAttribute('aria-busy', 'true');
    timer = setTimeout(() => preview(current), 250);
  }

  for (const name of ['kind', 'start_date', 'end_date']) {
    form.elements.namedItem(name).addEventListener('input', schedule);
    form.elements.namedItem(name).addEventListener('change', schedule);
  }
  form.addEventListener('submit', () => { ++revision; clearTimeout(timer); controller?.abort(); });
  if (form.elements.namedItem('start_date').value) schedule();
})();
