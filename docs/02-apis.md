# APIs externas — referencia rápida

Estado al 25/10/2026: ✅ probado con respuesta real · 🔑 endpoint verificado (responde 401/403 sin credencial), falta probar con key.

## Open-Meteo ✅ (sin key)

Pronóstico — `GET https://api.open-meteo.com/v1/forecast`
```
?latitude=-33.13&longitude=-64.35&forecast_days=7&timezone=America/Argentina/Cordoba
&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,
       et0_fao_evapotranspiration,leaf_wetness_probability_mean,vapour_pressure_deficit_max
&hourly=soil_moisture_3_to_9cm,soil_moisture_9_to_27cm,soil_temperature_6cm
```
Respuesta (recorte real, Río Cuarto, 25/10/2026):
```json
"daily": {"time": ["2026-10-25","2026-10-26","2026-10-27"],
  "temperature_2m_max": [17.3, 20.7, 17.8], "precipitation_sum": [0.0, 0.0, 15.1],
  "leaf_wetness_probability_mean": [31, 28, 72], "relative_humidity_2m_mean": [69, 70, 83]}
```
- Histórico (ERA5, desde 1940): `GET https://archive-api.open-meteo.com/v1/archive?...&start_date=2026-09-01&end_date=2026-09-30&daily=...` (sin `leaf_wetness_probability_mean`).
- Geocoding: `GET https://geocoding-api.open-meteo.com/v1/search?name=Río Cuarto&countryCode=AR&language=es`
- Uso no comercial gratis hasta 10.000 llamadas/día; atribución CC BY 4.0. Docs: https://open-meteo.com/en/docs
- Implementado en `agente/tools/clima.py` (devuelve además indicadores: lluvia total, días con HR ≥ 80 %, días con mojado de hoja ≥ 60 %).

## crop.health (Kindwise) 🔑

- `POST https://crop.kindwise.com/api/v1/identification?details=common_names,type,description,symptoms,treatment,severity,spreading,eppo_code&language=es`
- Header `Api-Key: <CROP_HEALTH_API_KEY>`; body JSON:
```json
{"images": ["<jpg en base64>"], "similar_images": false, "latitude": -33.13, "longitude": -64.35}
```
- Respuesta: `result.is_plant.probability`, `result.crop.suggestions[]`, `result.disease.suggestions[]` (cada una con `name`, `scientific_name`, `probability`, `details`).
- Detalles disponibles: common_names, type, taxonomy, gbif_id, eppo_code, eppo_regulation_status, wiki_url, wiki_description, image(s), description, treatment, symptoms, severity, spreading.
- Cultivos (23): manzana, banano, cebada, yuca, cítricos, cacao, café, **maíz**, algodón, pepino, berenjena, ajo, vid, palma aceitera, cebolla, **papa**, arroz, **soja**, caña de azúcar, té, tabaco, tomate, **trigo**. No cubre girasol ni maní.
- Precio: 100 créditos gratis al registrarse (1 identificación = 1 crédito); después desde €0,05/crédito. https://kindwise.com/pricing
- Fuente de los endpoints: código del cliente oficial `kindwise-api-client` (PyPI). Implementado en `agente/tools/imagen.py` sin depender del SDK, **con caché** en `.cache/imagen/`.
- El campo `treatment` trae recomendaciones genéricas del proveedor: el agente NO las debe pasar como receta (ver guardrails).

## Pl@ntNet 🔑

- `POST https://my-api.plantnet.org/v2/identify/all?api-key=<PLANTNET_API_KEY>&lang=es&nb-results=5` (multipart: `images`, `organs=auto`)
- Respuesta: `bestMatch`, `results[].score`, `results[].species.scientificNameWithoutAuthor`, `commonNames`, `family`.
- Identifica **especies**, no enfermedades → usarlo para malezas. Cuota diaria por usuario (`GET /v2/quota/daily`). https://my.plantnet.org/doc/api/quota
- Existe un servidor MCP de referencia: https://github.com/OrHavraPerry/plantnet-mcp

## AGROVOC (FAO) ✅ (sin key)

- Búsqueda: `GET https://agrovoc.fao.org/browse/rest/v1/search/?query=roya*&lang=es&maxhits=5`
- Concepto: `GET https://agrovoc.fao.org/browse/rest/v1/agrovoc/data?uri=<uri>&format=application/ld%2Bjson`
- SPARQL: `https://agrovoc.fao.org/sparql`
- Ejemplo real: "roya" → `c_6710` (en: *rusts*), más amplio: *Enfermedad fungosa*, más específicos: roya amarilla, roya del tallo… "umbral económico" → `c_24921` (en: *economic thresholds*).
- Limitación: no tiene muchos nombres vulgares rioplatenses ("chicharrita" no aparece) → para eso está el diccionario de nombres vulgares que arma el retriever con las fichas.

## EPPO Global Database 🔑

- Registro gratis en https://data.eppo.int → token. Rutas v1.0 (verificadas, 403 sin token válido):
  - `GET https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}?authtoken=...`
  - `GET https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}/hosts?authtoken=...`
  - `GET https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}/distribution?authtoken=...`
  - `POST https://data.eppo.int/api/rest/1.0/tools/names2codes` (form `intext`, `authtoken`)
- Contenido: >97.800 especies con códigos EPPO, >1.900 plagas reguladas con hospederos y distribución, >15.000 fotos. https://eppo.int/RESOURCES/eppo_databases/global_database
- Es opcional para el TP (las fichas SINAVIMO ya traen hospederos para Argentina).

## NASA POWER ✅ (alternativa de clima, sin key)

- `GET https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&latitude=-31.4&longitude=-64.2&start=20260901&end=20260930&format=JSON`
- Comunidad `AG` = agroclimatología (pensada para modelos tipo DSSAT). No implementado como tool; sirve como backup o para comparar.
