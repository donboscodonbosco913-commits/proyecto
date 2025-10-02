from sqlalchemy.orm import Session
from models import Equipo, TipoDispositivo, Edificios, PcDetalle, GraficaDedicada


from models import PcDetalle, GraficaDedicada

def obtener_equipos(db: Session):
    equipos = db.query(Equipo).all()
    for e in equipos:
        tipo = db.query(TipoDispositivo).filter_by(id_tipo=e.id_tipo).first()
        edificio = db.query(Edificios).filter_by(id_edificio=e.id_edificio).first()
        e.tipo_nombre = tipo.nombre if tipo else ""
        e.edificio_nombre = edificio.nombre if edificio else ""

        if e.tipo_nombre.lower() == "cpu":
            detalle = db.query(PcDetalle).filter_by(id_equipo=e.id_equipo).first()
            if detalle:
                e.ram_gb = detalle.ram_gb
                e.tipo_ram = detalle.tipo_ram
                e.almacenamiento_gb = detalle.almacenamiento_gb
                e.tipo_almacenamiento = detalle.tipo_almacenamiento
                e.procesador = detalle.procesador
                e.otros_detalles = detalle.otros_detalles

                grafica = db.query(GraficaDedicada).filter_by(id_pc=detalle.id_pc).first()
                if grafica:
                    e.grafica_marca = grafica.marca
                    e.grafica_modelo = grafica.modelo
                    e.vram_gb = grafica.vram_gb
    return equipos


def obtener_edificios(db: Session):
    return db.query(Edificios).all()

def obtener_tipos_dispositivos(db: Session):
    return db.query(TipoDispositivo).all()


from sqlalchemy.orm import joinedload
from models import Equipo
from sqlalchemy.orm import Session
from models import Equipo, TipoDispositivo, Edificios, PcDetalle, GraficaDedicada

def obtener_equipos_usuario(db: Session):
    """
    Trae todos los equipos con sus relaciones y atributos para mostrar en la vista de usuario.
    """
    equipos = db.query(Equipo).all()

    for e in equipos:
        # Nombre de tipo y edificio
        tipo = db.query(TipoDispositivo).filter_by(id_tipo=e.id_tipo).first()
        edificio = db.query(Edificios).filter_by(id_edificio=e.id_edificio).first()
        e.tipo_nombre = tipo.nombre if tipo else ""
        e.edificio_nombre = edificio.nombre if edificio else ""

        # Detalles de CPU
        if e.tipo_nombre.lower() == "cpu":
            detalle = db.query(PcDetalle).filter_by(id_equipo=e.id_equipo).first()
            if detalle:
                e.ram_gb = detalle.ram_gb
                e.tipo_ram = detalle.tipo_ram
                e.almacenamiento_gb = detalle.almacenamiento_gb
                e.tipo_almacenamiento = detalle.tipo_almacenamiento
                e.procesador = detalle.procesador
                e.otros_detalles = detalle.otros_detalles

                grafica = db.query(GraficaDedicada).filter_by(id_pc=detalle.id_pc).first()
                if grafica:
                    e.grafica_marca = grafica.marca
                    e.grafica_modelo = grafica.modelo
                    e.vram_gb = grafica.vram_gb
    return equipos


from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Equipo, Edificios, TipoDispositivo

def obtener_equipos_con_filtros(db: Session, filtro: str = None, id_edificio: int = None, id_tipo: int = None):
    # Consulta base con joins
    query = db.query(Equipo).join(Edificios).join(TipoDispositivo).filter(Equipo.estado == "Activo")
    
    # Aplicar filtro de texto
    if filtro and filtro.strip():
        filtro_like = f"%{filtro.strip()}%"
        query = query.filter(
            or_(
                Equipo.codigo.ilike(filtro_like),
                Equipo.marca.ilike(filtro_like),
                Equipo.modelo.ilike(filtro_like),
                Equipo.serie.ilike(filtro_like),
                Edificios.nombre.ilike(filtro_like),
                TipoDispositivo.nombre.ilike(filtro_like)
            )
        )
    
    # Aplicar filtro por edificio
    if id_edificio:
        query = query.filter(Equipo.id_edificio == id_edificio)
    
    # Aplicar filtro por tipo
    if id_tipo:
        query = query.filter(Equipo.id_tipo == id_tipo)
    
    # Ordenar y obtener resultados
    return query.order_by(Equipo.codigo).all()