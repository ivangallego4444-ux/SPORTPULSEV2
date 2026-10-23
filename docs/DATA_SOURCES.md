# Fuentes de datos gratuitas — verificación real (2026-10-21)

Todo lo que sigue se comprobó haciendo peticiones HTTP reales a cada API y/o
leyendo sus páginas oficiales de términos/licencia hoy mismo (no son datos
de memoria ni suposiciones). Donde no se pudo verificar algo, se dice
explícitamente en vez de inventarlo.

> **Actualización (misma fecha, segunda sesión):** baloncesto y tenis ya
> están resueltos y **implementados** en `apps/api` + `apps/web` sin crear
> ninguna cuenta nueva (petición explícita del usuario). Ver
> "Resolución de baloncesto y tenis" más abajo. balldontlie sigue sin
> probarse (exige cuenta) y por eso no se usa en el código.
>
> **Actualización (misma fecha, tercera sesión):** el usuario pidió
> ampliar a LaLiga, Premier League, Serie A, Ligue 1 y Champions League, y
> autorizó explícitamente crear cuentas en football-data.org/API-Football
> para ello. No las he creado — crear cuentas en servicios de terceros
> está fuera de lo que puedo hacer yo mismo aunque se autorice
> explícitamente (una regla de seguridad, no una decisión de este
> proyecto). En su lugar verifiqué que **TheSportsDB ya cubre esas cinco
> ligas con la misma clave pública gratuita**, así que están todas
> implementadas sin cuenta nueva — ver "Las cinco ligas nuevas" más abajo.
> También se construyó un motor de predicción (Poisson real sobre
> resultados reales) y se encontró/arregló un bug real de caché. Ver
> [README.md](../README.md) para el resumen completo de esta sesión.

## Resumen rápido

| Fuente | Deporte | Coste | Funciona ahora (probado) | Uso comercial | Limitación clave |
|---|---|---|---|---|---|
| OpenLigaDB | Fútbol (Alemania) | 0 € | Sí | Permitido con atribución (ODbL) | Solo competiciones alemanas (Bundesliga, 2.Bundesliga, 3.Liga, DFB-Pokal, algunas más) |
| football-data.org | Fútbol (internacional) | 0 € (tier Free) | Sí | No prohibido explícitamente, pero exige atribución y limita a 1 dominio/app | Solo 12 competiciones, 10 peticiones/min, datos retrasados, sin alineaciones/estadísticas; **no puedes usar los escudos de los equipos sin permiso del propietario** |
| TheSportsDB | Fútbol + baloncesto + tenis + más (v1) | 0 € (clave pública `123`) | Sí | **Prohibido publicar en app store en el tier gratis**; para web pública no está prohibido explícitamente pero es ambiguo | 30 peticiones/min; escudos/artwork con licencia mixta, algunos no se pueden usar públicamente |
| balldontlie | Baloncesto (NBA/WNBA/+ligas), también lista tenis/golf/fútbol entre sus 20+ ligas | 0 €/mes por 1 deporte | Parcialmente (endpoint de equipos exige clave; no me he registrado, ver más abajo) | **Explícitamente permitido**, sin atribución obligatoria | Plan gratis = 1 solo deporte, 5 peticiones/min, acceso "Basic" (no todas las estadísticas) |
| Jeff Sackmann tennis_atp / tennis_wta (GitHub) | Tenis histórico | 0 € | **No disponible**: el repo ya no es público en la cuenta del autor | — | No se puede usar como fuente hasta reconfirmar dónde está |
| API-Football / api-sports.io | Fútbol+ | Se dice que tiene free tier (~100 req/día) | **No verificado**: la web bloquea el acceso automatizado (403) | Desconocido | Requiere registro manual para comprobar — no lo he hecho |

## Detalle por fuente

### 1. OpenLigaDB — `api.openligadb.de`
- **Probado en vivo**: `GET /getmatchdata/bl1` devuelve partidos de la
  Bundesliga 2026/2027 ya jugados, con resultado, minuto de cada gol,
  goleador, y **URL del escudo de cada equipo** (`teamIconUrl`).
- **Sin clave de API, sin registro.**
- **Licencia**: Open Database License (ODbL) 1.0, enlazada directamente
  desde `openligadb.de/lizenz`. Permite uso comercial y redistribución con
  atribución; si redistribuyes la base de datos (no solo tu app) como base
  de datos, aplica "share-alike".
- **Cobertura real**: ligas alemanas (1./2./3. Bundesliga, DFB-Pokal, y
  algunas copas/ligas juveniles). **No cubre La Liga, Premier League,
  Serie A, etc.** Ya es la fuente que usa el proyecto actual
  (`apps/workers/src/sportpulse_workers/jobs/openligadb.py`), así que es
  terreno conocido.
