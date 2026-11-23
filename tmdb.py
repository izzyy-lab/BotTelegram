"""Acceso a TMDb: busqueda de peliculas por genero y armado del texto sin spoilers."""
import os
import random
import re

import httpx

def cargar_env(ruta=".env"):
    """Lee pares CLAVE=valor de un .env junto al proyecto y los mete en el entorno.

    Asi la API key vive en un archivo del proyecto (ignorado por git) y no hay que
    exportar variables en cada terminal nueva. Lo que ya este en el entorno manda.
    """
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


cargar_env()
API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"
IDIOMA = "es-MX"
IMAGENES = "https://image.tmdb.org/t/p/w500"  # ancho suficiente para Telegram

# ids oficiales de generos de TMDb (son estables, no vale la pena pedirlos cada arranque)
GENEROS = {
    "accion": (28, "Accion 💥"),
    "aventura": (12, "Aventura 🧭"),
    "animacion": (16, "Animacion 🎨"),
    "comedia": (35, "Comedia 😂"),
    "crimen": (80, "Crimen 🔍"),
    "documental": (99, "Documental 🎥"),
    "drama": (18, "Drama 🎭"),
    "familia": (10751, "Familia 👨‍👩‍👧"),
    "fantasia": (14, "Fantasia 🧝"),
    "historia": (36, "Historia 🏛️"),
    "terror": (27, "Terror 👻"),
    "musica": (10402, "Musica 🎵"),
    "misterio": (9648, "Misterio 🕵️"),
    "romance": (10749, "Romance 💞"),
    "cienciaficcion": (878, "Ciencia ficcion 🚀"),
    "suspenso": (53, "Suspenso 😰"),
    "guerra": (10752, "Guerra ⚔️"),
    "western": (37, "Western 🤠"),
}

# palabras que el usuario puede escribir -> clave de genero
SINONIMOS = {
    "accion": "accion", "pelea": "accion", "peleas": "accion", "adrenalina": "accion",
    "aventura": "aventura", "aventuras": "aventura", "viaje": "aventura",
    "animacion": "animacion", "animada": "animacion", "animadas": "animacion",
    "anime": "animacion", "dibujos": "animacion",
    "comedia": "comedia", "comica": "comedia", "risa": "comedia", "reir": "comedia",
    "gracioso": "comedia", "graciosa": "comedia", "divertida": "comedia", "humor": "comedia",
    "crimen": "crimen", "policial": "crimen", "mafia": "crimen", "narcos": "crimen",
    "documental": "documental", "documentales": "documental", "real": "documental",
    "drama": "drama", "dramatica": "drama", "llorar": "drama", "triste": "drama",
    "emotiva": "drama", "profunda": "drama",
    "familia": "familia", "familiar": "familia", "ninos": "familia", "infantil": "familia",
    "fantasia": "fantasia", "magia": "fantasia", "magica": "fantasia", "dragones": "fantasia",
    "historia": "historia", "historica": "historia", "epoca": "historia",
    "terror": "terror", "miedo": "terror", "horror": "terror", "fantasmas": "terror",
    "zombies": "terror", "susto": "terror", "sustos": "terror",
    "musica": "musica", "musical": "musica", "musicales": "musica", "cantar": "musica",
    "misterio": "misterio", "misteriosa": "misterio", "detective": "misterio",
    "enigma": "misterio", "investigacion": "misterio",
    "romance": "romance", "romantica": "romance", "romanticas": "romance", "amor": "romance",
    "pareja": "romance", "cursi": "romance",
    "cienciaficcion": "cienciaficcion", "ciencia": "cienciaficcion", "scifi": "cienciaficcion",
    "espacio": "cienciaficcion", "futuro": "cienciaficcion", "robots": "cienciaficcion",
    "aliens": "cienciaficcion", "extraterrestres": "cienciaficcion", "distopia": "cienciaficcion",
    "suspenso": "suspenso", "thriller": "suspenso", "tension": "suspenso",
    "intriga": "suspenso", "psicologico": "suspenso", "psicologica": "suspenso",
    "guerra": "guerra", "belica": "guerra", "soldados": "guerra", "militar": "guerra",
    "western": "western", "vaqueros": "western", "oeste": "western",
}

ACENTOS = str.maketrans("áéíóúüñ", "aeiouun")


def normalizar(texto: str) -> str:
    return texto.lower().translate(ACENTOS)


