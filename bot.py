"""CAMovies - bot de Telegram que recomienda peliculas segun tus gustos.

Se presenta como Cam, y habla de si misma en femenino.
"""
import os
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import Conflict, InvalidToken, NetworkError, TelegramError, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tmdb import (
    GENEROS,
    buscar_peliculas,
    buscar_por_titulo,
    escapar,
    formatear_pelicula,
    generos_de,
    generos_desde_texto,
    limpiar_titulo,
    peliculas_similares,
    url_poster,
    SORPRESAS,
    buscar_sorpresa,
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
POR_TANDA = 3

PRESENTACION = (
    "🍿 ¡Hola! Soy *Cam*, tu recomendadora de cine.\n\n"
    "Cuentame que te gusta y te paso peliculas con su *calificacion*, sus generos "
    "y un resumen *sin spoilers*.\n\n"
    "Estoy lista para cosas como:\n"
    "• _quiero algo de terror y misterio_\n"
    "• _me gusto la pelicula Submarine, me recomiendas alguna parecida?_\n"
    "• _una comedia romantica para hoy_\n\n"
    "Y si no sabes que ver, dale a *Sorprendeme* o elige un genero 👇"
)


def _fila_sorpresa() -> list[list[InlineKeyboardButton]]:
    """Botones para cuando no sabe que escoger."""
    return [
        [InlineKeyboardButton("🎲 Sorprendeme", callback_data="sorpresa:azar")],
        [InlineKeyboardButton(SORPRESAS["top"]["etiqueta"], callback_data="sorpresa:top"),
         InlineKeyboardButton(SORPRESAS["joya"]["etiqueta"], callback_data="sorpresa:joya")],
    ]


def teclado_generos() -> InlineKeyboardMarkup:
    botones = [InlineKeyboardButton(etiqueta, callback_data=f"g:{clave}")
               for clave, (_, etiqueta) in GENEROS.items()]
    filas = _fila_sorpresa() + [botones[i:i + 2] for i in range(0, len(botones), 2)]
    return InlineKeyboardMarkup(filas)


def teclado_otra_sorpresa(modo: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Otra tanda", callback_data=f"sorpresa:{modo}")],
        [InlineKeyboardButton(
            SORPRESAS["joya" if modo == "top" else "top"]["etiqueta"],
            callback_data=f"sorpresa:{'joya' if modo == 'top' else 'top'}")],
        [InlineKeyboardButton("🎭 Elegir un genero", callback_data="menu")],
    ])


def teclado_mas(claves: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Mas de esto", callback_data="mas:" + ",".join(claves))],
        [InlineKeyboardButton("🎲 Otro genero", callback_data="menu")],
    ])


