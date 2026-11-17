# Hinchaboard — guía técnica de implementación

> El README principal es el manifiesto del producto. Este documento describe
> lo construido: modelo de rankings, stack, deploy, API y reglas.

Plataforma donde los **hinchas empujan a sus clubes** en rankings públicos.
**Temporada anual**: al cierre del año, el campeón de cada país y el campeón
mundial entran al **Salón de la Fama para siempre**.

## Modelo: dos rankings independientes

Cada club tiene **dos contadores separados**:

1. **Ranking del país.** Solo participan los clubes de ese país. Un empuje
   en el ranking de España mueve únicamente la tabla española.
2. **Ranking global.** Abierto a los 405 clubes del mundo. Cualquier hincha
   puede empujar cualquier club y ese club aparece en la tabla global.

Un empuje pertenece a **un solo ranking**. Lo recaudado en el país no mueve
el global y lo recaudado en el global no mueve el país. La misma hinchada
puede librar las dos guerras por separado.

En el código, `scope` identifica el ranking:

- `scope = "global"` → tabla mundial.
- `scope = "<countryId>"` → tabla de ese país (los ids de país coinciden con
  los ids de liga del seed: `arg`, `esp`, `eng`, etc.).

## Cómo funciona

1. **La tabla:** dos vistas separadas, **Ranking mundial** y **Por país**.
   Dentro de cada una, los clubes se ordenan por total acumulado. Empuje
   mínimo **USD 1**; los empujes se suman al total del club. Para pasar al
   club de arriba hay que superarlo por al menos **USD 1**.
2. **Mensaje junto a la posición:** al empujar, el hincha puede dejar una
   frase (máx. 140 caracteres) visible al lado de su club.
3. **Chat de hinchas ("La Tribuna"):** chat público en vivo con saldo
   prepago. **USD 1 = 3 mensajes**: el navegador guarda un token de billetera,
   cada mensaje descuenta uno y el crédito se carga por
   `POST /api/chat/credits` → `pay.html?credit=…`. El dinero del chat **no**
   empuja clubes ni mueve rankings.
4. **Vidriera gratis:** carruseles con los **405 clubes** de 22 países
   (América Latina, MLS y Europa), sin números ni jerarquía. Seed en
   `frontend/clubs.json`; cada club tiene sigla y color para su escudo SVG.
5. **Flujo de empuje:** formulario (liga + club + monto + mensaje) con selector
   **País del club / El mundo** → `POST /api/pushes` → `pay.html?intent=…` →
   al confirmarse el pago, el monto se suma al club **en ese ranking**.

## Stack (costo USD 0)

- **Cloudflare Workers** — API + frontend como static assets (un solo deploy).
- **Cloudflare KV** — tablas por ranking, actividad, chat, billeteras, intenciones y rate limits.
- **Frontend** — HTML/CSS/JS puro, sin build ni dependencias. Escudos SVG
  generados con color y sigla (sin logos de terceros).

El plan gratuito de Cloudflare alcanza para el v1 (100k requests/día).

## Estructura

```
hinchaboard-v2/
├── README.md                 ← manifiesto del producto
├── IMPLEMENTACION.md         ← este documento
├── wrangler.toml             ← config de Cloudflare
├── build_preview.py          ← genera preview.html autocontenido
├── frontend/
│   ├── index.html            ← ranking + formulario + carruseles + chat
│   ├── pay.html              ← página de confirmación de pago (stub)
│   ├── styles.css
│   ├── app.js                ← i18n EN/ES, tablas, formulario, feed
│   └── clubs.json            ← seed de 405 clubes / 22 países
└── worker/
    ├── index.js              ← API
    ├── lib.js                ← lógica pura (validación, empujes, ranking)
    ├── test.js               ← 24 tests unitarios
    └── test-integration.js   ← 22 tests de integración con KV mockeado
```

