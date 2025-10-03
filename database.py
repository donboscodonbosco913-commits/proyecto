# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (opcional)
load_dotenv()

# =====================================
# URL de conexión a PostgreSQL en Render
# =====================================
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://inventario_colegio_user:GSJt4xitqcW2FRIz92Yl1ePvXDVeX0b4@dpg-d3fgbv15pdvs73dm20vg-a.oregon-postgres.render.com/inventario_colegio"
)

# Crear engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={}  # No es necesario en PostgreSQL
)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa
Base = declarative_base()

# =====================================
# Dependencia para rutas de FastAPI
# =====================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
