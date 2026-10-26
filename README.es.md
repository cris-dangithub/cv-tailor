# cv-tailor

*[Read in English](README.md)*

Una skill para agentes (Claude Code y Codex) que convierte **tu pool de conocimiento** y **una
oferta de trabajo** en una hoja de vida a medida, en PDF, en todos los idiomas que elijas y
escrita como escribes **tú**. Nunca inventa un dato.

```
tú:     [pegas una o varias ofertas, o sus links]
agente: 000014 Acme Mobility — Analytics Engineer → CV-AlexRivera-AcmeMobility-EN.pdf, -ES.pdf
        coincidencias fuertes · huecos y cómo defenderlos · qué quedó fuera y por qué · pendientes
```

## Qué hace

- **Genera** un CV por oferta e idioma (n ofertas × z idiomas), solo con tu pool: archivos,
  carpetas, links, GitHub. Lo que falta lo pregunta una vez y lo recuerda.
- **Escribe con tu voz**, medida sobre textos tuyos, con comprobaciones numéricas (longitud de
  frase, primera persona, señales de IA) en vez de opiniones.
- **Numera y guarda** cada aplicación (`applications/000001-empresa-cargo/`) con la oferta, el
  razonamiento, el YAML editable, el HTML y el PDF.
- **Encuentra lo que enviaste**: pegas el correo del reclutador y te dice qué CV le llegó.
- **Lleva el estado**: enviada, respondida, entrevista, rechazada, oferta.
- **Aprende** de tu feedback ("de la 000012 no me gustó…") sin apartarse de lo que pide cada oferta.
- **Alimenta tu base de conocimiento**: si tu pool lo gestiona su propia skill y permite
  actualizarlo, lo que confirmas al preparar un CV se guarda ahí a través de esa skill,
  automáticamente, sin duplicar, y se puede deshacer.
- **Mantiene un reporte por postulación** (`report.md`), escrito para ti: estado, tus CVs, qué se
  decidió y por qué, las preguntas que se te hicieron y tus respuestas.
- **Estilos**: uno por defecto, medido, o uno nuevo copiado de cualquier CV que te guste (medido,
  comparado lado a lado y aprobado por ti). Se mantiene el último que elegiste.

## Instalación

Requisitos: Python 3.9+ y Chrome, Edge, Chromium o Brave (cualquiera). Opcional: `gh` (GitHub como
fuente del pool) y LibreOffice (CVs de ejemplo en DOCX para estilos nuevos).

**Claude Code, como plugin**

```
/plugin marketplace add cris-dangithub/cv-tailor
/plugin install cv-tailor@cv-tailor
```

**Codex y/o Claude Code, desde un clon**

```bash
git clone https://github.com/cris-dangithub/cv-tailor
cd cv-tailor
./install.sh            # Windows: .\install.ps1
```

Enlaza `skills/cv-tailor` en `~/.codex/skills` y `~/.claude/skills` y crea el entorno de la skill.
También puedes copiar `skills/cv-tailor` dentro del `.claude/skills/` de un proyecto.

**Las dependencias** están en `skills/cv-tailor/requirements.txt` y se instalan en el venv propio
de la skill (`skills/cv-tailor/.venv`, ignorado por git) con pipenv. La skill lo hace sola la
primera vez; a mano es:

```bash
cd skills/cv-tailor
PIPENV_VENV_IN_PROJECT=1 pipenv install -r requirements.txt     # igual en Windows (el .env define la variable)
```

o simplemente `python skills/cv-tailor/cvt.py setup-env`.

## Primer uso

Abre tu agente en una carpeta vacía: esa carpeta será tu **espacio de trabajo**. Pega una oferta
(o di "configura cv-tailor"). La configuración pregunta, en este orden:

1. en qué idioma quieres que te hable (se pregunta en inglés; todo lo demás sigue en tu idioma);
2. en qué idiomas quieres tus CVs (p. ej. inglés, español, indonesio);
3. dónde está tu pool de conocimiento (carpetas, archivos, links, `github:<usuario>`); también
   busca skills dentro del pool para leerlo con ellas;
