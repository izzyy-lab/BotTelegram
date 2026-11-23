"""Revisa que todo este en su sitio antes de arrancar Cam:  python diagnostico.py

No imprime tus claves, solo si existen y si el servidor las acepta.
"""
import asyncio
import os
import sys

import tmdb  # al importarse lee el .env


def estado(ok: bool) -> str:
    return "[OK]   " if ok else "[FALLA]"


async def main():
    problemas = []

    print("1) Interprete de Python")
    print(f"   {estado(sys.version_info >= (3, 9))} {sys.version.split()[0]} - {sys.executable}")

    print("2) Librerias")
    try:
        import telegram
        import httpx
        version = tuple(int(n) for n in telegram.__version__.split(".")[:2])
        ok = version >= (22, 0)
        print(f"   {estado(ok)} python-telegram-bot {telegram.__version__}, httpx {httpx.__version__}")
        if not ok:
            problemas.append('Actualiza la libreria: pip install -U "python-telegram-bot>=22.0"')
    except ImportError as e:
        print(f"   {estado(False)} falta una libreria: {e}")
        problemas.append(r"Activa el entorno virtual (..\.venv\Scripts\Activate.ps1) y corre: pip install -r requirements.txt")
        print_resumen(problemas)
        return

    print("3) Archivo .env")
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    existe = os.path.exists(ruta)
    print(f"   {estado(existe)} {'encontrado' if existe else 'NO existe (copia .env.ejemplo como .env)'}")

    print("4) Claves cargadas")
    token = os.getenv("TELEGRAM_TOKEN")
    key = os.getenv("TMDB_API_KEY")
    print(f"   {estado(bool(token))} TELEGRAM_TOKEN {'presente (' + str(len(token)) + ' caracteres)' if token else 'ausente'}")
    print(f"   {estado(bool(key))} TMDB_API_KEY   {'presente (' + str(len(key)) + ' caracteres)' if key else 'ausente'}")
    if not token:
        problemas.append("Pon TELEGRAM_TOKEN en el archivo .env")
    if not key:
        problemas.append("Pon TMDB_API_KEY en el archivo .env")

    if token:
        print("5) Telegram responde?")
        try:
            bot = telegram.Bot(token)
            async with bot:
                yo = await bot.get_me()
            print(f"   {estado(True)} conectado como @{yo.username} ({yo.first_name})")
        except telegram.error.InvalidToken as e:
            print(f"   {estado(False)} token rechazado: {e}")
            problemas.append("El token no sirve: pide uno nuevo a @BotFather (/mybots) y actualiza .env")
        except (telegram.error.TimedOut, telegram.error.NetworkError) as e:
            print(f"   {estado(False)} sin conexion con api.telegram.org ({type(e).__name__})")
            problemas.append(
                "No hay conexion con api.telegram.org (el token puede estar bien). "
                "Revisa internet, firewall/antivirus o red del colegio; a veces hay que usar otra red o VPN"
            )
        except Exception as e:
            print(f"   {estado(False)} {type(e).__name__}: {e}")
            problemas.append(f"Fallo inesperado hablando con Telegram: {type(e).__name__}")

    if key:
        print("6) TMDb responde?")
        try:
            pelis = await tmdb.buscar_peliculas(["terror"], pagina=1)
            print(f"   {estado(bool(pelis))} {len(pelis)} peliculas recibidas"
                  + (f", ej: {pelis[0].get('title')}" if pelis else ""))
            if not pelis:
                problemas.append("TMDb contesto vacio; revisa los filtros en tmdb.py")
        except Exception as e:
            print(f"   {estado(False)} {type(e).__name__}: {e}")
            problemas.append("TMDb rechazo la API key: usa la 'API Key (v3 auth)' de themoviedb.org -> Ajustes -> API")

    print_resumen(problemas)


def print_resumen(problemas):
    print("\n" + "=" * 50)
    if problemas:
        print("Falta por arreglar:")
        for i, p in enumerate(problemas, 1):
            print(f"  {i}. {p}")
    else:
        print("Todo listo. Arranca con: python bot.py")


if __name__ == "__main__":
    asyncio.run(main())
