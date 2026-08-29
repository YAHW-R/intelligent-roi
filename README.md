# Promesas — Promesa del día (Intelligent ROI)

Sistema que extrae las **promesas de Dios** de la Biblia completa (World English
Bible), las clasifica con un modelo local de IA y muestra una **promesa diaria**
en tu escritorio.

Proyecto compuesto de dos partes desacopladas:

1. **`bible-processor/`** — *Fase 1*: procesa el CSV de la Biblia, detecta y
   clasifica las promesas con **llama3.2:3b** (Ollama local) y las persiste en
   una base de datos **SQLite** (`promesas.db`). Es un proceso *offline* que se
   ejecuta una sola vez para construir la base de datos.
2. **`promise-cli/`** — *Fase 2*: pequeño binario **Go** que consulta
   `promesas.db` y devuelve la promesa del día de forma determinista. Es el
   motor que alimenta los widgets de escritorio (Waybar, Rofi, Eww, etc.).

---

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Fase 1 — Extracción y clasificación](#fase-1--extracción-y-clasificación)
  - [Ejecución local (Python)](#ejecución-local-python)
  - [Ejecución con Docker](#ejecución-con-docker)
  - [Nota sobre la base de datos](#nota-sobre-la-base-de-datos)
- [Fase 2 — CLI de la promesa del día](#fase-2--cli-de-la-promesa-del-día)
  - [Compilación](#compilación)
  - [Uso](#uso)
  - [Configuración](#configuración)
- [Modelo de datos](#modelo-de-datos)
- [Etiquetas de clasificación](#etiquetas-de-clasificación)
- [Solucionar problemas](#solucionar-problemas)

---

## Requisitos

**General:**
- Sistema operativo Linux (target: Omarchy / entornos tiling).
- **Ollama** instalado y en ejecución (`http://localhost:11434`), con el modelo:
  ```bash
  ollama pull llama3.2:3b
  ```

**Para la Fase 1 (procesador):**
- Opción A (local): **Python 3.10+** con `pandas` (`pip install pandas`).
- Opción B (Docker): **Docker** con Compose plugin.

**Para la Fase 2 (CLI):**
- **Go 1.27+** (solo si quieres recompilar el binario). El binario compilado
  `promesas-cli` ya está incluido y no requiere nada más.

---

## Estructura del proyecto

```
intelligent-roi/
├── bible-processor/            # Fase 1: pipeline de extracción
│   ├── bible-english.csv       # Biblia fuente (World English Bible, 31,103 versículos)
│   ├── candidates.py           # Heurística: filtra versículos candidatos a promesa
│   ├── prompt.py               # Plantilla del prompt y etiquetas canónicas
│   ├── classify.py             # Clasifica candidatos con Ollama → promesas.db
│   ├── sanitize.py             # Limpia etiquetas no canónicas de la DB
│   ├── run_pipeline.sh         # Encadena: candidates → classify → sanitize
│   ├── candidates.csv          # Salida intermedia (candidatos detectados)
│   ├── promesas.db             # Base de datos final (SQLite, archivo reutilizable)
│   ├── Dockerfile              # Imagen del pipeline
│   └── .dockerignore
├── promise-cli/                # Fase 2: CLI diario
│   ├── main.go                 # Flags, seed diario, salida JSON/texto
│   ├── config.go               # Lectura de la configuración TOML
│   ├── db.go                   # Consultas SQLite
│   ├── go.mod / go.sum
│   └── promesas-cli            # Binario estático compilado
├── docker-compose.yml          # Orquestación del pipeline en Docker
└── config.toml.example         # Plantilla de configuración del CLI
```

---

## Instalación

1. **Clona / copia** el proyecto en tu máquina.
2. **Instala Ollama** y descarga el modelo (si no lo tienes):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.2:3b
   ```
3. **Fase 1 — procesador** (eliges local o Docker, ver abajo).
4. **Fase 2 — CLI**: ya está compilado en `promise-cli/promesas-cli`. Opcional:
   instala Go y recompila (ver [Compilación](#compilación)).
5. **Configura el CLI** copiando la plantilla (ver [Configuración](#configuración)).

---

## Fase 1 — Extracción y clasificación

El pipeline hace tres pasos automáticamente:

1. **`candidates.py`** — filtra los 31,103 versículos a ~2,350 candidatos usando
   heurísticas por marcadores divinos (`I will …`, `I am the LORD`, `Don't be
   afraid`, `blessed …`, etc.). Rápido, sin LLM.
2. **`classify.py`** — envía cada candidato a `llama3.2:3b` (Ollama) y decide si
   es una promesa y con qué etiquetas clasificarla. Guarda el progreso cada
   50 versículos en la tabla `progreso` (reanudable ante interrupciones) y solo
   persiste las que sí son promesas.
3. **`sanitize.py`** — recorre `promesas.db` y elimina etiquetas inventadas por
   el modelo que no estén en el conjunto canónico (fallback a `hope`).

> **Rendimiento:** con `llama3.2:3b` el proceso completo (~2,350 candidatos)
> tarda **~1,5–2 horas**. Usa `--limit N` para probar con un lote pequeño.

### Ejecución local (Python)

```bash
cd bible-processor
./run_pipeline.sh          # proceso completo
# o
./run_pipeline.sh --limit 50   # prueba con los primeros 50 candidatos
```

Equivale a ejecutar a mano:

```bash
cd bible-processor
python3 candidates.py
python3 classify.py            # añade --limit 50 para probar
python3 sanitize.py --db promesas.db
```

### Ejecución con Docker

El pipeline está dockerizado para facilitar el lanzamiento y el control de
procesos. La base de datos **no** se guarda en un volumen Docker: se escribe
como **archivo plano** en el host mediante bind mount, reutilizable por el CLI
y por cualquier otra herramienta.

```bash
# Desde la raíz del proyecto
docker compose up --build                 # proceso completo
# o smoke test
docker compose run --rm extractor --limit 50
```

Requisitos del contenedor:
- **Ollama** debe estar corriendo en el host (`network_mode: host` lo enlaza
  directamente con `localhost:11434`).
- Corre con tu usuario del host (UID/GID 1000 por defecto) para que la DB
  conserve ownership correcto.

### Nota sobre la base de datos

`bible-processor/promesas.db` es la salida final: un archivo **SQLite simple y
portable** (~457 promesas, 48 libros al momento de la última generación).

- No dependes del contenedor para leerla: el CLI Go y cualquier otra herramienta
  pueden abrirla con `sqlite3` o cualquier driver SQLite.
- `docker compose up` **re-genera por completo** la DB (INSERT OR REPLACE). Si
  quieres conservar la generación actual, haz una copia antes:
  ```bash
  cp bible-processor/promesas.db promesas.db.bak
  ```

---

## Fase 2 — CLI de la promesa del día

Binario **Go estático** (compilado con `CGO_ENABLED=0`, sin dependencias en
runtime). Devuelve la promesa del día de forma **determinista**: usa la fecha
(`YYYY-MM-DD`) como semilla de un generador pseudoaleatorio, de modo que el
resultado **no cambia a lo largo del día** y cambia cada día.

### Compilación

Solo si quieres recompilar:

```bash
cd promise-cli
go mod download
CGO_ENABLED=0 go build -o promesas-cli .
```

### Uso

```bash
./promesas-cli --hoy             # salida en texto plano (por defecto)
./promesas-cli --hoy --texto     # salida en texto plano explícita
./promesas-cli --hoy --json      # salida JSON
```

Salida JSON de ejemplo:

```json
{"text":"\"'I will give peace in the land...","reference":"Leviticus 26:6","tags":["peace","protection"],"usuario":"Demo"}
```

**Manejo de errores silencioso:** si la configuración o la base de datos no
están disponibles, el CLI imprime `Descansa en Dios` y termina con código de
salida **0** (en lugar de un stack trace), para no romper tu barra de estado.

### Configuración

Copia `config.toml.example` a la ruta de configuración del CLI:

```bash
mkdir -p ~/.config/promesas
cp config.toml.example ~/.config/promesas/config.toml
```

Rutas y variables de entorno:
- Config: `~/.config/promesas/config.toml`
- Dir config alternativo: `$XDG_CONFIG_HOME/promesas` o `$PROMESAS_CONFIG`
- DB por defecto: `~/.config/promesas/promesas.db` (o `$PROMESAS_DB`)

Contenido del archivo:

```toml
usuario = "Tu Nombre"

# Etiquetas preferidas (en inglés). El CLI prioriza promesas que coincidan con
# cualquiera de estas. Vacío = elegir entre todas.
tags_preferidos = ["strength", "comfort"]

# Ruta absoluta a la base de datos SQLite. Si se omite, usa la ruta por defecto.
db_path = "/ruta/a/bible-processor/promesas.db"
```

---

## Modelo de datos

Esquema de `promesas.db`:

```sql
CREATE TABLE promesas (
    verse_id INTEGER PRIMARY KEY,   -- ID del versículo en la Biblia
    book     TEXT NOT NULL,         -- nombre del libro
    chapter  INTEGER NOT NULL,      -- capítulo
    verse    INTEGER NOT NULL,      -- número de versículo
    text     TEXT NOT NULL,         -- texto del versículo (inglés)
    tags     TEXT NOT NULL DEFAULT '[]'  -- etiquetas como JSON, máximo 2
);

-- Tabla de progreso del procesador (reanudación tras interrupción)
CREATE TABLE progreso (
    clave TEXT PRIMARY KEY,
    valor TEXT
);
```

---

## Etiquetas de clasificación

El modelo clasifica cada promesa con un **máximo de 2** etiquetas canónicas en
**inglés** (para evitar que el modelo traduzca). Si encaja en ninguna, usa
`hope` como fallback.

| Categoría | Etiquetas (inglés) |
|-----------|--------------------|
| Circunstancial | `provision`, `protection`, `healing`, `wisdom`, `justice` |
| Emocional | `peace`, `comfort`, `strength`, `companionship`, `hope` |
| Espiritual | `forgiveness`, `love`, `faith`, `salvation`, `purpose` |

Estos son los mismos tokens que se guardan en `promesas.db` y que debes usar en
`tags_preferidos` de la configuración.

---

## Solucionar problemas

- **Ollama no responde** en el pipeline/CLI:
  ```bash
  ollama list        # confirma que el modelo está
  curl http://localhost:11434/api/tags   # ¿responde el servidor?
  ```
- **El CLI muestra "Descansa en Dios":** revisa que `db_path` en tu config
  apunte a `bible-processor/promesas.db` o configura `PROMESAS_DB`; o que la
  base de datos exista y tenga promesas:
  ```bash
  sqlite3 promesas.db "SELECT COUNT(*) FROM promesas;"
  ```
- **`database is locked` al ejecutar `sanitize.py`:** el procesador estará
  escribiendo en la DB. Espera a que `classify.py` termine y vuelve a ejecutarlo.
- **Proceso interrumpido:** no hay problema, `classify.py` reanuda desde el
  último checkpoint con `python3 classify.py --resume`.
- **Etiquetas inesperadas en la DB:** ejecuta de nuevo `python3 sanitize.py`.

---

## Fase 3 — Integración (futuro)

El CLI está diseñado para integrarse fácilmente con el escritorio:

- **Waybar:** módulo `custom/promesa` que ejecuta `promesas-cli --hoy --texto`.
- **Rofi/Wofi/Eww:** consumen la salida `--json` para mostrar tarjetas y
  tooltips.

El CLI es independiente de la UI para que puedas integrarlo como prefieras.