- **Mantenimiento**: el servidor funciona a donación (~50 €/mes según la
  propia web), lo paga la comunidad; riesgo de disponibilidad a largo
  plazo, pero sigue activo y actualizado a fecha de hoy.

### 2. football-data.org
- **Probado**: página de precios y Términos y Condiciones leídas
  directamente (texto completo de T&C del 2018, vigente).
- **Tier Free**: 12 competiciones, 10 peticiones/minuto, resultados y
  calendarios **retrasados**, tablas de clasificación. Sin alineaciones,
  goleadores, estadísticas (corners, tiros) — eso es un añadido de pago.
- **Obligación de atribución**: el texto exacto que exige incluir es
  *"Football data provided by the Football-Data.org API"*, visible en pie
  de página o "about".
- **Escudos de equipo**: el propio contrato dice que son propiedad de
  terceros y que **tienes que conseguir permiso tú mismo** para mostrarlos.
  No vienen "liberados" por usar la API.
- **Una clave = una app/dominio.** No pensada para repartir entre varios
  proyectos.
- **Tras cancelar**, ni siquiera puedes seguir mostrando datos ya obtenidos.

### 3. TheSportsDB
- **Probado en vivo con la clave pública gratuita `123`**:
  - `all_sports.php` — lista de deportes.
  - `search_all_leagues.php?s=Basketball` y `?s=Tennis` — **sí devuelve**
    ligas de baloncesto y tenis (ej. Argentine LNB, United Cup).
  - `searchteams.php?t=Real_Madrid` — funciona (contradice algún blog de
    terceros que decía que el free tier solo permite buscar "Arsenal").
  - `eventsnextleague.php`, `eventsseason.php`, `lookuptable.php` — todos
    responden con datos reales y actuales (temporada 2026/2027), incluidos
    escudos.
- **Términos de uso reales** (`thesportsdb.com/docs_terms_of_use.php`,
  actualizados 17/09/2026): *"You may use our API to lookup data and
  artwork for your development projects. You cannot publish apps to an
  appstore unless you are a paid subscriber."* — es decir, el tier gratis
  está pensado para desarrollo; publicar en una tienda de apps requiere
  pago. Para una web pública no hay prohibición literal, pero el espíritu
  del texto ("for your development projects") es ambiguo para un uso
  público/comercial continuado — **a confirmar con ellos antes de lanzar
  nada en producción**.
- **Licencia de imágenes mixta**: cada imagen tiene un campo
  `strCreativeCommons` (`Yes`/`No`/`Unknown`). Las marcadas `Unknown` o sin
  valor **no se pueden usar públicamente**, ni en capturas, ni en la app.
  Hay que filtrar por este campo antes de mostrar cualquier escudo/imagen.
- **Límite**: 30 peticiones/minuto con la clave gratuita.

### 4. balldontlie
- **Probado**: la web pública (planes y Términos de Servicio) se leyó
  completa. El endpoint real (`api.balldontlie.io/v1/teams`) devuelve
  `401 Unauthorized` sin clave — **hace falta crear una cuenta y generar
  una clave para comprobar el resto**, y crear cuentas no lo hago sin que
  lo pidas tú explícitamente (puedes hacerlo tú en balldontlie.io en 2
  minutos, es gratis).
- **Plan gratis**: 0 €/mes, **1 deporte a elegir**, 5 peticiones/min,
  acceso de datos "Basic" (no incluye todas las estadísticas avanzadas).
  Cobertura total del servicio: NBA, WNBA, NCAAB, NCAAW, EuroLeague y otras
  ligas de baloncesto, más NFL/MLB/NHL/NCAAF/MMA/PGA/Soccer/Tennis/Golf/
  Esports en los planes de pago superiores — **no está confirmado si
  "tenis" está disponible en el plan gratuito de 1 deporte** o solo en el
  plan "All-Access" (20+ ligas, 299,99 $/mes).
- **Términos de servicio — muy favorables**: permiten explícitamente *"any
  lawful personal or commercial purpose, including paid apps, media,
  analytics, AI, competing products, and resale"*, y dicen literalmente
  que **no se requiere atribución** para los usos permitidos. La única
  restricción relevante es que no puedes usar sus datos para montar una
  API de datos deportivos que compita directamente con la suya.
- **Conclusión**: es la fuente con mejores condiciones legales de las
  cuatro, pero antes de construir nada sobre ella hay que crear una cuenta
  gratuita y comprobar en el panel qué deporte se puede elegir en el tier
  gratis y qué trae exactamente "Basic" para baloncesto.