4. opcionalmente, un CV cuyo diseño quieras copiar.

Desde ahí, en esa carpeta, basta con pegar una oferta.

## App web

Lo mismo desde el navegador, o desde el móvil, en lugar de una ventana de chat:

```bash
python skills/cv-tailor/cvt.py setup-env --web    # una vez
python skills/cv-tailor/cvt.py web                # dentro de tu espacio de trabajo: http://127.0.0.1:8765
python skills/cv-tailor/cvt.py web --lan          # también el móvil en la misma Wi-Fi (dirección + QR)
python skills/cv-tailor/cvt.py web --public       # desde cualquier sitio, detrás de un túnel como `ngrok http 8765`
```

**Cuentas.** Todo el mundo inicia sesión, y la sesión dura hasta que se cierra.

- El superusuario se define con `CVT_ADMIN_USER` y `CVT_ADMIN_PASSWORD`, como variables de
  entorno o en `<workspace>/.cv-tailor/web/.env`.
- Si no se definen, es `admin` / `admin`, y entonces `--lan` / `--public` no arrancan.
- Cualquiera puede crear una cuenta. La primera queda activa al momento; las siguientes
  esperan a que el superusuario las apruebe en la pantalla Usuarios.

- **Escritorio**: pega una o varias ofertas o enlaces. Cada una tiene su propia sesión del
  agente, y hasta N trabajan en paralelo.
- **Aplicaciones**: índice y tablero por estado, búsqueda y cambios de estado con nota.
- **Aplicación**: el recorrido de estados, el CV por idioma y versión, el informe, la oferta y
  el feedback, que continúa la misma sesión.
- **Documentos**: todos los PDF. Puedes verlos, descargarlos o bajar una selección en ZIP.
- **Conversaciones**: las respuestas llegan en vivo, los pasos con herramientas se pliegan, las
  preguntas del agente se responden ahí mismo, y lo que está fuera de la lista blanca espera a
  que lo apruebes en una tarjeta.
- **Estilos y ajustes**: cambia de estilo o crea uno a partir de un CV de muestra. Elige el
  modelo (Opus 5.5 por defecto), el esfuerzo (alto o medio, también por mensaje), la ventana de
  compactación (pequeña por defecto, para que los chats salgan baratos), la concurrencia y el
  idioma (inglés, español o indonesio).

Usa **Claude Code** directamente, con tu propia sesión y sin API key, así que `claude` tiene que
estar instalado y con sesión iniciada (`claude auth login`; la sesión de la app de escritorio no
sirve para la CLI). La interfaz viene ya compilada: Node solo hace falta para modificarla.
Detalles: `skills/cv-tailor/references/web.md`.

## Tus datos

- **El pool es tuyo y se queda donde está.** La skill solo guarda su ubicación y nunca escribe en él;
  solo la skill que gestiona tu pool puede actualizarlo, si sus reglas lo permiten, y cada cambio
  se puede deshacer. Se desactiva con `pool.writeback: off`.
- **Todo lo que la skill produce vive en tu espacio de trabajo**, nunca en este repositorio:
  configuración, aplicaciones, hechos y preferencias aprendidos, perfil de voz, tus estilos.
- Un espacio de trabajo = una persona. Otra persona = otra carpeta.

## Desarrollo

```bash
python skills/cv-tailor/cvt.py setup-env --dev
skills/cv-tailor/.venv/Scripts/python -m pytest tests      # bin/python en macOS/Linux
```

Interfaz web (requiere Node 20+): con `cvt web` corriendo en un espacio de trabajo,
`npm --prefix skills/cv-tailor/web/ui run dev` sirve la interfaz con recarga en caliente en :5173
y redirige `/api` al servidor. Haz commit del resultado de `npm --prefix skills/cv-tailor/web/ui
run build` (`web/ui/dist`), que es lo que reciben los usuarios.

## Licencia

MIT. Las fuentes Montserrat incluidas usan la SIL Open Font License 1.1.
