from contextlib import closing
import json
from pathlib import Path
import os
import sys
import configparser
import sqlite3
from http.cookiejar import Cookie, CookieJar

import lz4.block


def _cookie(
    host: str,
    path: str,
    isSecure: bool,
    expiry: int,
    name: str,
    value: str,
    isHttpOnly: bool,
) -> Cookie:
    """Returns a Cookie object from the given parameters."""
    return Cookie(
        version=0,
        name=name,
        value=value,
        domain=host,
        path=path,
        secure=bool(isSecure),
        expires=expiry,
        rest={"HttpOnly": isHttpOnly} if isHttpOnly else {},
        # extra, todo remove?
        domain_specified=host.startswith("."),
        domain_initial_dot=host.startswith("."),
        path_specified=bool(path),
        discard=expiry is None,
        port=None,
        port_specified=False,
        comment=None,
        comment_url=None,
    )


def _cookies_from(cookie_file: Path, domain: str = "") -> CookieJar:
    """Returns a CookieJar containing cookies from the given Firefox cookies.sqlite file."""

    jar = CookieJar()

    with closing(
        sqlite3.connect(cookie_file.resolve().as_uri() + "?mode=ro", uri=True)
    ) as conn:
        for row in conn.execute(
            "SELECT host, path, isSecure, expiry, name, value, isHttpOnly "
            "FROM moz_cookies WHERE instr(lower(host), lower(?)) > 0",
            (domain,),
        ):
            jar.set_cookie(_cookie(*row))
    return jar


def _cookie_file() -> Path:
    """Returns the path to the Firefox cookies.sqlite file on Windows."""

    if not (directory := os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")):
        raise EnvironmentError(
            "Could not find APPDATA or LOCALAPPDATA environment variable."
        )

    if not (firefox := Path(directory) / "Mozilla" / "Firefox"):
        raise EnvironmentError(
            "Could not find Firefox directory in APPDATA or LOCALAPPDATA."
        )

    config = configparser.ConfigParser(interpolation=None)
    config.read(firefox / "profiles.ini", encoding="utf-8")

    # Firefox [Install*] has a default profile.
    # Firefox [Profile*] sections have profile paths.
    # Prioritize the current default, then install default, then others.
    profile_paths = [
        config[s]["Path"]
        for s in config.sections()
        if s.startswith("Profile") and config[s].get("Default") == "1"
    ]
    profile_paths += [
        config[s]["Default"]
        for s in config.sections()
        if s.startswith("Install") and config[s].get("Default")
    ]
    profile_paths += [
        config[s]["Path"]
        for s in config.sections()
        if s.startswith("Profile") and config[s].get("Default") != "1"
    ]

    for profile in profile_paths:
        # Profile paths can be relative or absolute.
        # Pathlib discards the previous path if the new one is absolute, so we can just join these.
        candidate = firefox / profile / "cookies.sqlite"
        if candidate.is_file():
            return candidate

    return None


def load_cookies_from_firefox(domain: str) -> dict:
    """Expects values like example.com or sub.example.com"""

    if sys.platform != "win32":
        raise NotImplementedError("This function is only implemented for Windows.")

    if not (cookie_file := _cookie_file()):
        raise FileNotFoundError("Could not find a Firefox cookies.sqlite file.")

    jar = _cookies_from(cookie_file, domain)

    for session in (
        cookie_file.parent / "sessionstore.js",
        cookie_file.parent / "sessionstore-backups" / "recovery.jsonlz4",
    ):
        if not session.is_file():
            continue

        data = session.read_bytes()
        if session.suffix == ".jsonlz4" and data[:8] == b"mozLz40\0":
            data = lz4.block.decompress(data[8:])
        else:
            raise FileNotFoundError(
                "Neither sessionstore nor valid recovery file found."
            )

        state: dict = json.loads(data)
        cookies: list = state.get("cookies", [])
        for window in state.get("windows", []):
            cookies.extend(window.get("cookies", []))

        for cookie in cookies:
            host = cookie.get("host", "")
            if domain.lower() in host.lower():
                jar.set_cookie(
                    _cookie(
                        host,
                        cookie.get("path", "/"),
                        cookie.get("secure", False),
                        None,  # expiry is not available in session cookies
                        cookie.get("name", ""),
                        cookie.get("value", ""),
                        cookie.get("httponly", False),
                    )
                )
    return jar
