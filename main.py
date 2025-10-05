from fastapi import FastAPI, Request, Form, Depends, Path, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from database import engine, Base, get_db
from models import (
    Usuario, Edificios, Equipo, PcDetalle, GraficaDedicada,
    TipoDispositivo, HistorialEliminados, Periferico,
    RolEnum, EstadoEnum
)
from crud.usuarios import autenticar_usuario, obtener_usuarios
from crud.edificios import obtener_edificios
from crud.equipos import obtener_equipos_con_filtros

# ------------------ INICIALIZACIÓN ------------------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
templates = Jinja2Templates(directory="templates")

# ⚠️ IMPORTANTE: si ya tienes BD montada en Postgres, no recrees todo cada vez.
# Base.metadata.create_all(bind=engine)

# ------------------ LOGIN ------------------
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, usuario: str = Form(...), clave: str = Form(...), db: Session = Depends(get_db)):
    user = autenticar_usuario(db, usuario, clave)
    if user:
        request.session["usuario_id"] = user.id_usuario
        request.session["rol"] = user.rol.value  # ✅ Guardar valor del Enum
        if user.rol == RolEnum.Administrador:
            return RedirectResponse("/admin", status_code=302)
        else:
            return RedirectResponse("/usuario", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

# ------------------ DASHBOARD ADMIN ------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)

    acciones = [
        {"nombre": "Nuevo Equipo", "icono": "fas fa-plus", "url": "/equipos?nuevo=true", "clase": "success"},
        {"nombre": "Nuevo Usuario", "icono": "fas fa-user-plus", "url": "/usuarios?nuevo=true", "clase": "info"},
        {"nombre": "Nuevo Edificio", "icono": "fas fa-building", "url": "/edificios?nuevo=true", "clase": "warning"},
        {"nombre": "Auditar Sistema", "icono": "fas fa-search", "url": "/historial", "clase": "secondary"}
    ]

    stats = {
        "total_usuarios": db.query(Usuario).count(),
        "total_edificios": db.query(Edificios).count(),
        "total_equipos": db.query(Equipo).count(),
        "total_historial": db.query(HistorialEliminados).count(),
        "equipos_activos": db.query(Equipo).filter(Equipo.estado == EstadoEnum.Activo).count(),
        "equipos_cpu": db.query(Equipo).join(TipoDispositivo).filter(TipoDispositivo.nombre == "CPU").count(),
        "administradores": db.query(Usuario).filter(Usuario.rol == RolEnum.Administrador).count(),
        "usuarios_estandar": db.query(Usuario).filter(Usuario.rol == RolEnum.Estandar).count()
    }

    return templates.TemplateResponse("dashboard_admin.html", {
        "request": request,
        "acciones": acciones,
        "stats": stats
    })

# ------------------ DASHBOARD USUARIO ------------------
@app.get("/usuario", response_class=HTMLResponse)
def usuario_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    filtro: Optional[str] = Query(None),
    id_edificio: Optional[str] = Query(None),
    id_tipo: Optional[str] = Query(None)
):
    if request.session.get("rol") != RolEnum.Estandar.value:
        return RedirectResponse("/", status_code=302)

    filtro_clean = filtro.strip() if filtro and filtro.strip() else None

    id_edificio_int = int(id_edificio) if id_edificio and id_edificio.isdigit() else None
    id_tipo_int = int(id_tipo) if id_tipo and id_tipo.isdigit() else None

    equipos = obtener_equipos_con_filtros(db, filtro_clean, id_edificio_int, id_tipo_int)
    edificios = obtener_edificios(db)
    tipos = db.query(TipoDispositivo).all()

    return templates.TemplateResponse("dashboard_user.html", {
        "request": request,
        "equipos": equipos,
        "edificios": edificios,
        "tipos": tipos,
        "filtro_actual": filtro or "",
        "id_edificio_actual": id_edificio_int,
        "id_tipo_actual": id_tipo_int
    })

# ------------------ USUARIOS ------------------
@app.get("/usuarios", response_class=HTMLResponse)
def usuarios_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)
    lista_usuarios = obtener_usuarios(db)
    return templates.TemplateResponse("usuarios.html", {"request": request, "usuarios": lista_usuarios})

@app.post("/usuarios/nuevo")
def crear_usuario(
    request: Request,
    nombre: str = Form(...),
    usuario: str = Form(...),
    clave: str = Form(...),
    rol: str = Form(...),
    db: Session = Depends(get_db)
):
    existente = db.query(Usuario).filter(Usuario.usuario == usuario).first()
    if existente:
        return templates.TemplateResponse("usuarios.html", {
            "request": request,
            "error": "El nombre de usuario ya existe.",
            "usuarios": db.query(Usuario).all()
        })
    nuevo = Usuario(nombre=nombre, usuario=usuario, clave=clave, rol=RolEnum(rol))
    db.add(nuevo)
    db.commit()
    return RedirectResponse("/usuarios", status_code=302)

