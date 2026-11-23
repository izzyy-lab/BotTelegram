# 🎬 CAMovies

Bot de Telegram que recomienda películas según tus gustos. Se presenta como **Cam** y cada
recomendación llega con su **calificación**, sus **géneros** y un **resumen sin spoilers**.

Los datos vienen de [TMDb](https://www.themoviedb.org) (The Movie Database).

---

## ✨ Qué hace

| Característica | Descripción |
|----------------|-------------|
| 🎯 **Recomendación por gustos** | Entiende texto libre: _"quiero algo de terror y misterio"_, _"una comedia romántica para hoy"_ |
| 🎬 **Parecidas a una que te gustó** | _"me gustó la película Submarine, ¿me recomiendas alguna parecida?"_ |
| 🎛️ **Menú de géneros** | 18 géneros en botones, por si no quieres escribir |
| ⭐ **Calificación** | Nota de TMDb sobre 10, en estrellas, con el número de votos |
| 🖼️ **Portada** | Manda la imagen del póster con la ficha al pie |
| 📖 **Resumen sin spoilers** | Solo el planteamiento de la historia, nunca el desenlace |
| 🖼️ **Portada** | La imagen de la película, con la ficha completa como pie de foto |
| 🎞️ **Parecidas a una que te gustó** | Nómbrale una película y te busca similares |
| 🎲 **Sorpréndeme** | Si no sabes qué ver: las mejor calificadas de la historia, o joyas ocultas |
| 🔁 **Sin repetir** | Recuerda lo que ya te mostró en la conversación |
| ✅ **Filtro de calidad** | Solo películas con nota ≥ 6.5 y al menos 300 votos |

---

## 🛠️ Tecnologías

| Tecnología | Propósito |
|------------|-----------|
| **Python 3.11+** | Lenguaje |
| **python-telegram-bot ≥22** | Framework del bot (la rama 20.x no funciona en Python 3.13+) |
| **httpx** | Cliente HTTP asíncrono para la API de TMDb |
| **TMDb API v3** | Catálogo, calificaciones y sinopsis en español |

---

## 📦 Instalación

```bash
git clone https://github.com/rubisabel00/machine-learning-Bot-telegram.git
cd machine-learning-Bot-telegram
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 1. Token de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) y envía `/newbot`
2. Nombre: `CAMovies` · username: el que quieras
3. Guarda el token

### 2. API key de TMDb (gratis)

1. Crea una cuenta en [themoviedb.org](https://www.themoviedb.org)
2. Entra a **Ajustes → API** y solicita una key de uso personal
3. Copia la **API Key (v3 auth)**

### 3. Guardar las claves

Copia `.env.ejemplo` como `.env` y escribe ahí tus dos valores:

```env
TMDB_API_KEY=tu_api_key_de_tmdb
TELEGRAM_TOKEN=tu_token_de_telegram
```

El `.env` está en `.gitignore`, así que no se sube al repositorio. Si prefieres variables
de entorno, también funcionan y tienen prioridad sobre el archivo.

### 4. Ejecutar

Activa primero el entorno virtual (con el Python del sistema da `No module named telegram`):

```powershell
.venv\Scripts\Activate.ps1
python bot.py
```

```
CAMovies (Cam) corriendo... esperando mensajes
```

---

## 🎯 Uso

| Comando | Qué hace |
|---------|----------|
| `/start` | Cam se presenta y muestra el menú de géneros |
| `/sorpresa` | No sabes qué ver: Cam elige. `/sorpresa mejores` o `/sorpresa joyas` |
| `/recomendar` | Igual que `/sorpresa`, o con género: `/recomendar terror` |
| `/ayuda` | Lista de comandos |

También puedes escribirle directamente qué quieres ver.

### Ejemplo de respuesta

Cada película llega como una foto de su portada, con la ficha en el pie de la imagen:

```
🎯 Para tu gusto (Terror 👻, Misterio 🕵️):

[ 🖼️ portada ]
🎬 El Conjuro (2013)
⭐⭐⭐⭐ 7.5/10 · 12840 votos
🏷️ Terror, Misterio, Suspenso
📖 Sin spoilers: Una familia se muda a una granja apartada y empiezan a
ocurrir cosas inexplicables. Llaman a dos investigadores de lo paranormal. […]

           [🔁 Mas de esto]
           [🎲 Otro genero]
```

---

## 📁 Estructura

```
CAMovies/
├── bot.py             # Handlers de Telegram, menús y presentación de Cam
├── tmdb.py            # Consulta a TMDb, géneros, sinónimos y resumen sin spoilers
├── test_cam.py        # Chequeo de la lógica sin red (python test_cam.py)
├── .env.ejemplo       # Plantilla de claves; cópiala como .env
├── requirements.txt
├── Indicaciones.txt   # Pasos rápidos de arranque
└── README.md
```

### Cómo funciona el "sin spoilers"

La sinopsis de TMDb suele ir de lo general a lo concreto, así que `resumen_sin_spoilers()`
se queda con las **dos primeras frases**: el planteamiento de la historia. Lo que viene
después (giros, final) se recorta y se marca con `[…]`.

---

## 🔮 Posibles mejoras

- [ ] Filtro por año o por década
- [ ] Filtro por plataforma (Netflix, Prime, Disney+) con el endpoint `watch/providers`
- [ ] Guardar los gustos del usuario en una base de datos, no solo en la sesión
- [ ] Póster de la película como imagen
- [ ] Recomendación por película parecida (`/movie/{id}/similar`)
- [ ] Resumen sin spoilers generado por un LLM en vez de por recorte de frases

---

## ⚠️ Seguridad

- **Nunca** subas el token de Telegram ni la API key al repositorio: usa variables de entorno
- Si un token se expone, revócalo de inmediato con [@BotFather](https://t.me/BotFather)

---

## 🙏 Créditos

- Datos de películas: [The Movie Database (TMDb)](https://www.themoviedb.org) — este producto
  usa la API de TMDb pero no está avalado ni certificado por TMDb
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
