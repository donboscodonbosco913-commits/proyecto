from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Equipo, Edificios, TipoDispositivo, PcDetalle, GraficaDedicada, Perifericos

def obtener_equipos_usuario(db: Session, filtro: str = None, id_edificio: int = None, id_tipo: int = None):
    query = db.query(Equipo).filter(Equipo.estado == "Activo")
    
    # Aplicar filtros
    if filtro:
        query = query.filter(
            or_(
                Equipo.codigo.ilike(f"%{filtro}%"),
                Equipo.marca.ilike(f"%{filtro}%"),
                Equipo.modelo.ilike(f"%{filtro}%"),
                Equipo.serie.ilike(f"%{filtro}%")
            )
        )
    
    if id_edificio:
        query = query.filter(Equipo.id_edificio == id_edificio)
    
    if id_tipo:
        query = query.filter(Equipo.id_tipo == id_tipo)
    
    equipos = query.order_by(Equipo.codigo).all()
    
    # Cargar relaciones
    for equipo in equipos:
        db.refresh(equipo)  # Asegurar que las relaciones se carguen
    
    return equipos

def obtener_equipo_completo(db: Session, id_equipo: int):
    equipo = db.query(Equipo).filter(
        Equipo.id_equipo == id_equipo, 
        Equipo.estado == "Activo"
    ).first()
    
    if not equipo:
        return None
    
    # Cargar detalles específicos según el tipo
    if hasattr(equipo, 'detalle') and equipo.detalle:
        # Cargar gráfica si existe
        if equipo.detalle.grafica:
            db.refresh(equipo.detalle.grafica)
        
        # Cargar periféricos
        perifericos = db.query(Perifericos).filter(
            Perifericos.id_equipo == id_equipo
        ).all()
        equipo.perifericos = perifericos
    
    return equipo