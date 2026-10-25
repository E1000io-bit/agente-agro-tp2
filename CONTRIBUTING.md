# Cómo trabajamos en el repo

Objetivo: que cualquiera del grupo pueda ver **qué se cambió, quién lo hizo, por qué y con qué resultado**.

## 0. Puesta en marcha (una sola vez)

- El dueño del repo invita al resto en **Settings → Collaborators**.
- Proteger `main` en **Settings → Branches → Add rule**: *Require a pull request before merging* (1 aprobación) y *Require status checks to pass* → `offline`.
- Crear las etiquetas y los issues iniciales: `bash scripts/crear_issues_iniciales.sh` (necesita la [CLI de GitHub](https://cli.github.com) y `gh auth login`).
- Cada integrante: `git clone`, crear el entorno (ver README → Arranque rápido) y copiar `.env.example` a `.env`.

## 1. Flujo de trabajo

1. **Toda tarea es un issue.** Antes de empezar algo, abrir (o tomar) un issue con la plantilla "Tarea" y asignárselo.
2. **Una rama por issue**, creada desde `main` actualizado:
   ```bash
   git switch main && git pull
   git switch -c feat/12-loop-agente        # tipo/numero-de-issue-descripcion-corta
   ```
   Tipos de rama: `feat/` (funcionalidad), `fix/` (corrección), `data/` (corpus o índice), `eval/` (evaluaciones), `docs/` (documentación).
3. **Commits chicos y descriptivos** (ver §2).
4. **Pull Request a `main`** con la plantilla completa y `Closes #12` para que el issue se cierre solo.
5. **Al menos 1 revisión** de otro integrante antes de mergear. El CI (tests offline) tiene que estar en verde.
6. Merge con **squash** para que `main` quede con un commit por PR.

`main` siempre tiene que funcionar: nadie hace push directo.

## 2. Mensajes de commit

Formato: `tipo(área): qué cambia` en presente, en español.

| tipo | cuándo | ejemplo |
|---|---|---|
| `feat` | funcionalidad nueva | `feat(agente): loop ReAct con LangGraph` |
| `fix` | corrección | `fix(rag): filtro de cultivo ignoraba "maní"` |
| `data` | cambios en `data/corpus` o en el índice | `data(chicharrita): informes 53 y 54` |
| `eval` | sets de prueba o resultados | `eval: resultados agente v1 vs baseline` |
| `docs` | documentación | `docs: decisión de usar BM25` |
| `chore` | configuración, dependencias, CI | `chore: agrega pytest al CI` |

Áreas: `agente`, `rag`, `tools`, `corpus`, `eval`, `ui`, `docs`, `ci`.

## 3. Reglas para datos y resultados (trazabilidad)

- **Corpus:** no editar a mano los `.md` de `data/corpus/`; se regeneran con los scripts. Si se actualiza, hacerlo en un commit `data(...)` propio, reindexar (`python -m agente.rag.indexar`) en el mismo commit y anotar en `CHANGELOG.md` qué se agregó y la fecha de descarga.
- **Resultados de evaluación:** guardar el `.jsonl` en `data/eval/` con un nombre que diga qué se evaluó (`resultados_<config>_<AAAAMMDD>.jsonl`) y copiar la tabla de métricas en `docs/04-evaluacion.md`. Nunca pisar resultados viejos: son la evidencia de cómo mejoró el agente.
- **Decisiones de diseño:** cada decisión que cambie cómo funciona el agente (modelo, framework, chunking, guardrails) se agrega a `docs/06-decisiones.md` con fecha, alternativas y motivo.
- **API keys:** sólo en `.env` (está en `.gitignore`). Si alguien sube una por error, avisar y rotarla: borrarla en un commit nuevo no alcanza porque queda en el historial.

## 4. Antes de abrir el PR

```bash
python tests/test_offline.py          # lo mismo que corre el CI
python scripts/evaluar_retriever.py   # si tocaste rag/ o corpus/: pegá el resultado en el PR
```

## 5. Versiones

Cuando se cierra una etapa (entrega parcial, demo), crear un tag y anotarlo en `CHANGELOG.md`:
```bash
git tag -a v0.2.0 -m "Agente con loop y tools de imagen" && git push --tags
```
