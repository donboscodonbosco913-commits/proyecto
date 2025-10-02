from sqlalchemy.orm import Session
from models import Edificios

def obtener_edificios(db: Session):
    return db.query(Edificios).all()

def crear_edificio(db: Session, nombre: str):
    nuevo = Edificios(nombre=nombre)
    db.add(nuevo)
    db.commit()

def eliminar_edificio(db: Session, id_edificio: int):
    edificio = db.query(Edificios).filter(Edificios.id_edificio == id_edificio).first()
    if edificio:
        db.delete(edificio)
        db.commit()
