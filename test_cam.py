"""Chequeo rapido de la logica de Cam, sin red ni Telegram:  python test_cam.py"""
import os

os.environ.setdefault("TMDB_API_KEY", "dummy")

from tmdb import (
    GENEROS,
    es_decente,
    formatear_pelicula,
    generos_de,
    generos_desde_texto,
    limpiar_titulo,
    resumen_sin_spoilers,
    url_poster,
)


def demo():
    # deteccion de gustos en texto libre
    assert generos_desde_texto("quiero algo de terror y misterio") == ["terror", "misterio"]
    assert generos_desde_texto("una COMEDIA romántica para hoy") == ["comedia", "romance"]
    assert generos_desde_texto("ciencia ficción en el espacio")[0] == "cienciaficcion"
    assert generos_desde_texto("algo que me haga llorar") == ["drama"]
    assert generos_desde_texto("hola buenas tardes") == []
    assert generos_desde_texto("terror terror terror") == ["terror"]  # sin repetidos

    # el caso que fallaba: nombrar una pelicula y pedir parecidas
    assert limpiar_titulo(
        "me gustó la pelicula submarine me recomiendas alguna parecida?") == "submarine"
    assert limpiar_titulo("me gusto Interstellar") == "Interstellar"
    assert limpiar_titulo("algo parecido a El Padrino por favor") == "El Padrino"
    assert limpiar_titulo("vi La La Land, recomiendame alguna") == "La La Land"
    # titulos que empiezan o siguen con palabras de relleno: no se mutilan
    assert limpiar_titulo("Como agua para chocolate") == "Como agua para chocolate"
    assert limpiar_titulo("Algo pasa con Mary") == "Algo pasa con Mary"
    assert limpiar_titulo("me encanto Amor sin barreras") == "Amor sin barreras"
    # puro relleno, sin titulo -> no hay nada que buscar
    assert limpiar_titulo("me recomiendas alguna parecida") == ""
    assert limpiar_titulo("hola") == "hola"

    # resumen sin spoilers: solo el planteamiento
    largo = "Un ladron entra a los suenos. Reune un equipo. Al final muere y era un sueno."
    corto = resumen_sin_spoilers(largo)
    assert "muere" not in corto, corto
    assert corto.startswith("Un ladron entra"), corto
    assert corto.endswith("[…]"), corto
    assert resumen_sin_spoilers("") and resumen_sin_spoilers(None)

    # ficha formateada: calificacion, generos y resumen
    peli = {
        "id": 954,
        "title": "Mission: Impossible_1",
        "release_date": "1996-05-22",
        "vote_average": 7.1,
        "vote_count": 6200,
        "genre_ids": [28, 53],
        "overview": "Un agente es acusado de traicion. Debe limpiar su nombre. Y el topo era su jefe.",
    }
    ficha = formatear_pelicula(peli)
    assert "7.1/10" in ficha and "6200 votos" in ficha
    assert "Accion" in ficha and "Suspenso" in ficha
    assert "topo" not in ficha, ficha
    assert r"Impossible\_1" in ficha, ficha  # markdown escapado

    # portada: url completa, y None cuando TMDb no tiene imagen (ahi va solo texto)
    assert url_poster({"poster_path": "/abc.jpg"}) == "https://image.tmdb.org/t/p/w500/abc.jpg"
    assert url_poster({"poster_path": None}) is None
    assert url_poster({}) is None
    # la ficha sigue completa: la foto se suma al texto, no lo reemplaza
    assert len(ficha) <= 1024, "no cabria en el caption de una foto"

    # generos de una pelicula ya descargada (para el plan B de los similares)
    assert generos_de(peli) == ["accion", "suspenso"]
    assert generos_de({"genres": [{"id": 27, "name": "Terror"}]}) == ["terror"]
    assert generos_de({}) == []

    # filtro de calidad de los similares
    assert es_decente(peli)
    assert not es_decente({"vote_average": 9.0, "vote_count": 3})      # pocos votos
    assert not es_decente({"vote_average": 4.2, "vote_count": 5000})   # mala nota
    assert not es_decente({})

    # modo sorpresa: las dos recetas deben pedir cosas distintas
    from tmdb import SORPRESAS
    top, joya = SORPRESAS["top"]["params"], SORPRESAS["joya"]["params"]
    assert top["vote_count.gte"] >= 3000, "las 'mejores' necesitan muchos votos"
    assert joya["vote_count.lte"] <= 2000 < top["vote_count.gte"], "las joyas son poco votadas"
    assert joya["vote_average.gte"] >= 7.0, "una joya tiene que estar bien calificada"
    assert top["sort_by"] == joya["sort_by"] == "vote_average.desc"

    assert len(GENEROS) == 18
    print("Todo OK")


if __name__ == "__main__":
    demo()
