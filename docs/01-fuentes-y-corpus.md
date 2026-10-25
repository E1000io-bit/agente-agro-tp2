# Fuentes y corpus del agente

Qué hay en `data/corpus/`, de dónde sale, cómo se actualiza y qué limitaciones tiene.

## 1. Fichas de plagas — SINAVIMO (SENASA) · `data/corpus/sinavimo/` (70 fichas)

| | |
|---|---|
| **Qué es** | Sistema Nacional de Vigilancia y Monitoreo de plagas, portal oficial de información fitosanitaria; lo mantiene la Dirección de Información Estratégica Fitosanitaria (DIEF) del SENASA. Acceso libre y gratuito. https://www.sinavimo.gob.ar/acerca-de-sinavimo |
| **Cómo se obtuvo** | `scripts/descargar_sinavimo.py`. Las URLs salen del sitemap público (`/sitemap.xml`, 4.760 fichas de plagas al 25/10/2026). `robots.txt` permite `/plaga/*`. Pausa de 1,5 s entre pedidos. |
| **Selección** | 70 plagas/enfermedades/malezas de maíz, soja, trigo y maní de la región centro, definidas en `data/plagas_objetivo.csv`. |
| **Formato** | Markdown con frontmatter YAML (slug, nombres vulgares, tipo, condición, cultivos, URL, fecha de descarga) + una sección `##` por campo de la ficha. |
| **Secciones de cada ficha** | Nombre vulgar · Sinonimia · Tipo de plaga · Taxonomía · Condición (en Argentina) · Cultivos / Órgano afectado · Descripción biológica · Signos y síntomas / Daños · Condiciones predisponentes · Bibliografía |
| **Cobertura** | 69/70 con síntomas y descripción; **54/70 con "Condiciones predisponentes"** (las que sirven para el cruce con clima). |
| **Ojo** | *Spissistilus festinus* figura como **Ausente** en Argentina y su ficha es casi vacía: queda como caso de prueba ("¿está en Argentina?"). La bibliografía no se indexa en el RAG (agrega ruido) pero queda en el archivo para citar. |

**Ampliar el corpus:**
```bash
python scripts/descargar_sinavimo.py --slugs helicoverpa-armigera puccinia-helianthi   # sueltas
python scripts/descargar_sinavimo.py --todo --filtro-cultivo "Helianthus annuus"        # todo lo que afecte girasol (tarda >1 h)
```
Los slugs se pueden buscar en el sitemap (`grep -i "nombre" ` sobre la lista de URLs) o en el buscador del sitio.

**Composición actual (`data/catalogo_plagas.csv`):** 27 hongos, 26 insectos, 10 malezas, 3 virus, 1 bacteria, 1 fitoplasma, 1 nematodo, 1 ácaro. Por cultivo principal: soja 29, maíz 18, trigo 16, maní 3, varios 4.

## 2. Informes de la Red Nacional de Monitoreo de chicharrita · `data/corpus/chicharrita/` (10 informes)

| | |
|---|---|
| **Qué es** | Informes quincenales de la red de trampas de *Dalbulus maidis* (capturas por región y % de portación de *Spiroplasma*). |
| **De dónde** | Listado MAIZAR: https://www.maizar.org.ar/vertodas_area.php?id=39 (informes 2024–2026). Los primeros 21 también están en la página del INTA: https://www.argentina.gob.ar/inta/achaparramiento-del-maiz/red-nacional-de-monitoreo-informes |
| **Qué se bajó** | Los 10 más recientes: N° 42 a 50 y N° 52 (22/05/2026 → 20/10/2026; el N° 51 no figura en el listado de MAIZAR). PDF en `pdf/` + texto extraído en `.md` (con marcas `<!-- página N -->`). |
| **Actualizar** | `python scripts/descargar_informes_chicharrita.py --n 5` (salta los que ya existen). `--inta` agrega los 21 primeros. |
| **Ojo** | Los gráficos y mapas de los PDF no pasan al texto: el agente sólo "ve" lo escrito. Siempre debe decir número y fecha del informe. |

## 3. Fuentes que se usan "en vivo" (tools, no corpus)

| Fuente | Tool | Acceso |
|---|---|---|
| Open-Meteo (pronóstico, histórico ERA5, geocoding) | `clima_lote`, `clima_historico`, `geocodificar` | Sin key, uso no comercial ≤10.000 llamadas/día, CC BY 4.0 |
| crop.health (Kindwise) | `diagnosticar_cultivo` | API key; 100 créditos gratis |
| Pl@ntNet | `identificar_maleza` | API key gratuita con cuota diaria |
| AGROVOC (FAO) | `glosario` | Sin key |
| EPPO Global Database | `info_eppo` | Token gratuito (registro) |

Detalle de endpoints y ejemplos en `02-apis.md`.

## 4. Fuentes para citar / derivar (no se descargan)

| Fuente | Para qué | Link |
|---|---|---|
| Guía de Productos Fitosanitarios (CASAFE) | Derivar cuando piden productos o dosis (web con registro; app gratis) | https://www.casafe.org/publicaciones/guia-de-productos-fitosanitarios/ |
| Receta fitosanitaria | Justificar por qué el agente no receta | https://www.casafe.org/receta-fitosanitaria/ · Córdoba: Ley 9164 https://www.cba.gov.ar/wp-content/4p96humuzp/2013/05/9164-Agroqu%c3%admicos.pdf |
| Mapa de malezas REM Aapresid | Resistencias por partido/departamento (rojo confirmada, amarillo sospechada, naranja tolerancia), 200 partidos de 10 provincias, actualización ~bienal (última 2025). Es un visor web sin API: el agente debe **derivar** cuando preguntan "qué resistencias hay en mi zona" | https://www.aapresid.org.ar/rem-malezas/mapa-malezas/ |
| Consulta de status de plagas (SENASA) | Confirmar presencia oficial | https://www.argentina.gob.ar/senasa/portal-de-certificacion-fitosanitaria-de-exportacion/consulta-de-status-de-plagas-en-argentina |
| INTA Digital (repositorio) | Guías de manejo para ampliar el corpus a mano (PDF) | https://repositorio.inta.gob.ar |
| ORA — reservas de agua | Shapes semanales por cultivo (metadata desactualizada, última 2019) | https://datos.magyp.gob.ar/dataset/ora---reservas-agua-suelo |
| Estimaciones agrícolas | Contexto productivo por departamento (CSV) | https://datos.gob.ar/dataset?tags=maiz |

## 5. Ideas para ampliar el corpus (si sobra tiempo)

1. **Guías del INTA** de manejo de plagas de maíz/soja/trigo (PDF del repositorio INTA Digital) → copiar a `data/corpus/inta/` con el mismo frontmatter (`slug`, `titulo`, `url`, `fecha`, `cultivos_tp`) y reindexar. El indexador trata cualquier carpeta que no sea `sinavimo` como documento largo (ventanas de 1.200 caracteres).
2. **Girasol**: no lo cubre crop.health, pero SINAVIMO sí (`--filtro-cultivo "Helianthus annuus"`).
3. **Panorama Agrícola Semanal** (Bolsa de Cereales de Bs. As.) o **GEA** (Bolsa de Comercio de Rosario) para preguntas de coyuntura.
