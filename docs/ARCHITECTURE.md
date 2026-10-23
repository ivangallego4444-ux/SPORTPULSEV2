# SportPulse v2 — arquitectura simple (borrador inicial)

Objetivo: un sistema multideporte (fútbol, baloncesto, tenis, y otros a
futuro) con coste de infraestructura de **0 €/mes**, construido sobre fuentes
de datos gratuitas reales. Esta es la forma más simple que cubre el
requisito, no un diseño final.

## Idea central: un adaptador por fuente, un modelo común por encima

```
            +-------------------+
            |   apps/web        |   Next.js, dark mode, Framer Motion
            +---------+---------+
                      | HTTP/JSON
            +---------v---------+
            |   apps/api        |   FastAPI. Cachea en memoria (TTL) y
            |                   |   sirve /matches, /standings, /analysis
            +---------+---------+
                      |
      +---------------+----------------+
      |                                |
+-----v--------------+       +---------v-----------+
| packages/          |       | packages/sp_predict  |   Poisson real sobre
| sp_providers        |       | (forma, H2H,         |   los Match ya
| (openligadb,        |------>| predicción)          |   obtenidos — nunca
|  thesportsdb)        |      +----------------------+   llama a una fuente
+-----+---------------+                                  externa él mismo
      |
      v
+-----------------+
| packages/sp_core |   Modelos comunes: Match, StandingRow, FormResult,
|                  |   MatchPrediction, Competition — iguales para
|                  |   cualquier deporte
+------------------+
```

**Por qué así de simple:**
- Cada fuente externa tiene su propio formato, límites de peticiones y
  licencia. Aislar eso en un "adaptador" por fuente (carpeta
  `packages/sp_providers`) evita que esas diferencias contaminen el resto
  del sistema.
- `sp_core` define un modelo único (`Match`, `StandingRow`, `FormResult`,
  `MatchPrediction`) al que TODOS los adaptadores traducen. Añadir una
  liga nueva no obliga a rediseñar nada: ya se hizo cinco veces esta
  sesión (LaLiga, Premier League, Serie A, Ligue 1, Champions League)
  solo añadiendo configuración, no código nuevo.
- `sp_predict` nunca llama a una API externa — solo calcula sobre los
  `Match` que `apps/api` ya obtuvo para esa competición, así que no añade
  ni una petición más a una fuente ya limitada.
- La caché TTL en memoria (`packages/sp_providers/base.py`) sustituye a
  workers programados por ahora: es lo bastante simple para una fuente de
  datos gratuita con límites de ráfaga (ver docs/DATA_SOURCES.md), y
  evita construir infraestructura (cola, scheduler, base de datos) que
  esta versión no necesita todavía. `apps/workers` queda como carpeta
  reservada para cuando (si) haga falta ingesta programada de verdad.

## Por qué NO usar datos simulados mientras no hay fuente verificada

Para tenis en concreto, todavía no hay una fuente gratuita en vivo
verificada con licencia clara para uso comercial (ver
[DATA_SOURCES.md](./DATA_SOURCES.md)). La solución correcta es dejar ese
adaptador sin implementar y mostrarlo como "próximamente" en el producto,
no rellenarlo con datos falsos.

## Estado

Esta arquitectura ya está implementada para fútbol, baloncesto y tenis
(ver [README.md](../README.md) para cómo ejecutarla y qué muestra cada
deporte). "Otros deportes" queda como siguiente paso — ver la sección
final de [DATA_SOURCES.md](./DATA_SOURCES.md).