def teclado_similares(id_pelicula: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Mas parecidas a esa", callback_data=f"sim:{id_pelicula}")],
        [InlineKeyboardButton("🎲 Elegir un genero", callback_data="menu")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        PRESENTACION, parse_mode="Markdown", reply_markup=teclado_generos()
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Soy *Cam* 🎬, tu recomendadora de cine.\n\n"
        "/start - me presento y te muestro los generos\n"
        "/sorpresa - no sabes que ver? yo elijo\n"
        "   • `/sorpresa mejores` - las mejor calificadas de la historia\n"
        "   • `/sorpresa joyas` - joyas ocultas que casi nadie ha visto\n"
        "/recomendar - igual que /sorpresa, o con genero: `/recomendar terror`\n"
        "/ayuda - este mensaje\n\n"
        "Tambien puedes decirme un genero, o nombrarme una pelicula que te gusto "
        "y te busco parecidas.",
        parse_mode="Markdown",
    )


# ─── Envio de recomendaciones ───────────────────────────

def _elegir(candidatas: list[dict], context: ContextTypes.DEFAULT_TYPE) -> list[dict]:
    """Quita lo ya mostrado a este usuario y devuelve una tanda al azar."""
    vistas = context.user_data.setdefault("vistas", set())
    nuevas = [p for p in candidatas if p.get("id") not in vistas]
    if not nuevas:
        nuevas = list(candidatas)  # ya le mostre todo: mejor repetir que no responder
        vistas.clear()
    random.shuffle(nuevas)
    tanda = nuevas[:POR_TANDA]
    vistas.update(p["id"] for p in tanda)
    return tanda


async def _aviso_error(mensaje, e: Exception):
    if isinstance(e, RuntimeError):
        await mensaje.reply_text(
            "⚠️ Me falta la llave de TMDb. Configura `TMDB_API_KEY` y vuelve a iniciarme.",
            parse_mode="Markdown",
        )
    else:
        print(f"Error consultando TMDb: {type(e).__name__}: {e}")
        await mensaje.reply_text("⚠️ No pude consultar el catalogo ahora. Intenta en un momento.")


CAPTION_MAX = 1024  # limite de Telegram para el texto que acompana una foto


async def enviar_tanda(mensaje, tanda: list[dict], encabezado: str, teclado):
    """Manda el encabezado y luego una foto por pelicula, con su ficha como pie.

    La ficha (calificacion, generos y resumen sin spoilers) va en el caption de la
    portada, asi que la imagen se suma al texto en vez de reemplazarlo. Si TMDb no
    tiene portada, o Telegram no logra descargarla, esa pelicula sale como texto.
    """
    await mensaje.reply_text(encabezado, parse_mode="Markdown")
    for i, peli in enumerate(tanda):
        ficha = formatear_pelicula(peli)[:CAPTION_MAX]
        # el teclado se cuelga de la ultima, para no repetir botones en cada foto
        botones = teclado if i == len(tanda) - 1 else None
        poster = url_poster(peli)
        if poster:
            try:
                await mensaje.reply_photo(
                    photo=poster, caption=ficha, parse_mode="Markdown", reply_markup=botones
                )
                continue
            except TelegramError as e:
                print(f"No pude enviar la portada de {peli.get('title')}: {e}")
        await mensaje.reply_text(ficha, parse_mode="Markdown", reply_markup=botones)


async def enviar_por_genero(mensaje, context: ContextTypes.DEFAULT_TYPE, claves: list[str]):
    await mensaje.chat.send_action(ChatAction.TYPING)
    try:
        resultados = await buscar_peliculas(claves)
    except Exception as e:
        await _aviso_error(mensaje, e)
        return
    tanda = _elegir(resultados, context)
    if not tanda:
        await mensaje.reply_text("😕 No encontre nada con esa combinacion. Prueba con otro genero.")
        return
    titulos = [GENEROS[k][1] for k in claves if k in GENEROS]
    encabezado = f"🎯 Para tu gusto ({', '.join(titulos)}):" if titulos else "🎲 Te traigo estas:"
    await enviar_tanda(mensaje, tanda, encabezado, teclado_mas(claves))


ENCABEZADOS_SORPRESA = {
    "top": "🏆 De lo mejor que se ha filmado, segun quienes las votaron:",
    "joya": "💎 Joyas ocultas: nota altisima y casi nadie las ha visto 👀",
}


async def enviar_sorpresa(mensaje, context: ContextTypes.DEFAULT_TYPE, modo: str):
    """Modo para cuando no sabe que escoger. 'azar' decide entre las dos recetas."""
    if modo not in SORPRESAS:
        modo = random.choice(list(SORPRESAS))
    await mensaje.chat.send_action(ChatAction.TYPING)
    try:
        resultados = await buscar_sorpresa(modo)
    except Exception as e:
        await _aviso_error(mensaje, e)
        return
    tanda = _elegir(resultados, context)
    if not tanda:
        await mensaje.reply_text("😕 No me llego nada del catalogo. Intenta de nuevo.")
        return
    await enviar_tanda(mensaje, tanda, ENCABEZADOS_SORPRESA[modo], teclado_otra_sorpresa(modo))


async def enviar_similares(mensaje, context: ContextTypes.DEFAULT_TYPE, base: dict) -> bool:
    """Recomienda a partir de una pelicula concreta. False si TMDb no dio nada."""
    try:
        similares = await peliculas_similares(base["id"])
    except Exception as e:
        await _aviso_error(mensaje, e)
        return True
    titulo = escapar(base.get("title") or base.get("original_title") or "esa")
    if not similares:
        # sin recomendaciones propias: tiro por los generos de esa pelicula
        claves = generos_de(base)
        if not claves:
            return False
        await mensaje.reply_text(
            f"No tengo parecidas exactas a *{titulo}*, asi que te busco por sus generos 👇",
            parse_mode="Markdown",
        )
        await enviar_por_genero(mensaje, context, claves)
        return True
    tanda = _elegir(similares, context)
    await enviar_tanda(
        mensaje,
        tanda,
        f"Si te gusto *{titulo}*, creo que estas te van a encantar:",
        teclado_similares(base["id"]),
    )
    return True


# ─── Handlers ───────────────────────────────────────────

async def recomendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    claves = generos_desde_texto((update.message.text or "").replace("/recomendar", ""))
    if claves:
        await enviar_por_genero(update.message, context, claves)
    else:
        await enviar_sorpresa(update.message, context, "azar")


async def sorpresa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sorpresa [joyas|mejores] - para cuando no sabe que escoger."""
    texto = (update.message.text or "").lower()
    if "joya" in texto or "oculta" in texto:
        modo = "joya"
    elif "mejor" in texto or "top" in texto or "clasic" in texto:
        modo = "top"
    else:
        modo = "azar"
    await enviar_sorpresa(update.message, context, modo)


async def texto_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    claves = generos_desde_texto(texto)
    if claves:
        await enviar_por_genero(update.message, context, claves)
        return

    # no menciono generos: a lo mejor me esta nombrando una pelicula
    titulo = limpiar_titulo(texto)
    if titulo:
        await update.message.chat.send_action(ChatAction.TYPING)
        try:
            base = await buscar_por_titulo(titulo)
        except Exception as e:
            await _aviso_error(update.message, e)
            return
        if base and await enviar_similares(update.message, context, base):
            return

    await update.message.reply_text(
        "🤔 No encontre esa pelicula ni pille el genero que quieres. Dime un genero "
        "(_terror_, _comedia romantica_, _ciencia ficcion_), nombrame una pelicula que "
        "te gusto, o si no sabes que ver dale a *Sorprendeme*:",
        parse_mode="Markdown",
        reply_markup=teclado_generos(),
    )


async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefijo, _, valor = query.data.partition(":")

    if prefijo == "menu":
        await query.message.reply_text("¿Que se te antoja hoy?", reply_markup=teclado_generos())
        return
    if prefijo == "sorpresa":
        await enviar_sorpresa(query.message, context, valor)
        return
    if prefijo == "sim":
        try:
            similares = await peliculas_similares(int(valor))
        except Exception as e:
            await _aviso_error(query.message, e)
            return
        tanda = _elegir(similares, context)
        if not tanda:
            await query.message.reply_text("😕 Ya te mostre todas las parecidas que tengo.")
            return
        await enviar_tanda(
            query.message, tanda, "🔁 Mas en esa linea:", teclado_similares(int(valor))
        )
        return

    claves = [c for c in valor.split(",") if c in GENEROS]
    await enviar_por_genero(query.message, context, claves)


def main():
    if not TOKEN:
        print("ERROR: variable TELEGRAM_TOKEN no configurada (ponla en el archivo .env)")
        raise SystemExit(1)
    if not os.getenv("TMDB_API_KEY"):
        print("AVISO: falta TMDB_API_KEY, el bot arranca pero no podra recomendar.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["ayuda", "help"], ayuda))
    app.add_handler(CommandHandler("recomendar", recomendar))
    app.add_handler(CommandHandler(["sorpresa", "random"], sorpresa))
    app.add_handler(CallbackQueryHandler(boton))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_libre))

    print("CAMovies (Cam) corriendo... esperando mensajes")
    try:
        app.run_polling()
    except InvalidToken:
        print("ERROR: Telegram rechazo el token. Revisa TELEGRAM_TOKEN en el archivo .env.")
        raise SystemExit(1)
    except Conflict:
        print("ERROR: ya hay otra copia de este bot corriendo (misma cuenta de BotFather).")
        print("       Cierra la otra ventana/terminal y vuelve a intentar.")
        raise SystemExit(1)
    except (TimedOut, NetworkError) as e:
        print(f"ERROR: no hay conexion con api.telegram.org ({type(e).__name__}).")
        print("       El token puede estar bien: revisa internet, firewall/antivirus o la red.")
        print("       Corre  python diagnostico.py  para ver que falla exactamente.")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Cam se despide.")


if __name__ == "__main__":
    main()