## API

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/board?scope=global` | Tabla global + actividad + stats |
| GET | `/api/board?scope=esp` | Tabla de España (solo clubes españoles) |
| GET | `/api/board?scope=country&country=esp` | Forma alternativa para la tabla de un país |
| POST | `/api/pushes` | Crea intención de empuje `{scope, club, amount, fan, message}` |
| GET | `/api/intents/:id` | Estado de una intención |
| POST | `/api/admin/confirm` | Confirma empuje o carga de chat (testing, `ADMIN_SECRET`) |
| GET/POST | `/api/chat` | Leer / enviar mensajes (POST requiere `wallet` y saldo) |
| GET | `/api/chat/wallet?wallet=<uuid>` | Saldo de mensajes |
| POST | `/api/chat/credits` | Crea carga de chat `{wallet, amount}` (USD 1 = 3) |
| POST | `/api/webhooks/polar` | Webhook stub (501) |
| POST | `/api/webhooks/lemonsqueezy` | Webhook stub (501) |

Errores relevantes: `UNKNOWN_SCOPE`, `CLUB_UNKNOWN`, `SCOPE_MISMATCH`
(el club no pertenece a ese país), `AMOUNT_TOO_LOW`, `RATE_LIMITED`,
`WALLET_REQUIRED`, `NO_CHAT_CREDIT` (402).

### KV

Binding: `RANKING_KV`.

- `board:global` → `{clubId: {league,total,pushes,firstAt,lastAt,shout?}}`
- `board:country:<countryId>` → misma forma, solo clubes de ese país
- `activity` → últimos empujes confirmados (con `scope`)
- `chat` → últimos mensajes
- `wallet:<uuid>` → `{messages, updatedAt}` saldo prepago del chat
- `intents:<uuid>` → intención pendiente (TTL 1 hora; tipo `push` o `chat_credit`)
- `rl:<ip>` / `rlc:<ip>` / `rlcr:<ip>` → rate limits de empujes, chat y cargas

## Deploy paso a paso

**1. Cuenta de Cloudflare (gratis)**
- [cloudflare.com](https://cloudflare.com) → Sign up → plan Free.

**2. Repo en GitHub**
- El código vive en `enrrutador/hinchaboard-v2`.

**3. Crear el Worker conectado al repo**
- Cloudflare dashboard → **Workers & Pages** → **Create** → **Workers** →
  **Import a repository** → conectar GitHub → elegir `hinchaboard-v2` →
  **Deploy**.
- Cloudflare lee `wrangler.toml` y publica frontend + API juntos.
- URL tipo `hinchaboard-v2.<tu-cuenta>.workers.dev`.

**4. Crear la base KV**
- Dashboard → **Storage & databases** → **KV** → **Create namespace** →
  nombre: `RANKING_KV` → copiar el ID.
- Worker → **Settings** → **Bindings** → **Add binding** → **KV Namespace** →
  variable: `RANKING_KV` → pegar el ID → Save.
- Alternativa: pegar el ID en `wrangler.toml` y re-deploy.

**5. Variables de entorno**
- `ADMIN_SECRET` → **Secret** (solo para probar pagos antes del proveedor real).
- `PAYMENT_PROVIDER` → **Text** → `stub`.

**6. Re-deploy y probar**
- Workers & Pages → Worker → **Deployments** → **Retry deployment**.
- Abrir la URL → elegir un ranking → empujar un club → en la página de pago,
  pegar `ADMIN_SECRET` y **Mark as paid (test)**.
- Verificar que el club aparece en la tabla elegida y **no** en la otra.

## Probar en local (opcional)

```bash
node worker/test.js               # 24 tests de reglas/validación
node worker/test-integration.js   # 22 tests de la API
python3 build_preview.py          # regenera preview.html
```

## Conectar pagos reales

La variable `PAYMENT_PROVIDER` elige entre `stub`, `polar` o `lemonsqueezy`.
Los endpoints de webhook existen y hoy devuelven **501** a propósito. Para
conectar uno real, en `worker/index.js`:

1. Verificar la firma del webhook con el secreto del proveedor.
2. Extraer `intentId` y monto del evento.
3. Llamar a `confirmPush(env, intent)` (la misma función del endpoint de testing).

**Nota para Argentina:** Stripe no opera bien para residentes argentinos.
Candidatos a verificar: **Lemon Squeezy** (Merchant of Record) o **Polar.sh**.
Confirmar disponibilidad para AR antes de programar la integración.

## Reglas del v1

- Empuje mínimo: USD 1.
- Para pasar al club de arriba: su total + al menos USD 1 más que el total propio.
- Un empuje pertenece a un solo ranking (`scope`).
- En un ranking de país solo se pueden empujar clubes de ese país; en el
  global, cualquier club.
- Empates: gana el club que llegó primero a ese total (`firstAt`).
- Los empujes son finales, sin reembolsos.
- Rate limit: 10 intentos de empuje por IP por hora.
- Rate limit del chat: 20 mensajes por IP cada 10 minutos.
- Chat prepago: USD 1 = 3 mensajes; cada mensaje descuenta 1; el crédito no
  afecta rankings.
- Sin cuentas de usuario en el v1: la billetera es un UUID guardado en
  `localStorage` (quien tenga el token puede gastar su saldo).

## Idioma

Interfaz **inglés y español** con selector manual (EN/ES). Los textos viven en
`STRINGS` (`frontend/app.js`) y los nombres de países/ligas en `clubs.json`
(`name_en/name_es`, `country_en/country_es`). Agregar un idioma nuevo requiere
sumar su bloque de textos y, si se quieren nombres traducidos, sus campos en
el seed. No se usa traducción automática.

## Pendiente / diferido

- **Chat prepago:** flujo y saldo implementados; falta conectar el cobro real.
- **Pagos reales:** proveedor sin conectar (empujes y cargas de chat).
- **Confirmación de pago:** solo vía `ADMIN_SECRET`; quitar o proteger al
  conectar el proveedor.
- **Salón de la Fama:** la UI existe; falta la lógica de cierre de temporada.
- **Cuentas, dashboards, patrocinios:** fuera del v1 por decisión explícita.
