import os
from sqlmodel import SQLModel, create_engine, Session

# Default to local Docker Postgres for host-side development
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://user:password@localhost:5433/opentrade"
)

engine = create_engine(DATABASE_URL)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
