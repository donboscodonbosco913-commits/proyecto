from fastapi import FastAPI, Request, Form, Depends, Path, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional

from database import engine, Base, get_db
from models import Usuario, Edificios, Equipo, PcDetalle, GraficaDedicada, TipoDispositivo, HistorialEliminados, Periferico
from crud.usuarios import autenticar_usuario, obtener_usuarios
from crud.edificios import obtener_edificios
from crud.equipos import obtener_equipos, obtener_tipos_dispositivos, obtener_equipos_con_filtros

# ------------------ Inicialización ------------------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
templates = Jinja2Templates(directory="templates")
Base.metadata.create_all(bind=engine)

# ------------------ LOGIN ------------------
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, usuario: str = Form(...), clave: str = Form(...), db: Session = Depends(get_db)):
    user = autenticar_usuario(db, usuario, clave)
    if user:
        request.session["usuario_id"] = user.id_usuario
        request.session["rol"] = user.rol
        if user.rol == "Administrador":
            return RedirectResponse("/admin", status_code=302)
        else:
            return RedirectResponse("/usuario", status_code=302)
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
    existente = db.query(Usuario).filter(Usuario.usuario == usuario).first()
    if existente:
        return templates.TemplateResponse("usuarios.html", {
            "request": request,
            "error": "El nombre de usuario ya existe.",
            "usuarios": db.query(Usuario).all()
        })
    nuevo = Usuario(nombre=nombre, usuario=usuario, clave=clave, rol=rol)
    db.add(nuevo)
    db.commit()
    return RedirectResponse("/usuarios", status_code=302)

# ------------------ EDIFICIOS ------------------
@app.get("/edificios", response_class=HTMLResponse)
def edificios_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)
    lista_edificios = obtener_edificios(db)
    return templates.TemplateResponse("edificios.html", {"request": request, "edificios": lista_edificios})

# ------------------ EQUIPOS ------------------
@app.get("/equipos", response_class=HTMLResponse)
def equipos_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
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
            "estado": e.estado,
            "fecha_registro": e.fecha_registro,
            # Inicializamos todos los campos técnicos
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
            # Detalles de PC
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
                # Gráfica dedicada
                grafica = db.query(GraficaDedicada).filter(GraficaDedicada.id_pc == detalle_pc.id_pc).first()
                if grafica:
                    e_dict.update({
                        "grafica_marca": grafica.marca,
                        "grafica_modelo": grafica.modelo,
                        "vram_gb": grafica.vram_gb
                    })

            # Periféricos como diccionarios
            perifericos = db.query(Periferico).filter(Periferico.id_equipo == e.id_equipo).all()
            e_dict["perifericos"] = [
                {
                    "tipo": p.tipo,
                    "marca": p.marca,
                    "modelo": p.modelo,
                    "serie": p.serie
                }
                for p in perifericos
            ]

        equipos_completos.append(e_dict)

    # Manejo de mensajes
    mensaje_alert = None
    if "mensaje" in request.session:
        mensaje_alert = {"tipo": "success", "texto": request.session.pop("mensaje")}
    elif "error" in request.session:
        mensaje_alert = {"tipo": "danger", "texto": request.session.pop("error")}

    return templates.TemplateResponse("equipos.html", {
        "request": request,
        "equipos": equipos_completos,
        "edificios": edificios,
        "tipos": tipos,
        "mensaje_alert": mensaje_alert
    })



# ...existing code...

@app.post("/edificios/nuevo")
def crear_edificio(
    request: Request,
    nombre: str = Form(...),
    db: Session = Depends(get_db)
):
    if request.session.get("rol") != "Administrador":
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

