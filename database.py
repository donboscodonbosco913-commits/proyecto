from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Datos de conexión a PostgreSQL en Render
DB_USER = "inventario_colegio_user"
DB_PASSWORD = "GSJt4xitqcW2FRIz92Yl1ePvXDVeX0b4"
DB_HOST = "dpg-d3fgbv15pdvs73dm20vg-a"
DB_PORT = 5432
DB_NAME = "inventario_colegio"

# URL de conexión PostgreSQL
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Configuración SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
