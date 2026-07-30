from __future__ import annotations

from fetchflow.errors import RATE_LIMIT_MESSAGE, describe_failure, looks_rate_limited


def test_terminal_color_codes_never_reach_the_message():
    """Se vio "[0;31mERROR: [0m[youtube] ..." crudo en una UI real.

    Es lo primero que ve alguien cuando algo falla.
    """
    raw = "\x1b[0;31mERROR: \x1b[0m[youtube] abc: This content isn't available"

    out = describe_failure(RuntimeError(raw))

    assert "\x1b" not in out
    assert out == "[youtube] abc: This content isn't available"


def test_the_yt_dlp_prefix_is_dropped():
    # "ERROR: " es ruido: la app ya sabe que es un error, lo muestra en rojo.
    assert describe_failure(RuntimeError("ERROR: algo se rompio")) == "algo se rompio"


def test_the_reason_the_site_gave_survives():
    # Cuando un sitio cambia, ese texto es lo unico util que se puede dar.
    out = describe_failure(RuntimeError("[vimeo] 1: Failed to fetch OAuth token: HTTP Error 401"))

    assert "401" in out
    assert "OAuth" in out


def test_a_rate_limit_becomes_something_actionable():
    """El mensaje de yt-dlp recomienda un flag de linea de comandos.

    En una app embebida ese flag no existe, asi que el consejo es inaplicable y deja a
    la persona creyendo que algo esta roto.
    """
    raw = "The current session has been rate-limited by YouTube for up to an hour. It is recommended to use `-t sleep`"

    out = describe_failure(RuntimeError(raw))

    assert out == RATE_LIMIT_MESSAGE
    assert "-t sleep" not in out


def test_each_app_can_word_the_rate_limit_in_its_own_voice():
    out = describe_failure(
        RuntimeError("HTTP Error 429: Too Many Requests"),
        rate_limit_message="Slow down, mate.",
    )

    assert out == "Slow down, mate."


def test_a_message_that_is_only_decoration_still_says_something():
    # Un mensaje vacio dejaria la UI con un error en blanco.
    assert describe_failure(RuntimeError("\x1b[0;31mERROR: \x1b[0m")) == "RuntimeError"
    assert describe_failure(ValueError("")) == "ValueError"


def test_a_normal_failure_is_not_mistaken_for_a_rate_limit():
    assert looks_rate_limited("[vimeo] 1: HTTP Error 401: Unauthorized") is False
    assert looks_rate_limited("HTTP Error 429: Too Many Requests") is True
