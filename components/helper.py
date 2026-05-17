"""
Backwards-compat shim. De oude check_password() is vervangen door JWT-validatie
(zie auth.py). Alle pages importeren nog wel `from components.helper import *`,
dus we exposen `check_password` als alias zodat bestaande imports blijven werken.
"""
from auth import check_jwt as check_password  # noqa: F401