### 5. Jeff Sackmann `tennis_atp` / `tennis_wta` (histórico, GitHub)
- Es la fuente histórica más citada para datos de tenis ATP/WTA (rankings,
  resultados, estadísticas de partido) y durante años ha sido gratuita y
  abierta.
- **Comprobación de hoy**: la cuenta de GitHub `JeffSackmann` solo tiene
  **un** repositorio público ahora mismo
  (`tennis_MatchChartingProject`); `tennis_atp` y `tennis_wta` ya no
  aparecen como repos públicos de esa cuenta (devuelven 404 en la API de
  GitHub). Solo quedan *forks* de terceros (ej. `jasonmauss/tennis_atp`),
  desactualizados y sin fichero de licencia visible.
- **No la cuento como fuente disponible** hasta confirmar qué ha pasado
  (¿renombrada? ¿movida a una organización? ¿retirada?). No voy a construir
  nada sobre una fuente que no puedo verificar que siga publicada.

### 6. API-Football / api-sports.io
- Es la API de pago/freemium más citada para fútbol+baloncesto+tenis
  combinados (vía RapidAPI).
- **No pude verificarla**: la web devuelve `403` a peticiones automatizadas
  (protección anti-bot), y comprobar el plan gratuito real requiere
  registrarse en RapidAPI — no lo he hecho porque implica crear una cuenta,
  y eso te lo dejo a ti si quieres explorarla.
- La cito aquí solo como "pendiente de verificar", no como fuente
  confirmada.

## Deportes "otros" (más allá de fútbol/baloncesto/tenis)

TheSportsDB es, de las fuentes comprobadas, la única que cubre un abanico
amplio de deportes adicionales (motorsport, ciclismo, artes marciales,
béisbol, etc.) bajo la misma clave gratuita — con las mismas reservas de
términos de uso y licencia de imágenes ya explicadas arriba.

## Resolución de baloncesto y tenis (misma fecha, segunda sesión)

El usuario pidió explícitamente no crear cuentas ni pedir claves nuevas.
Eso descarta **balldontlie** por ahora (su endpoint real exige clave;
`GET /v1/teams` sin clave devuelve `401`) y **API-Football** (la web
bloquea el acceso automatizado, `403`). Con esa restricción, la única
fuente que queda para baloncesto y tenis sin registro es **TheSportsDB**
con la clave pública `123` — así que se verificaron sus endpoints reales
para ambos deportes en vez de quedarse con la duda:

- **Baloncesto (NBA, id de liga `4387`)**: `eventsnextleague.php` y
  `eventsseason.php` devuelven partidos reales (próximos y resultados,
  con marcador estructurado). `lookuptable.php` para la NBA **devuelve
  vacío** — esta fuente no tiene clasificación de la NBA. Implementado así
  de forma honesta: partidos sí, tabla no.
- **Tenis (ATP World Tour id `4464`, WTA Tour id `4517`)**: existen y
  devuelven eventos reales (ej. finales de Grand Slam, ATP 250/500). Pero:
  - No hay equipos/jugadores estructurados: solo texto libre
    (`strEvent`, `strResult`). Se implementó sin inventar un reparto de
    sets — se muestra el texto real tal cual.
  - `eventsnextleague.php` devuelve `{"events": null}` para ambos tours en
    el momento de la prueba — no hay "próximos partidos" que mostrar ahora
    mismo, y la web lo indica explícitamente en vez de dejarlo vacío sin
    explicación.
  - `eventsseason.php` para 2026 solo devolvió ~15 eventos para todo el
    año en ATP — cobertura real pero muy por debajo de una temporada
    completa (miles de partidos en la realidad). Es un límite de la
    fuente gratuita, no un error nuestro.
  - Durante las pruebas, varias peticiones seguidas devolvieron `HTTP 429`
    (límite de Cloudflare, más agresivo que el "30/min" documentado) — por
    eso el adaptador usa una caché en memoria (`sp_providers/base.py`) en
    vez de llamar a la fuente en cada petición.

**"Otros deportes" (motorsport, etc.)**: se dejó **fuera** de `SPORTS` en
`sp_providers/registry.py` a propósito. El adaptador de TheSportsDB es
genérico y probablemente funcionaría igual para motorsport u otro deporte
de la lista, pero no se verificó en vivo (la investigación se cortó por el
límite de tiempo pedido y por el `429` de la fuente) — así que no se activó
ninguna competición "otros" en la web para no afirmar algo no comprobado.

## Las cinco ligas nuevas (LaLiga, Premier League, Serie A, Ligue 1, Champions League)

