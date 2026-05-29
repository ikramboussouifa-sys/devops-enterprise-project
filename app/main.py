from fastapi import Depends
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from prometheus_client import generate_latest
from sqlalchemy.orm import Session

from app.database import Base
from app.database import engine
from app.database import get_db
from app.metrics import REQUEST_COUNT
from app.metrics import REQUEST_LATENCY
from app.models import User
from app.models import UserCreate
from app.models import UserResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevOps Enterprise API")

ENDPOINT = "/users"

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/")
def root():
    return {"message": "API is running"}


@app.post(ENDPOINT, response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    REQUEST_COUNT.labels(method="POST", endpoint=ENDPOINT).inc()

    with REQUEST_LATENCY.labels(endpoint=ENDPOINT).time():
        db_user = User(
            name=user.name,
            email=user.email
        )

        db.add(db_user)

        db.commit()

        db.refresh(db_user)

        return db_user


@app.get(ENDPOINT)
def get_users(db: Session = Depends(get_db)):
    REQUEST_COUNT.labels(method="GET", endpoint=ENDPOINT).inc()

    with REQUEST_LATENCY.labels(endpoint=ENDPOINT).time():
        users = db.query(User).all()

        return users


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest())