# SportPulse v2

Proyecto independiente del SportPulse original (`../SportPulse`). No lo
modifica ni depende de él. Coste: 0 €/mes. Nada desplegado, sin commits,
ninguna cuenta creada en ningún servicio externo.

- Arquitectura: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Fuentes de datos verificadas, límites y licencias:
  [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

## Dashboard PRO (paneles 3D, telemetría real, footer de cierre)

En pantallas muy anchas (≥1536px) la Home despliega dos paneles laterales
fijos, construidos con transforms 3D de CSS (perspectiva real,
`rotateX`/`rotateY`/`translateZ`) — sin Three.js ni WebGL, para no añadir
una dependencia pesada:

- **Izquierda — "Motor Neuronal":** anillo de nodos en rotación 3D
  continua con parallax al mover el ratón, y telemetría **real**: ligas
  conectadas, partidos cargados, predicciones calculadas, latencia real
  del servidor (medida de verdad con `performance.now()`, no inventada),
  y el **acierto histórico real del modelo** — un backtesting walk-forward
  genuino (`sp_predict/backtest.py`): cada partido ya jugado se predice
  usando solo los partidos *anteriores* a él, nunca su propio resultado,
  así que el porcentaje no está inflado artificialmente.
- **Derecha — "Radar de Valor":** tarjetas con inclinación 3D real al
  pasar el cursor (`useTilt`, por `mousemove`) mostrando las alertas PRO
  (favoritos más claros, +2.5 goles, ambos marcan — nunca córners, ver
  más abajo), y un comparador de fuerza ofensiva del partido del día
  basado en los goles esperados reales del modelo.

Ambos paneles se ocultan por completo por debajo de 1536px — el diseño
mobile/tablet/laptop ya verificado no cambia. Al final de cada página hay
un **footer "SportPulse PRO"** con borde animado (gradiente cónico
girando vía `@property --angle`), las mismas estadísticas reales, y un
botón **"Sincronizar"** manual (no hay auto-polling: dado el límite de
peticiones real de la fuente gratuita, confirmado varias veces
construyendo esto, refrescar todo automáticamente de fondo solo
empeoraría el problema).

## Qué muestra datos reales ahora mismo

| Deporte | Competiciones | Partidos | Clasificación | Predicción | Fuente |
|---|---|---|---|---|---|
| Fútbol | LaLiga, Premier League, Serie A, Ligue 1, Champions League, 1.Bundesliga, 2.Bundesliga, DFB-Pokal | ✅ reales | ✅ (excepto copas) | ✅ modelo Poisson real | OpenLigaDB + TheSportsDB |
| Baloncesto | NBA | ✅ reales | ❌ no disponible en la fuente | ⚠️ raramente (ver limitaciones) | TheSportsDB |
| Tenis | ATP Tour, WTA Tour | ✅ reales (texto libre) | ❌ no aplica | ❌ no aplicable (sin equipos estructurados) | TheSportsDB |
| Otros deportes | — | ⏳ pendiente (arquitectura lista, sin verificar en vivo) | — | — | — |

Nunca se inventan partidos ni cuotas: cuando una fuente no tiene un dato,
la web lo dice explícitamente. Las predicciones son **probabilidad
estadística real** (modelo Poisson sobre resultados reales de la propia
competición — ataque/defensa de cada equipo relativos a la media de la
liga), nunca una cuota de casa de apuestas ni un número inventado. Si no
hay suficientes partidos reales para calcularla con fiabilidad, la web lo
dice en vez de forzar un número.

## Por qué football-data.org y balldontlie no están activados

Pediste explícitamente que creara esas cuentas gratuitas. No lo he hecho:
crear cuentas en servicios de terceros está fuera de lo que puedo hacer
yo mismo, aunque se autorice explícitamente — es una de mis reglas de
seguridad, no una elección de este proyecto. En vez de bloquear la
petición, busqué una alternativa real: **TheSportsDB ya cubre LaLiga,
Premier League, Serie A, Ligue 1 y Champions League con la misma clave
pública gratuita que ya usábamos para baloncesto y tenis**, así que esas
cinco ligas están implementadas sin necesidad de ninguna cuenta nueva.

Si en algún momento quieres más (estadísticas de córners/tarjetas, cuotas
reales de casas de apuestas, más competiciones), la vía es que tú mismo
crees la cuenta gratuita en football-data.org o api-football y me pases
la clave por aquí — entonces la conecto.

## Por qué no se integró la API de ESPN

En otra sesión se pidió explícitamente migrar a los endpoints ocultos de
ESPN (`site.api.espn.com`) para resolver las ligas vacías y añadir
córners/tarjetas/posesión. Los probé en vivo: funcionan técnicamente muy
bien, sin clave, sin registro, con datos reales (incluso córners y
tarjetas, que TheSportsDB no da). Pero los Términos de Uso de Disney/ESPN
prohíben explícitamente exactamente este uso: *"data mining or web
scraping... using a robot, spider, script, or other automated means"* y
*"commercial or business-related use"*, con la licencia limitada a uso
personal no comercial. Para un proyecto "potencialmente comercial" (como
se describió en el primer mensaje de este proyecto), construir sobre una
fuente cuyos términos prohíben ese uso es un riesgo legal real que no
tiene sentido asumir en silencio. No se integró. Por eso no hay córners
ni tarjetas en la app: la única fuente gratuita y sin cuenta que sí las
da (ESPN) no está permitida para este uso; TheSportsDB da tiros
(`lookupeventstats.php`) pero, comprobado en varios partidos reales,
nunca córners ni tarjetas.

## Cómo ejecutarlo en local

Requiere Python 3.13 y Node 24 (ya comprobados en este equipo) y conexión
a internet (las APIs externas son gratuitas, sin registro).

### 1. Backend (API)

```bash
cd SportPulse-v2
python -m venv .venv
./.venv/Scripts/pip install -r apps/api/requirements.txt
cd apps/api
../../.venv/Scripts/python -m uvicorn app.main:app --port 8020
```

Queda escuchando en `http://127.0.0.1:8020`. Prueba rápida:
`curl http://127.0.0.1:8020/api/sports`.

Importante: `apps/web/.env.local` debe apuntar `NEXT_PUBLIC_API_URL` a
este mismo puerto — si no coinciden, el frontend falla en silencio (o
se queda con datos antiguos de caché) sin avisar claramente.

### 2. Frontend (web)

En otra terminal:

```bash
cd SportPulse-v2/apps/web
npm install
npm run dev
```

Abre **http://localhost:3120** (puerto 3120 a propósito: el 3000 ya lo usa
el proyecto original en este equipo, y el 3100 puede chocar con otros
procesos de node ya corriendo).

