from fastapi import FastAPI
from src.api import users, projects, tasks

app = FastAPI(
    title="TaskFlow API",
    description="A task and project management backend.",
    version="1.0.0",
)

app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
