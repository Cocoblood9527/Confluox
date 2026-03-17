from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/example")

    @router.get("")
    def read_example() -> dict[str, str]:
        return {"plugin": "example_api"}

    context.app.include_router(router)
