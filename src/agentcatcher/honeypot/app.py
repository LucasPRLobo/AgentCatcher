from fastapi import FastAPI


def create_app() -> FastAPI:
    # FastAPI's default /docs, /redoc and /openapi.json would reveal the stack and hand
    # agents a map of every route, so the decoy disables them.
    return FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


app = create_app()
