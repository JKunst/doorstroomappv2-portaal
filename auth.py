"""
JWT-validatie voor Doorstroomanalyse — subapp van het Bovenbouw-portaal.

De gebruiker komt binnen met ?token=<JWT> in de URL. De JWT is door het portaal
ondertekend met HS256 en bevat: eckid, naam, rol, klas, app_rollen, exp.

Eenmaal gevalideerd staat de user-info in st.session_state['user'].
Token wordt uit de URL gestript zodra 'ie verwerkt is — zo voorkomen we
dat een refresh een verlopen token opnieuw probeert.
"""
import os
import jwt
import streamlit as st

PORTAAL_JWT_SECRET = os.environ.get("PORTAAL_JWT_SECRET")
TOEGESTANE_ROLLEN  = {"docent", "beheerder"}


def _stop_met_melding(msg: str) -> None:
    st.error(msg)
    st.markdown('[← Terug naar portaal](https://bovenbouwsucces.nl)')
    st.stop()


def check_jwt() -> dict:
    """
    Controleert de JWT en zet de user in session_state.
    Roep aan bovenaan elke pagina, vóór elke st.* call die data toont.
    """
    if "user" in st.session_state:
        return st.session_state["user"]

    if not PORTAAL_JWT_SECRET:
        _stop_met_melding("Configuratiefout: PORTAAL_JWT_SECRET niet gezet.")

    token = st.query_params.get("token")
    if not token:
        _stop_met_melding("Geen token — log in via het portaal.")

    try:
        claims = jwt.decode(token, PORTAAL_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        _stop_met_melding("Sessie verlopen. Ga terug naar het portaal en open de tegel opnieuw.")
    except jwt.InvalidTokenError:
        _stop_met_melding("Ongeldig token.")

    if claims.get("rol") not in TOEGESTANE_ROLLEN:
        _stop_met_melding("Geen toegang — deze app is alleen voor docenten.")

    st.session_state["user"] = claims

    # Token uit URL halen — anders blijft 'ie in browser-history en refresht 'ie naar een verlopen token
    st.query_params.clear()
    return claims
