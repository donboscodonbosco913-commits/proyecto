from sqlalchemy import Column, Integer, String, Text, Enum, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

# ------------------ ENUMS ------------------
class RolEnum(enum.Enum):
    Administrador = "Administrador"
    Estandar = "Estandar"   # ✅ Cambiado de "Usuario" a "Estandar" para coincidir con main.py

class EstadoEnum(enum.Enum):
    Activo = "Activo"
    Inactivo = "Inactivo"
    Eliminado = "Eliminado"

# ------------------ MODELOS ------------------

class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(50), unique=True, nullable=False)
    clave = Column(String(255), nullable=False)
    rol = Column(Enum(RolEnum, name="rol_enum"), nullable=False)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())  # ✅ ahora se autocompleta en Postgres


class Edificios(Base):
    __tablename__ = "edificios"

    id_edificio = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)


class TipoDispositivo(Base):
    __tablename__ = "tipos_dispositivos"

    id_tipo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)


class Equipo(Base):
    __tablename__ = "equipos"

    id_equipo = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True)
    id_edificio = Column(Integer, ForeignKey("edificios.id_edificio"), nullable=False)
    id_tipo = Column(Integer, ForeignKey("tipos_dispositivos.id_tipo"), nullable=False)
    marca = Column(String(50))
    modelo = Column(String(50))
    serie = Column(String(100))
    estado = Column(Enum(EstadoEnum, name="estado_enum"), default=EstadoEnum.Activo, nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())  # ✅ autocompleta en Postgres

    edificio = relationship("Edificios")
    tipo = relationship("TipoDispositivo")
    detalle = relationship("PcDetalle", uselist=False, back_populates="equipo")
    perifericos = relationship("Periferico", back_populates="equipo", cascade="all, delete-orphan")
    historiales = relationship("HistorialEliminados", back_populates="equipo", cascade="all, delete-orphan")


class PcDetalle(Base):
    __tablename__ = "pc_detalles"

    id_pc = Column(Integer, primary_key=True, index=True)
    id_equipo = Column(Integer, ForeignKey("equipos.id_equipo", ondelete="CASCADE"), unique=True, nullable=False)
    ram_gb = Column(Integer)
    tipo_ram = Column(String(20))
    almacenamiento_gb = Column(Integer)
    tipo_almacenamiento = Column(String(20))
    procesador = Column(String(100))
    otros_detalles = Column(Text)

    equipo = relationship("Equipo", back_populates="detalle")
    grafica = relationship("GraficaDedicada", uselist=False, back_populates="pc")


class GraficaDedicada(Base):
    __tablename__ = "graficas_dedicadas"

    id_grafica = Column(Integer, primary_key=True, index=True)
    id_pc = Column(Integer, ForeignKey("pc_detalles.id_pc", ondelete="CASCADE"), unique=True, nullable=False)
    marca = Column(String(50))
    modelo = Column(String(100))
    vram_gb = Column(Integer)

    pc = relationship("PcDetalle", back_populates="grafica")


class HistorialEliminados(Base):
    __tablename__ = "historial_eliminados"

    id_historial = Column(Integer, primary_key=True, autoincrement=True)
    id_equipo = Column(Integer, ForeignKey("equipos.id_equipo"), nullable=False)
    codigo = Column(String(50))
    id_edificio = Column(Integer)
    id_tipo = Column(Integer)
    marca = Column(String(50))
    modelo = Column(String(50))
    serie = Column(String(50))
    estado = Column(Enum(EstadoEnum, name="estado_enum"), default=EstadoEnum.Eliminado, nullable=False)

    equipo = relationship("Equipo", back_populates="historiales")


class Periferico(Base):
    __tablename__ = "perifericos"

    id_periferico = Column(Integer, primary_key=True, autoincrement=True)
    id_equipo = Column(Integer, ForeignKey("equipos.id_equipo", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)
    marca = Column(String(50))
    modelo = Column(String(50))
    serie = Column(String(50))

    equipo = relationship("Equipo", back_populates="perifericos")
