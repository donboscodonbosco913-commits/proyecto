# main.py
from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import os

from database import engine, Base, get_db
from models import Usuario, Edificios, Equipo, PcDetalle, GraficaDedicada, TipoDispositivo, HistorialEliminados, Periferico
from crud.usuarios import autenticar_usuario, obtener_usuarios
from crud.edificios import obtener_edificios
from crud.equipos import obtener_equipos_con_filtros, obtener_tipos_dispositivos

# ------------------ Inicialización ------------------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
templates = Jinja2Templates(directory="templates")

# ------------------ Crear Tablas ------------------
# Solo crear si no existe y manejar enums correctamente
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print("Error al crear tablas:", e)

# ------------------ LOGIN ------------------
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(
    request: Request,
    usuario: str = Form(...),
    clave: str = Form(...),
    db: Session = Depends(get_db)
):
    user = autenticar_usuario(db, usuario, clave)
    if user:
        request.session["usuario_id"] = user.id_usuario
        request.session["rol"] = user.rol
        redirect_url = "/admin" if user.rol == "Administrador" else "/usuario"
        return RedirectResponse(redirect_url, status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})

# ------------------ DASHBOARDS ------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
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
        "equipos_activos": db.query(Equipo).filter(Equipo.estado=="Activo").count(),
        "equipos_cpu": db.query(Equipo).join(TipoDispositivo).filter(TipoDispositivo.nombre=="CPU").count(),
        "administradores": db.query(Usuario).filter(Usuario.rol=="Administrador").count(),
        "usuarios_estandar": db.query(Usuario).filter(Usuario.rol=="Estandar").count()
    }

    return templates.TemplateResponse("dashboard_admin.html", {
        "request": request,
        "acciones": acciones,
        "stats": stats
    })

# ------------------ USUARIOS ------------------
@app.get("/usuarios", response_class=HTMLResponse)
def usuarios_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
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
    if db.query(Usuario).filter(Usuario.usuario == usuario).first():
        return templates.TemplateResponse(
            "usuarios.html",
            {"request": request, "error": "El nombre de usuario ya existe.", "usuarios": db.query(Usuario).all()}
        )
    nuevo = Usuario(nombre=nombre, usuario=usuario, clave=clave, rol=rol)
    db.add(nuevo)
    db.commit()
    return RedirectResponse("/usuarios", status_code=302)

# ------------------ EDIFICIOS ------------------
@app.get("/edificios", response_class=HTMLResponse)
def edificios_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("edificios.html", {"request": request, "edificios": obtener_edificios(db)})

@app.post("/edificios/nuevo")
def crear_edificio(request: Request, nombre: str = Form(...), db: Session = Depends(get_db)):
    if db.query(Edificios).filter(Edificios.nombre == nombre).first():
        return templates.TemplateResponse(
            "edificios.html",
            {"request": request, "error": "El edificio ya existe.", "edificios": db.query(Edificios).all()}
        )
    db.add(Edificios(nombre=nombre))
    db.commit()
    return RedirectResponse("/edificios", status_code=302)

# ------------------ EQUIPOS ------------------
@app.get("/equipos", response_class=HTMLResponse)
def equipos_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)

    # Aquí tu lógica de equipos (igual que tu versión original)
    # ...

    return templates.TemplateResponse("equipos.html", {
        "request": request,
        # "equipos": equipos_completos,
        # "edificios": edificios,
        # "tipos": tipos,
        # "mensaje_alert": mensaje_alert
    })

# ------------------ USUARIO DASHBOARD ------------------
@app.get("/usuario", response_class=HTMLResponse)
def usuario_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    filtro: Optional[str] = Query(None),
    id_edificio: Optional[int] = Query(None),
    id_tipo: Optional[int] = Query(None)
):
    if request.session.get("rol") != "Estandar":
        return RedirectResponse("/", status_code=302)

    equipos = obtener_equipos_con_filtros(db, filtro, id_edificio, id_tipo)
    edificios = obtener_edificios(db)
    tipos = obtener_tipos_dispositivos(db)

    return templates.TemplateResponse("dashboard_user.html", {
        "request": request,
        "equipos": equipos,
        "edificios": edificios,
        "tipos": tipos,
        "filtro_actual": filtro or "",
        "id_edificio_actual": id_edificio,
        "id_tipo_actual": id_tipo
    })

# ------------------ CERRAR SESIÓN ------------------
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

# ------------------ MAIN ------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