def generos_desde_texto(texto: str) -> list[str]:
    """Saca las claves de genero que menciona el usuario, en orden de aparicion y sin repetir."""
    palabras = re.findall(r"[a-z]+", normalizar(texto).replace(" ", " "))
    # "ciencia ficcion" y "ciencia-ficcion" llegan como dos palabras: tambien pruebo pegadas
    palabras += [a + b for a, b in zip(palabras, palabras[1:])]
    encontrados = []
    for palabra in palabras:
        clave = SINONIMOS.get(palabra)
        if clave and clave not in encontrados:
            encontrados.append(clave)
    return encontrados


def resumen_sin_spoilers(sinopsis: str, max_frases: int = 2) -> str:
    """Primeras frases de la sinopsis: el planteamiento, antes de que cuente el desenlace.

    ponytail: heuristica por frases; si algun dia se nota que filtra finales,
    el upgrade es pedirle el resumen a un LLM con instruccion de no spoilear.
    """
    sinopsis = (sinopsis or "").strip()
    if not sinopsis:
        return "Sin sinopsis disponible en espanol, pero vale la pena darle una oportunidad."
    frases = re.split(r"(?<=[.!?])\s+", sinopsis)
    corto = " ".join(frases[:max_frases]).strip()
    if len(frases) > max_frases:
        corto += " […]"
    return corto


def escapar(texto: str) -> str:
    """Neutraliza los caracteres que romperian el Markdown de Telegram."""
    for c in "_*`[":
        texto = texto.replace(c, "\\" + c)
    return texto


def url_poster(peli: dict) -> str | None:
    """Portada de la pelicula, o None si TMDb no tiene imagen de esa."""
    ruta = peli.get("poster_path")
    return f"{IMAGENES}{ruta}" if ruta else None


def formatear_pelicula(peli: dict) -> str:
    titulo = escapar(peli.get("title") or peli.get("original_title") or "Sin titulo")
    anio = (peli.get("release_date") or "----")[:4]
    nota = peli.get("vote_average") or 0
    votos = peli.get("vote_count") or 0
    estrellas = "⭐" * max(1, round(nota / 2))
    nombres = [GENEROS[k][1].rsplit(" ", 1)[0] for k, (gid, _) in GENEROS.items()
               if gid in (peli.get("genre_ids") or [])]
    return (
        f"🎬 *{titulo}* ({anio})\n"
        f"{estrellas} *{nota:.1f}/10* · {votos} votos\n"
        f"🏷️ {', '.join(nombres) or 'Sin genero'}\n"
        f"📖 _Sin spoilers:_ {resumen_sin_spoilers(peli.get('overview'))}"
    )


async def buscar_peliculas(claves_genero: list[str], pagina: int | None = None) -> list[dict]:
    """Pide a TMDb peliculas bien calificadas de esos generos. Lanza RuntimeError si no hay API key."""
    clave = API_KEY or os.getenv("TMDB_API_KEY")
    if not clave:
        raise RuntimeError("Falta la variable de entorno TMDB_API_KEY")
    ids = [str(GENEROS[k][0]) for k in claves_genero if k in GENEROS]
    params = {
        "api_key": clave,
        "language": IDIOMA,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "vote_average.gte": 6.5,
        "vote_count.gte": 300,
        "page": pagina or random.randint(1, 5),
    }
    if ids:
        params["with_genres"] = ",".join(ids)
    async with httpx.AsyncClient(timeout=15) as cliente:
        r = await cliente.get(f"{BASE}/discover/movie", params=params)
        r.raise_for_status()
        return r.json().get("results", [])


# ─── Recomendar a partir de una pelicula que ya le gusto ──────────────

# Relleno que la gente pone alrededor del titulo. Se recorta solo por los
# extremos, para no mutilar titulos que lleven esas palabras dentro
# ("Como agua para chocolate", "Amor sin barreras").
# Ojo: nada de prefijos de UNA palabra que puedan abrir un titulo real
# ("Como agua para chocolate", "Algo pasa con Mary"): solo frases inequivocas.
PREFIJOS = [
    "me gusto", "me gustaron", "me encanto", "me fascino", "me enamoro",
    "la pelicula", "el pelicula", "pelicula", "peli", "film", "vi",
    "quiero algo como", "quiero algo parecido a", "quiero algo parecido",
    "algo parecido a", "algo parecido", "algo como", "algo similar a", "algo similar",
    "parecida a", "parecido a", "parecidas a", "similar a", "del estilo de", "estilo de",
    "recomiendame algo como", "recomiendame", "me recomiendas", "recomiendas",
    "alguna como", "otra como", "alguna", "algun", "ver",
    "que sea como", "en la linea de", "al estilo",
]
SUFIJOS = [
    "me recomiendas alguna parecida", "me recomiendas algo parecido",
    "me recomiendas alguna", "me recomiendas algo", "me recomiendas",
    "recomiendame alguna", "recomiendame algo", "recomiendame",
    "alguna parecida", "algo parecido", "alguna similar", "algo similar",
    "parecida", "parecidas", "parecido", "parecidos", "similar", "similares",
    "por favor", "porfa", "gracias", "please", "y", "o", "pero",
]


