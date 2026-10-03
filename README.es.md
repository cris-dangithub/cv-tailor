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

## Tus datos

- **El pool es tuyo y se queda donde está.** La skill solo guarda su ubicación y nunca escribe en él.
- **Todo lo que la skill produce vive en tu espacio de trabajo**, nunca en este repositorio:
  configuración, aplicaciones, hechos y preferencias aprendidos, perfil de voz, tus estilos.
- Un espacio de trabajo = una persona. Otra persona = otra carpeta.

## Desarrollo

```bash
python skills/cv-tailor/cvt.py setup-env --dev
skills/cv-tailor/.venv/Scripts/python -m pytest tests      # bin/python en macOS/Linux
```

## Licencia

MIT. Las fuentes Montserrat incluidas usan la SIL Open Font License 1.1.