@app.post("/usuarios/{id_usuario}/eliminar")
def eliminar_usuario(request: Request, id_usuario: int = Path(...), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        return templates.TemplateResponse("usuarios.html", {
            "request": request,
            "error": "Usuario no encontrado.",
            "usuarios": db.query(Usuario).all()
        })
    db.delete(usuario)
    db.commit()
    return RedirectResponse("/usuarios", status_code=302)

# ------------------ EDIFICIOS ------------------
@app.get("/edificios", response_class=HTMLResponse)
def edificios_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)
    lista_edificios = obtener_edificios(db)
    return templates.TemplateResponse("edificios.html", {"request": request, "edificios": lista_edificios})

@app.post("/edificios/nuevo")
def crear_edificio(request: Request, nombre: str = Form(...), db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)
    existente = db.query(Edificios).filter(Edificios.nombre == nombre).first()
    if existente:
        return templates.TemplateResponse("edificios.html", {
            "request": request,
            "error": "El edificio ya existe.",
            "edificios": db.query(Edificios).all()
        })
    nuevo = Edificios(nombre=nombre)
    db.add(nuevo)
    db.commit()
    return RedirectResponse("/edificios", status_code=302)

# ------------------ EQUIPOS ------------------
@app.get("/equipos", response_class=HTMLResponse)
def equipos_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)

    equipos = db.query(Equipo).all()
    edificios = db.query(Edificios).all()
    tipos = db.query(TipoDispositivo).all()

    equipos_completos = []

    for e in equipos:
        e_dict = {
            "id_equipo": e.id_equipo,
            "codigo": e.codigo,
            "edificio_nombre": e.edificio.nombre if e.edificio else "",
            "tipo_nombre": e.tipo.nombre if e.tipo else "",
            "marca": e.marca,
            "modelo": e.modelo,
            "serie": e.serie,
            "estado": e.estado.value if e.estado else "",
            "fecha_registro": e.fecha_registro,
            "ram_gb": None,
            "tipo_ram": None,
            "almacenamiento_gb": None,
            "tipo_almacenamiento": None,
            "procesador": None,
            "otros_detalles": None,
            "grafica_marca": None,
            "grafica_modelo": None,
            "vram_gb": None,
            "perifericos": []
        }

        if e_dict["tipo_nombre"].lower() == "cpu":
            detalle_pc = db.query(PcDetalle).filter(PcDetalle.id_equipo == e.id_equipo).first()
            if detalle_pc:
                e_dict.update({
                    "ram_gb": detalle_pc.ram_gb,
                    "tipo_ram": detalle_pc.tipo_ram,
                    "almacenamiento_gb": detalle_pc.almacenamiento_gb,
                    "tipo_almacenamiento": detalle_pc.tipo_almacenamiento,
                    "procesador": detalle_pc.procesador,
                    "otros_detalles": detalle_pc.otros_detalles
                })
                grafica = db.query(GraficaDedicada).filter(GraficaDedicada.id_pc == detalle_pc.id_pc).first()
                if grafica:
                    e_dict.update({
                        "grafica_marca": grafica.marca,
                        "grafica_modelo": grafica.modelo,
                        "vram_gb": grafica.vram_gb
                    })

            perifericos = db.query(Periferico).filter(Periferico.id_equipo == e.id_equipo).all()
            e_dict["perifericos"] = [
                {"tipo": p.tipo, "marca": p.marca, "modelo": p.modelo, "serie": p.serie}
                for p in perifericos
            ]

        equipos_completos.append(e_dict)

    return templates.TemplateResponse("equipos.html", {
        "request": request,
        "equipos": equipos_completos,
        "edificios": edificios,
        "tipos": tipos
    })

# ------------------ HISTORIAL ------------------
@app.get("/historial", response_class=HTMLResponse)
def historial_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Administrador.value:
        return RedirectResponse("/", status_code=302)

    historial = db.query(HistorialEliminados).all()
    return templates.TemplateResponse("historial.html", {
        "request": request,
        "historial": historial
    })

# ------------------ DETALLE EQUIPO USUARIO ------------------
@app.get("/usuario/equipo/{id_equipo}", response_class=HTMLResponse)
def ver_equipo_detalle(request: Request, id_equipo: int, db: Session = Depends(get_db)):
    if request.session.get("rol") != RolEnum.Estandar.value:
        return RedirectResponse("/", status_code=302)
    
    equipo = db.query(Equipo).filter(
        Equipo.id_equipo == id_equipo,
        Equipo.estado == EstadoEnum.Activo
    ).first()
    if not equipo:
        return templates.TemplateResponse("error.html", {"request": request, "mensaje": "Equipo no encontrado"})
    
    perifericos = []
    if equipo.tipo.nombre.lower() == 'cpu':
        perifericos = db.query(Periferico).filter(Periferico.id_equipo == id_equipo).all()
    
    return templates.TemplateResponse("detalle_equipo.html", {
        "request": request,
        "equipo": equipo,
        "perifericos": perifericos
    })