def limpiar_titulo(texto: str) -> str:
    """Deja solo el posible titulo: quita signos y el relleno de los extremos.

    'me gusto la pelicula Submarine, me recomiendas alguna parecida?' -> 'Submarine'
    """
    texto = re.sub(r"[¿?¡!.,;:\"]", " ", texto)
    texto = " ".join(texto.split())
    cambio = True
    while cambio and texto:
        cambio = False
        plano = normalizar(texto)
        for p in PREFIJOS:
            if plano == p:
                return ""
            if plano.startswith(p + " "):
                texto = texto[len(p) + 1:].strip()
                cambio = True
                break
        if cambio:
            continue
        plano = normalizar(texto)
        for s in SUFIJOS:
            if plano == s:
                return ""
            if plano.endswith(" " + s):
                texto = texto[: len(texto) - len(s) - 1].strip()
                cambio = True
                break
    return texto.strip(" -_")


def generos_de(peli: dict) -> list[str]:
    """Claves de genero de una pelicula ya descargada."""
    ids = peli.get("genre_ids") or [g["id"] for g in peli.get("genres", [])]
    return [clave for clave, (gid, _) in GENEROS.items() if gid in ids]


def es_decente(peli: dict) -> bool:
    """Filtro suave para los similares: TMDb los devuelve sin filtrar por calidad."""
    return (peli.get("vote_average") or 0) >= 6.0 and (peli.get("vote_count") or 0) >= 100


async def _pedir(ruta: str, **extra) -> dict:
    clave = API_KEY or os.getenv("TMDB_API_KEY")
    if not clave:
        raise RuntimeError("Falta la variable de entorno TMDB_API_KEY")
    params = {"api_key": clave, "language": IDIOMA, **extra}
    async with httpx.AsyncClient(timeout=15) as cliente:
        r = await cliente.get(f"{BASE}{ruta}", params=params)
        r.raise_for_status()
        return r.json()


async def buscar_por_titulo(titulo: str) -> dict | None:
    """Encuentra la pelicula que el usuario menciono. None si no hay nada parecido."""
    if not titulo.strip():
        return None
    datos = await _pedir("/search/movie", query=titulo, include_adult="false", page=1)
    resultados = datos.get("results") or []
    if not resultados:
        # puede estar escrita en ingles y no existir en el catalogo es-MX
        datos = await _pedir("/search/movie", query=titulo, include_adult="false",
                             page=1, language="en-US")
        resultados = datos.get("results") or []
    # el mas popular entre los primeros, para no quedarse con un remake desconocido
    return max(resultados[:5], key=lambda p: p.get("popularity") or 0) if resultados else None


async def peliculas_similares(id_pelicula: int) -> list[dict]:
    """Recomendaciones de TMDb para esa pelicula; si no hay, cae a 'similar'."""
    datos = await _pedir(f"/movie/{id_pelicula}/recommendations", page=1)
    resultados = [p for p in datos.get("results", []) if es_decente(p)]
    if not resultados:
        datos = await _pedir(f"/movie/{id_pelicula}/similar", page=1)
        resultados = [p for p in datos.get("results", []) if es_decente(p)]
    return resultados


# ─── Para cuando no sabe que escoger ─────────────────────

# "top": lo mejor valorado de siempre, con muchisimos votos para que no entre
#        un titulo oscuro con nota 10 y cuatro votos.
# "joya": nota alta pero poca gente la ha votado: lo que casi nadie ha visto.
SORPRESAS = {
    "top": {
        "etiqueta": "🏆 Las mejor calificadas",
        "params": {
            "sort_by": "vote_average.desc",
            "vote_average.gte": 7.5,
            "vote_count.gte": 3000,
        },
        "paginas": 5,
    },
    "joya": {
        "etiqueta": "💎 Joyas ocultas",
        "params": {
            "sort_by": "vote_average.desc",
            "vote_average.gte": 7.0,
            "vote_count.gte": 200,
            "vote_count.lte": 2000,
        },
        "paginas": 8,
    },
}


async def buscar_sorpresa(modo: str, pagina: int | None = None) -> list[dict]:
    """Peliculas para el modo sorpresa: 'top' (las mejores) o 'joya' (poco vistas)."""
    receta = SORPRESAS.get(modo) or SORPRESAS["top"]
    datos = await _pedir(
        "/discover/movie",
        include_adult="false",
        page=pagina or random.randint(1, receta["paginas"]),
        **receta["params"],
    )
    return datos.get("results", [])