Verificadas en vivo con la misma clave pública `123` de TheSportsDB, sin
cuenta nueva. IDs de liga confirmados uno a uno con `lookupleague.php`:
LaLiga `4335`, Premier League `4328`, Serie A `4332`, Ligue 1 `4334`,
Champions League `4480`.

- **`eventsseason.php` tiene un tope de ~15 eventos para toda la
  competición**, sin importar el deporte (ya lo habíamos visto en tenis;
  aquí se confirmó que también aplica a fútbol: La Liga 2026-2027 solo
  devolvió 15 partidos de toda la temporada). Demasiado poco para nada
  serio.
- **Solución real**: `eventsround.php?id=...&r=<ronda>&s=<temporada>` no
  tiene ese tope — devuelve la jornada completa (ej. 10 partidos en La
  Liga). El proveedor pide las primeras 11 jornadas una a una, con 0.3s
  de pausa entre cada una para no disparar el límite de ráfaga de
  Cloudflare (confirmado en vivo: aparece un `HTTP 429` real si se piden
  muchas seguidas sin pausa).
- **Clasificación**: `lookuptable.php` funciona igual que para La Liga en
  la sesión anterior — da clasificación real para las cinco, excepto
  **Champions League** (fase de grupos + eliminatorias, no hay tabla
  única; devuelve vacío, y así se refleja honestamente).
- **Bug real encontrado y arreglado en esta sesión**: cuando una petición
  fallaba (por el límite de ráfaga), el resultado vacío se guardaba en
  caché 15 minutos igual que un éxito — así que la web se quedaba
  mostrando "sin datos" mucho después de que el límite ya hubiera pasado.
  Ahora un fallo solo se cachea 20 segundos. Verificado en vivo: tras un
  `429` real, los datos volvieron solos 25 segundos después.

## Motor de predicción (probabilidad real, no cuotas)

El usuario pidió explícitamente no usar cuotas de apuestas inventadas,
sino probabilidad estadística real. Implementado en `packages/sp_predict`:

- Modelo de Poisson simple: fuerza de ataque/defensa de cada equipo en
  casa y fuera, relativa a la media de goles de la propia competición
  (calculada sobre los partidos reales ya obtenidos, nunca datos de otra
  fuente).
- Exige un mínimo de 3 partidos reales como local (resp. visitante) de
  cada equipo; si no hay suficiente muestra, devuelve "sin predicción"
  con el motivo exacto en vez de forzar un número.
- Probado en vivo con un partido real: Barcelona–Real Madrid (LaLiga,
  25/10/2026) → 82% victoria local, calculado con 4 partidos reales de
  cada equipo — el endpoint devuelve también cuántos partidos reales se
  usaron, para que quede claro que no es una cifra inventada.
- No incluye hándicaps, córners ni tarjetas: ninguna fuente gratuita
  verificada da esos datos, y el usuario pidió explícitamente no
  inventarlos.

## Estado final por deporte (implementado y verificado en vivo)

- **Fútbol**: ✅ 8 competiciones — LaLiga, Premier League, Serie A,
  Ligue 1, Champions League (TheSportsDB) + 1.Bundesliga, 2.Bundesliga,
  DFB-Pokal (OpenLigaDB). Partidos reales, clasificación real (excepto
  las dos copas/fase de grupos), predicción Poisson real cuando hay
  muestra suficiente.
- **Baloncesto**: ✅ NBA — próximos partidos y resultados recientes
  reales, con marcador. Sin clasificación. Predicción raramente
  disponible: el tope de 15 eventos de `eventsseason.php` apenas cubre un
  puñado de los 30 equipos de la NBA en un momento dado.
- **Tenis**: ✅ ATP Tour y WTA Tour — resultados reales recientes (texto
  libre), sin próximos partidos disponibles ahora mismo, sin
  clasificación, sin predicción (no hay nombres de jugador estructurados
  en esta fuente). Cobertura real pero escasa.
- **Otros deportes**: ⏳ pendiente. Arquitectura lista (mismo adaptador
  genérico), ninguna competición concreta verificada en vivo todavía.

## Siguiente paso de implementación

1. Activar "otros deportes" en `sp_providers/registry.py` solo después de
   verificar en vivo al menos una liga (ej. Fórmula 1) de la misma forma
   que se hizo aquí con las demás — no antes.
2. Si en algún momento quieres más cobertura (córners, tarjetas, cuotas
   reales de bookmaker, o mejorar baloncesto más allá del tope de 15
   eventos), la vía es que tú mismo crees la cuenta gratuita en
   football-data.org, api-football o balldontlie y me pases la clave —
   crear la cuenta en sí no es algo que yo pueda hacer por ti aunque lo
   autorices.
