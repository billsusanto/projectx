from typing import List
from fastapi import FastAPI, HTTPException, status, Depends
from datetime import datetime, timezone
import logfire
from dotenv import load_dotenv
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db, get_session
from app.models import Todo, TodoCreate, TodoRead, TodoUpdate

load_dotenv()

logfire.configure()

app = FastAPI()

logfire.instrument_fastapi(app)

@app.on_event("startup")
async def on_startup():
    await init_db()
    logfire.info("Database initialized")

@app.get("/health")
def read_root():
    return {"Status": "Ok"}

@app.post("/todos/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo: TodoCreate,
    session: AsyncSession = Depends(get_session)
):
    db_todo = Todo.model_validate(todo)

    session.add(db_todo)
    await session.commit()
    await session.refresh(db_todo)

    logfire.info(f"Created todo ({db_todo.description}) with ID: {db_todo.id}")

    return db_todo

@app.get("/todos/", response_model=List[TodoRead])
async def get_todos(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Todo))
    todos = result.scalars().all()

    logfire.info(f"Retrieved {len(todos)} todos")
    return todos

@app.get("/todos/{id}", response_model=TodoRead)
async def get_todo(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    todo = await session.get(Todo, id)

    if not todo:
        logfire.warn(f"Todo with ID {id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {id} not found"
        )

    logfire.info(f"Retrieved todo with ID: {id}")
    return todo

@app.put("/todos/{id}", response_model=TodoRead)
async def update_todo(
    id: int,
    updated_todo: TodoUpdate,
    session: AsyncSession = Depends(get_session)
):
    todo = await session.get(Todo, id)

    if not todo:
        logfire.warn(f"Todo with ID {id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {id} not found"
        )

    todo_data = updated_todo.model_dump(exclude_unset=True)
    for key, value in todo_data.items():
        setattr(todo, key, value)

    todo.updated_at = datetime.now(timezone.utc)

    session.add(todo)
    await session.commit()
    await session.refresh(todo)

    logfire.info(f"Updated todo with ID: {id}")

    return todo

@app.delete("/todos/{id}")
async def delete_todo(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    todo = await session.get(Todo, id)

    if not todo:
        logfire.warn(f"Todo with ID {id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {id} not found"
        )

    await session.delete(todo)
    await session.commit()

    logfire.info(f"Deleted todo with ID: {id}")

    return {"message": f"Todo with ID {id} deleted successfully"}
