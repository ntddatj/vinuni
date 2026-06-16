from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmailAlreadyExistsError)
    async def email_exists_handler(request: Request, exc: EmailAlreadyExistsError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
