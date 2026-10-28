# BS-manager
Plataforma de Gestão: uma alternativa simples ao Odoo para equipas pequenas, acessível pelo browser (computador ou telemóvel) a partir de qualquer lado.

## Funcionalidades

| Módulo | O que faz |
|---|---|
| **Picagens** | Botão de entrada/saída no ecrã inicial, com notas opcionais (ex.: "teletrabalho"). Histórico mensal com totais por dia e por mês, e exportação para CSV (abre no Excel). Os administradores podem corrigir, acrescentar ou apagar picagens, e cada alteração fica marcada. |
| **Tarefas** | Registo do trabalho feito: data, projeto/cliente, título, descrição e horas. Filtros por mês, projeto e colaborador, e exportação para CSV. |
| **Férias e ausências** | Pedidos de férias, faltas, baixa, formação, teletrabalho, etc. Os dias úteis são contados automaticamente, sem fins de semana nem feriados. O saldo anual de férias é controlado, os pedidos sobrepostos são bloqueados, e os administradores aprovam ou rejeitam com uma nota. |
| **Calendário** | Calendário da equipa com os feriados nacionais (incluindo Páscoa, Sexta-feira Santa e Corpo de Deus), as ausências aprovadas de todos e os eventos partilhados (reuniões, prazos). Os pedidos pendentes só são visíveis para o próprio e para os administradores. |
| **Utilizadores** | Os administradores criam contas, definem os dias de férias, a cor no calendário e o perfil (colaborador ou administrador), e podem desativar contas. Cada pessoa pode mudar a sua palavra-passe. |

Tecnologia: Python 3.11+ · Flask · SQLAlchemy · SQLite (desenvolvimento) ou PostgreSQL (produção) · FullCalendar.

## Experimentar no seu computador

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
ADMIN_EMAIL=admin@exemplo.pt ADMIN_PASSWORD=mudar123 flask --app wsgi run --debug
```

Abra http://localhost:5000 e entre com o email e a palavra-passe acima. O primeiro administrador só é criado se a base de dados estiver vazia. Também o pode criar mais tarde com `flask --app wsgi create-admin`.

Testes: `pytest`

## Correr num PC do escritório (Linux)

Para uma equipa pequena basta um PC Linux que esteja sempre ligado. Os dados ficam numa base SQLite em `instance/bs-manager.db`.

1. Instale o Python e o Git (Ubuntu/Debian: `sudo apt install python3 python3-venv git`) e clone o repositório.
2. Crie o ficheiro `.env` com o primeiro administrador:
   ```bash
   cp .env.example .env
   ```
   Preencha `SECRET_KEY`, `ADMIN_EMAIL` e `ADMIN_PASSWORD`. `DOMAIN` e `POSTGRES_PASSWORD` só são precisos com Docker.
3. Instale como serviço, para arrancar sempre que o PC liga:
   ```bash
   ./instalar-servico.sh
   ```
   Se só quiser experimentar, use antes `./iniciar.sh` (para com Ctrl+C).
4. Os colegas na mesma rede abrem `http://<IP-do-PC>:8000`. O IP aparece nos registos (`journalctl -u bs-manager`) ou com `hostname -I`. Se o PC tiver firewall: `sudo ufw allow 8000/tcp`.

Cuidados:
* O PC não pode suspender. Desative a suspensão automática nas definições de energia.
* Peça ao responsável de rede um IP fixo para o PC (reserva DHCP no router), para o endereço não mudar.
* Faça cópias de segurança regulares de `instance/bs-manager.db` (por exemplo, com uma tarefa `cron` que a copia para outro disco ou para a cloud).

### Aceder de fora do escritório