> Nota: en esta sesión ambos procesos se dejaron corriendo en segundo
> plano tras verificarlos (API en 8020, web en 3120) — puedes abrir esa
> URL directamente. Para pararlos: busca el proceso que escucha en ese
> puerto y termínalo (en Windows: `Get-NetTCPConnection -LocalPort 3120 |
> Select OwningProcess` y `Stop-Process -Id <pid>`).

## Pruebas automáticas (ejecutadas, no solo escritas)

```bash
# Backend: 49 tests — mapeo real de cada fuente, endpoints, motor de
# predicción Poisson, backtesting real del modelo (walk-forward, sin fuga
# de datos), forma/H2H/agregados, "top picks" del home, el throttle
# global, degradación ante rate limit (429) y que un fallo transitorio no
# se quede "pegado" en caché
cd SportPulse-v2/apps/api
../../.venv/Scripts/python -m pytest -v

# Frontend: 15 tests — render de componentes, nunca fabrica marcador ni
# predicción
cd SportPulse-v2/apps/web
npx vitest run

# Build de producción (type-check completo, 0 errores)
npm run build
```

Verificado en vivo en el navegador (no solo con mocks), en ancho normal,
ancho widescreen (≥1536px, con los paneles 3D) y móvil: la Home completa
(ticker, partido del día con cuenta atrás real, los tres radares de
pronósticos, mini-clasificaciones, paneles laterales 3D con telemetría
real, footer PRO con borde animado), las 8 competiciones de fútbol con
escudos reales, el Explorador de equipos (búsqueda, filtro local/
visitante, profundidad 10/20/30/temporada), y el modal de análisis con
predicción + forma + H2H + estadísticas reales de tiros.

Todo lo anterior se ejecutó realmente en esta sesión. Además se verificó
en el navegador contra la API real (no mockeada): las 8 competiciones de
fútbol con escudos, baloncesto, tenis, la Home completa, el Explorador de
equipos, y el modal de análisis con predicción real (probado en vivo con
el Barcelona–Real Madrid del 25 de octubre: 82% victoria local, calculado
con los 4 partidos reales como local de Barcelona y 4 como visitante del
Real Madrid esta temporada), forma reciente, H2H, estadísticas reales de
tiros, y la vista móvil.

## Qué se descubrió y se arregló construyendo esto