# ...existing code...
# ------------------ ACTUALIZAR DETALLES PC ------------------
@app.post("/equipos/{id_equipo}/detalles/actualizar")
async def actualizar_detalles_pc(  # Cambiar a async
    request: Request,
    id_equipo: int = Path(...),
    ram_gb: Optional[int] = Form(None),
    tipo_ram: Optional[str] = Form(None),
    almacenamiento_gb: Optional[int] = Form(None),
    tipo_almacenamiento: Optional[str] = Form(None),
    procesador: Optional[str] = Form(None),
    otros_detalles: Optional[str] = Form(None),
    grafica_marca: Optional[str] = Form(None),
    grafica_modelo: Optional[str] = Form(None),
    vram_gb: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)

    equipo = db.query(Equipo).filter(Equipo.id_equipo == id_equipo).first()
    if not equipo:
        request.session["error"] = "Equipo no encontrado"
        return RedirectResponse("/equipos", status_code=302)

    try:
        # Obtener datos del formulario
        form_data = await request.form()
        
        detalle_pc = db.query(PcDetalle).filter(PcDetalle.id_equipo == id_equipo).first()
        if not detalle_pc:
            detalle_pc = PcDetalle(id_equipo=id_equipo)
            db.add(detalle_pc)
            db.commit()
            db.refresh(detalle_pc)

        # Actualizar detalles principales
        detalle_pc.ram_gb = ram_gb
        detalle_pc.tipo_ram = tipo_ram
        detalle_pc.almacenamiento_gb = almacenamiento_gb
        detalle_pc.tipo_almacenamiento = tipo_almacenamiento
        detalle_pc.procesador = procesador
        detalle_pc.otros_detalles = otros_detalles

        # Actualizar gráfica
        grafica = db.query(GraficaDedicada).filter(GraficaDedicada.id_pc == detalle_pc.id_pc).first()
        if not grafica:
            grafica = GraficaDedicada(id_pc=detalle_pc.id_pc)
            db.add(grafica)

        grafica.marca = grafica_marca
        grafica.modelo = grafica_modelo
        grafica.vram_gb = vram_gb

        # Eliminar periféricos antiguos
        db.query(Periferico).filter(Periferico.id_equipo == id_equipo).delete()

        # Procesar periféricos del formulario
        perifericos_data = {}
        
        for key, value in form_data.items():
            if key.startswith("perifericos["):
                # Extraer índice y campo - formato: perifericos[0][tipo]
                import re
                match = re.match(r"perifericos\[(\d+)\]\[(\w+)\]", key)
                if match:
                    idx, field = match.groups()
                    if idx not in perifericos_data:
                        perifericos_data[idx] = {}
                    perifericos_data[idx][field] = value

        # Guardar periféricos en la base de datos
        for idx, p_data in perifericos_data.items():
            if p_data.get("tipo"):  # Solo crear si tiene tipo
                nuevo_periferico = Periferico(
                    id_equipo=id_equipo,
                    tipo=p_data.get("tipo"),
                    marca=p_data.get("marca", ""),
                    modelo=p_data.get("modelo", ""),
                    serie=p_data.get("serie", "")
                )
                db.add(nuevo_periferico)

        db.commit()
        request.session["mensaje"] = "✅ Detalles actualizados correctamente"
        
    except Exception as e:
        db.rollback()
        request.session["error"] = f"❌ Error al actualizar: {str(e)}"

    return RedirectResponse("/equipos", status_code=302)




# ------------------ ELIMINAR EQUIPO ------------------
@app.post("/equipos/{id_equipo}/eliminar")
def eliminar_equipo(request: Request, id_equipo: int = Path(...), db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)

    equipo = db.query(Equipo).filter(Equipo.id_equipo == id_equipo).first()
    if not equipo:
        request.session["error"] = f"No se encontró el equipo con ID {id_equipo}"
        return RedirectResponse("/equipos", status_code=302)

    try:
        detalle_pc = db.query(PcDetalle).filter(PcDetalle.id_equipo == id_equipo).first()
        if detalle_pc:
            db.execute(text("CALL eliminar_pc_historial_ext(:p_id_pc)"), {"p_id_pc": detalle_pc.id_pc})
        else:
            historial = HistorialEliminados(
                id_equipo=equipo.id_equipo,
                codigo=equipo.codigo,
                id_edificio=equipo.id_edificio,
                id_tipo=equipo.id_tipo,
                marca=equipo.marca,
                modelo=equipo.modelo,
                serie=equipo.serie,
                estado="Eliminado"
            )
            db.add(historial)
            db.delete(equipo)

        db.commit()
        request.session["mensaje"] = f"✅ Equipo {equipo.codigo} eliminado correctamente."
    except Exception as e:
        db.rollback()
        
    return RedirectResponse("/equipos", status_code=302)


