from sqlalchemy.orm import Session
from models import Usuario

def autenticar_usuario(db: Session, usuario: str, clave: str):
    return db.query(Usuario).filter_by(usuario=usuario, clave=clave).first()

def obtener_usuarios(db):
    return db.query(Usuario).all()