* **Tailscale (recomendado):** instale o [Tailscale](https://tailscale.com) no PC do escritório (`curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`) e no computador ou telemóvel de cada colega. Todos acedem a `http://<nome-do-pc>:8000` como se estivessem no escritório, sem abrir portas no router. A aplicação não fica exposta à internet. É gratuito para equipas pequenas.
* **Cloudflare Tunnel:** dá um endereço público com HTTPS (ex.: `https://gestao.suaempresa.pt`) sem abrir portas, mas precisa de um domínio gerido na Cloudflare. Nesse caso, defina `SESSION_COOKIE_SECURE=1` no `.env`.
* **Abrir a porta no router:** não recomendado. A aplicação ficaria exposta sem HTTPS.

## Pôr online num servidor (acesso remoto pela internet)

Outra opção é um servidor pequeno (VPS de ~5 €/mês na Hetzner, OVH, DigitalOcean, etc.) com Docker. O `docker-compose.yml` arranca três serviços:

* **web**: a aplicação (gunicorn);
* **db**: PostgreSQL, com os dados guardados num volume;
* **caddy**: servidor HTTPS que obtém e renova sozinho o certificado SSL (Let's Encrypt).

Passos:

1. Compre ou use um domínio e crie um registo DNS **A** (ex.: `gestao.suaempresa.pt`) a apontar para o IP do servidor.
2. No servidor, instale o Docker e clone o repositório.
3. `cp .env.example .env` e preencha `DOMAIN`, `SECRET_KEY`, `POSTGRES_PASSWORD` e os dados `ADMIN_*`.
   Para gerar uma chave: `python3 -c "import secrets; print(secrets.token_hex(32))"`
4. `docker compose up -d --build`
5. Abra `https://gestao.suaempresa.pt`, entre como administrador e crie as contas dos colegas em **Utilizadores**.

Atualizar para uma nova versão: `git pull && docker compose up -d --build`.

Cópia de segurança da base de dados:

```bash
docker compose exec db pg_dump -U bsmanager bsmanager > backup-$(date +%F).sql
```

### Alternativas sem servidor próprio

* **Render / Railway / Fly.io**: criam a aplicação a partir do `Dockerfile` e dão-lhe uma base de dados PostgreSQL. Defina as variáveis `DATABASE_URL`, `SECRET_KEY`, `SESSION_COOKIE_SECURE=1` e `ADMIN_*`. O HTTPS é tratado pela plataforma.
* **Servidor no escritório**: use o mesmo `docker compose` e abra as portas 80 e 443 no router, ou use um túnel (Cloudflare Tunnel, Tailscale) para não expor portas.

## Configuração (variáveis de ambiente)

| Variável | Por omissão | Descrição |
|---|---|---|
| `SECRET_KEY` | (obrigatória em produção) | Chave para assinar as sessões |
| `DATABASE_URL` | SQLite em `instance/` | Ex.: `postgresql://user:pass@host/db` |
| `COMPANY_NAME` | `BS Manager` | Nome no topo da página |
| `APP_TIMEZONE` | `Europe/Lisbon` | Fuso horário das picagens |
| `DEFAULT_VACATION_DAYS` | `22` | Dias de férias de cada novo utilizador |
| `EXTRA_HOLIDAYS` | (vazio) | Feriados municipais em formato `MM-DD`, separados por vírgula (ex.: `06-13`) |
| `SESSION_COOKIE_SECURE` | `0` | `1` quando servido por HTTPS |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` | (vazio) | Primeiro administrador |

## Estrutura

```
app/
  __init__.py      # criação da app, configuração, comando create-admin
  models.py        # User, WorkSession (picagens), TaskEntry, LeaveRequest, Event
  holidays.py      # feriados portugueses
  routes/          # auth, dashboard, attendance, tasks, leave, calendar, admin
  templates/       # páginas HTML (Jinja2)
  static/style.css
tests/             # testes automáticos (pytest)
serve.py           # servidor para correr num PC (usado por iniciar.sh / instalar-servico.sh)
```

## Ideias para próximas versões

* Notificações por email quando um pedido de férias é aprovado ou rejeitado
* Mapa de férias anual por equipa e relatórios de horas extra
* Gestão de projetos com tarefas atribuídas (kanban)
* Picagem com geolocalização ou QR code
* Autenticação com Google/Microsoft 365