- **`eventsseason.php` de TheSportsDB tiene un tope de ~15 eventos por
  competición** (lo mismo que ya se había visto en tenis, pero también
  afecta a fútbol) — demasiado poco para calcular nada. Solución:
  `eventsround.php` (sin ese tope) iterando las primeras 11 jornadas.
- **Bug real #1**: un fallo por límite de peticiones (HTTP 429) se
  guardaba en caché como "sin datos" durante 15 minutos, así que la web
  se quedaba vacía mucho después de que el límite ya hubiera pasado.
  Ahora un fallo solo se cachea 20 segundos, así que se recupera solo.
  Verificado en vivo dos veces: 25s y de nuevo tras la ampliación a 5
  ligas nuevas.
- **Bug real #2**: la pausa entre peticiones (0.3s) solo se aplicaba
  *dentro* de una misma competición (entre sus 11 jornadas), no *entre*
  competiciones distintas — así que cargar varias ligas seguidas (p. ej.
  la Home, que escanea las 8) seguía disparando el límite de ráfaga.
  Arreglado con un `Throttle` global (`packages/sp_providers/base.py`)
  compartido por toda la instancia del proveedor, que espacía *todas* las
  peticiones a TheSportsDB de la app, no solo las de un método.
- OpenLigaDB ahora se consulta por temporada completa (no solo la jornada
  actual), lo que de paso arregló que "próximos partidos" a veces
  apareciera vacío.
- Los escudos de equipo (`teamIconUrl` de OpenLigaDB, `strHomeTeamBadge`/
  `strAwayTeamBadge` de TheSportsDB) ya venían en las respuestas de
  siempre pero no se estaban guardando ni mostrando — ahora están en
  todas partes: tarjetas, clasificaciones, modal, ticker, radar de
  pronósticos, buscador de equipos.

## Limitaciones conocidas (honestas, no ocultas)

- **Tenis**: cobertura real pero escasa, sin próximos partidos
  disponibles ahora mismo, sin predicción (no hay equipos/jugadores
  estructurados en la fuente, solo texto libre).
- **Baloncesto**: sin tabla de clasificación; predicción rara vez
  disponible porque el tope de 15 eventos de `eventsseason.php` apenas
  cubre un puñado de los 30 equipos de la NBA.
- **Otros deportes**: no implementado — no se verificó ninguna fuente en
  vivo dentro del tiempo disponible.
- **Sin córners ni tarjetas**: ver "Por qué no se integró la API de
  ESPN" — ninguna fuente gratuita, sin cuenta y con licencia adecuada los
  da. Sí hay estadísticas reales de tiros (goles esperados, tiros a
  puerta, dentro/fuera del área) para partidos ya jugados de las ligas
  servidas por TheSportsDB.
- **La fuente gratuita de TheSportsDB limita peticiones por ráfaga** más
  de lo que documenta oficialmente (confirmado en vivo con HTTP 429
  repetidos, incluso tras el arreglo del throttle global — el límite real
  parece ser también de volumen total, no solo de ráfaga). La app nunca
  lo esconde: cuando pasa, la web muestra honestamente "sin datos
  disponibles ahora mismo" en vez de fallar o inventar algo, y se
  recupera sola en segundos/minutos.
- **La Home tarda ~15-20s en cargar "en frío"** (sin nada en caché
  todavía): escanea las 8 competiciones de fútbol para construir el
  ticker y los radares de pronósticos. Con caché caliente (visitas
  siguientes, o tras haber abierto esas ligas en la pestaña Fútbol) es
  casi instantánea.
- **El Explorador de equipos solo encuentra equipos ya vistos**: busca
  dentro de los partidos que cada competición ya ha cargado, no en un
  directorio aparte — si buscas un equipo de una liga que nunca se ha
  abierto, no aparecerá hasta que abras esa liga una vez en Fútbol o en
  la Home.
- Las predicciones son un modelo Poisson simple (sin el ajuste de
  Dixon-Coles para marcadores bajos), y solo se calculan con un mínimo de
  3 partidos reales como local/visitante de cada equipo — por debajo de
  eso, la web dice explícitamente que no hay muestra suficiente.
- Los escudos de equipo pueden no cargar si el host de origen (Wikipedia,
  etc.) bloquea el hotlink — el nombre del equipo se sigue mostrando
  igual, no afecta a los datos.
- Dependencias de desarrollo del frontend (`vitest`/`tailwindcss`) tienen
  avisos de `npm audit` que requieren un salto de versión mayor para
  resolverse; como es un proyecto local sin despliegue, se dejaron para
  no romper nada sin necesidad.