#-------------------NUEVO EQUIPO-----------------------
@app.post("/equipos/nuevo")
async def crear_equipo(
    request: Request,
    codigo: str = Form(...),
    id_edificio: int = Form(...),
    id_tipo: int = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    serie: str = Form(...),
    estado: str = Form(...),
    # Opcionales para PC
    ram_gb: Optional[int] = Form(None),
    tipo_ram: Optional[str] = Form(None),
    almacenamiento_gb: Optional[int] = Form(None),
    tipo_almacenamiento: Optional[str] = Form(None),
    procesador: Optional[str] = Form(None),
    otros_detalles: Optional[str] = Form(None),
    grafica_marca: Optional[str] = Form(None),
    grafica_modelo: Optional[str] = Form(None),
    vram_gb: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)

    form_data = await request.form()

    try:
        # Crear el equipo básico
        nuevo_equipo = Equipo(
            codigo=codigo,
            id_edificio=id_edificio,
            id_tipo=id_tipo,
            marca=marca,
            modelo=modelo,
            serie=serie,
            estado=estado,
            fecha_registro=datetime.now()
        )
        db.add(nuevo_equipo)
        db.commit()
        db.refresh(nuevo_equipo)

        # Revisar si el tipo es CPU para agregar detalles
        tipo_obj = db.query(TipoDispositivo).filter(TipoDispositivo.id_tipo == id_tipo).first()
        if tipo_obj and tipo_obj.nombre.lower() == "cpu":
            # Detalles de PC
            detalle_pc = PcDetalle(
                id_equipo=nuevo_equipo.id_equipo,
                ram_gb=ram_gb,
                tipo_ram=tipo_ram,
                almacenamiento_gb=almacenamiento_gb,
                tipo_almacenamiento=tipo_almacenamiento,
                procesador=procesador,
                otros_detalles=otros_detalles
            )
            db.add(detalle_pc)
            db.commit()
            db.refresh(detalle_pc)

            # Gráfica dedicada
            if grafica_marca or grafica_modelo or vram_gb:
                grafica = GraficaDedicada(
                    id_pc=detalle_pc.id_pc,
                    marca=grafica_marca,
                    modelo=grafica_modelo,
                    vram_gb=vram_gb
                )
                db.add(grafica)
                db.commit()

            # Periféricos
            perifericos_data = {}
            import re
            for key, value in form_data.items():
                if key.startswith("perifericos["):
                    match = re.match(r"perifericos\[(\d+)\]\[(\w+)\]", key)
                    if match:
                        idx, field = match.groups()
                        if idx not in perifericos_data:
                            perifericos_data[idx] = {}
                        perifericos_data[idx][field] = value

            for idx, p_data in perifericos_data.items():
                if p_data.get("tipo"):  # solo si tiene tipo
                    nuevo_periferico = Periferico(
                        id_equipo=nuevo_equipo.id_equipo,
                        tipo=p_data.get("tipo"),
                        marca=p_data.get("marca", ""),
                        modelo=p_data.get("modelo", ""),
                        serie=p_data.get("serie", "")
                    )
                    db.add(nuevo_periferico)
            db.commit()

        request.session["mensaje"] = f"✅ Equipo {codigo} creado correctamente."

    except Exception as e:
        db.rollback()
        request.session["error"] = f"❌ Error al crear equipo: {str(e)}"

    return RedirectResponse("/equipos", status_code=302)


# ------------------ HISTORIAL ------------------
@app.get("/historial", response_class=HTMLResponse)
def historial_view(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Administrador":
        return RedirectResponse("/", status_code=302)

    historial = db.query(HistorialEliminados).all()
    mensaje = request.session.pop("mensaje", None)
    error = request.session.pop("error", None)

    return templates.TemplateResponse("historial.html", {
        "request": request,
        "historial": historial,
        "mensaje": mensaje,
        "error": error
    })

# ------------------ CERRAR SESIÓN ------------------
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

# ------------------ DASHBOARD USUARIO ------------------
@app.get("/usuario", response_class=HTMLResponse)
def usuario_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    filtro: Optional[str] = Query(None),
    id_edificio: Optional[str] = Query(None),
    id_tipo: Optional[str] = Query(None)
):
    if request.session.get("rol") != "Estandar":
        return RedirectResponse("/", status_code=302)

    filtro_clean = filtro if filtro and filtro.strip() else None

    id_edificio_int = None
    if id_edificio and id_edificio.strip():
        try:
            id_edificio_int = int(id_edificio)
        except ValueError:
            id_edificio_int = None

    id_tipo_int = None
    if id_tipo and id_tipo.strip():
        try:
            id_tipo_int = int(id_tipo)
        except ValueError:
            id_tipo_int = None

    equipos = obtener_equipos_con_filtros(db, filtro_clean, id_edificio_int, id_tipo_int)
    edificios = obtener_edificios(db)
    tipos = obtener_tipos_dispositivos(db)

    return templates.TemplateResponse("dashboard_user.html", {
        "request": request,
        "equipos": equipos,
        "edificios": edificios,
        "tipos": tipos,
        "filtro_actual": filtro or "",
        "id_edificio_actual": id_edificio_int,
        "id_tipo_actual": id_tipo_int
    })

# ------------------ DETALLE EQUIPO USUARIO ------------------
@app.get("/usuario/equipo/{id_equipo}", response_class=HTMLResponse)
def ver_equipo_detalle(request: Request, id_equipo: int, db: Session = Depends(get_db)):
    if request.session.get("rol") != "Estandar":
        return RedirectResponse("/", status_code=302)
    
    equipo = db.query(Equipo).filter(Equipo.id_equipo == id_equipo, Equipo.estado == "Activo").first()
    
    if not equipo:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "mensaje": "Equipo no encontrado"
        })
    
    perifericos = []
    if equipo.tipo.nombre.lower() == 'cpu':
        perifericos = db.query(Periferico).filter(Periferico.id_equipo == id_equipo).all()
    
    return templates.TemplateResponse("detalle_equipo.html", {
        "request": request,
        "equipo": equipo,
        "perifericos": perifericos
    })
