"""
Sistema de Gestión de Usuarios en Consola
-----------------------------------------
"""

import sqlite3, json, os, threading, time
from getpass import getpass
from datetime import datetime

# -------------------------
# Configuración JSON 
# -------------------------
ARCHIVO_CONFIG = "config.json"
CONFIG_DEF = {"bd": "usuarios.db", "intervalo_mantenimiento": 60}

def cargar_configuracion(ruta=ARCHIVO_CONFIG):
    """
    Carga archivo de configuración JSON.
    Si no existe, crea uno con valores por defecto.
    """
    if not os.path.exists(ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(CONFIG_DEF, f, indent=2)
        return CONFIG_DEF.copy()
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

config = cargar_configuracion()

# -------------------------
# Modelos de Usuario
# -------------------------
class Usuario:
    """Clase base Usuario con atributos encapsulados."""
    def __init__(self, id_usuario, nombre_usuario, correo, rol, creado_en):
        self._id = id_usuario
        self._nombre_usuario = nombre_usuario
        self._correo = correo
        self._rol = rol
        self._creado_en = creado_en

    @property
    def nombre_usuario(self): return self._nombre_usuario
    @property
    def rol(self): return self._rol

class Admin(Usuario):
    """Subclase Admin con permisos adicionales."""
    def eliminar_usuario(self, repositorio, nombre_objetivo):
        """Método exclusivo de Admin para eliminar usuarios."""
        repositorio.eliminar_usuario(nombre_objetivo)

# -------------------------
# Auditoría uso de lista enlazada
# -------------------------
class NodoEvento:
    """Nodo de la lista enlazada para eventos de auditoría."""
    def __init__(self, mensaje, siguiente=None):
        self.mensaje = mensaje
        self.siguiente = siguiente

class RegistroAuditoria:
    """Registro de auditoría implementado como lista enlazada."""
    def __init__(self):
        self.cabeza = None

    def agregar_evento(self, evento):
        """Agrega un evento con la fecha y hora actual al registro."""
        ts = datetime.now().astimezone().strftime('%Y-%m-%d %I:%M:%S %p').lower()
        nodo = NodoEvento(f"{ts} - {evento}", self.cabeza)
        self.cabeza = nodo

    def obtener_eventos(self):
        """Itera sobre los eventos registrados."""
        actual = self.cabeza
        while actual:
            yield actual.mensaje
            actual = actual.siguiente

# -------------------------
# Interfaces y Repositorio
# -------------------------
class IRepositorioUsuarios:
    """Interfaz del repositorio de usuarios."""
    def crear_usuario(self, nombre_usuario, contrasena, correo="", rol="user"): ...
    def obtener_por_nombre(self, nombre_usuario): ...
    def listar_usuarios(self): ...
    def actualizar_correo(self, nombre_usuario, nuevo_correo): ...
    def eliminar_usuario(self, nombre_usuario): ...

class RepositorioUsuariosSQLite(IRepositorioUsuarios):
    """Implementación del repositorio usando SQLite."""
    def __init__(self, ruta_bd=None):
        self.ruta_bd = ruta_bd or config["bd"]
        self._crear_tablas()

    def _conexion(self):
        return sqlite3.connect(self.ruta_bd)

    def _crear_tablas(self):
        """Crea tablas de usuarios y roles si no existen."""
        with self._conexion() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    rol_id INTEGER,
                    creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rol_id) REFERENCES roles(id)
                )
            """)
            conn.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('user')")
            conn.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('admin')")

    def crear_usuario(self, nombre_usuario, contrasena, correo="", rol="user"):
        """Crea un nuevo usuario en la base de datos."""
        try:
            with self._conexion() as conn:
                rol_id = conn.execute("SELECT id FROM roles WHERE nombre=?", (rol,)).fetchone()[0]
                conn.execute(
                    "INSERT INTO usuarios (username, password, email, rol_id) VALUES (?, ?, ?, ?)",
                    (nombre_usuario, contrasena, correo, rol_id)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def obtener_por_nombre(self, nombre_usuario):
        """Obtiene un usuario por su nombre."""
        with self._conexion() as conn:
            return conn.execute("""
                SELECT u.id, u.username, u.password, u.email, r.nombre, u.creado_en
                FROM usuarios u JOIN roles r ON u.rol_id = r.id
                WHERE u.username = ?
            """, (nombre_usuario,)).fetchone()

    def listar_usuarios(self):
        """Lista todos los usuarios registrados."""
        with self._conexion() as conn:
            return conn.execute("""
                SELECT u.username, u.email, r.nombre
                FROM usuarios u JOIN roles r ON u.rol_id = r.id
            """).fetchall()

    def actualizar_correo(self, nombre_usuario, nuevo_correo):
        """Actualiza el correo de un usuario."""
        with self._conexion() as conn:
            conn.execute("UPDATE usuarios SET email=? WHERE username=?", (nuevo_correo, nombre_usuario))

    def eliminar_usuario(self, nombre_usuario):
        """Elimina un usuario por su nombre."""
        with self._conexion() as conn:
            conn.execute("DELETE FROM usuarios WHERE username=?", (nombre_usuario,))

# -------------------------
# Cache (tabla hash)
# -------------------------
class CacheUsuarios:
    """Cache de usuarios implementada como tabla hash."""
    def __init__(self):
        self._mapa = {}

    def guardar(self, nombre_usuario, registro):
        """Guarda un usuario en cache."""
        self._mapa[nombre_usuario] = registro

    def obtener(self, nombre_usuario):
        """Obtiene un usuario desde cache."""
        return self._mapa.get(nombre_usuario)

    def eliminar(self, nombre_usuario):
        """Elimina un usuario de cache."""
        self._mapa.pop(nombre_usuario, None)

# -------------------------
# Gestor de usuarios
# -------------------------
class GestorUsuarios:
    """Gestor de usuarios que depende de la interfaz del repositorio (DIP)."""
    def __init__(self, repositorio: IRepositorioUsuarios, auditoria: RegistroAuditoria, cache: CacheUsuarios):
        self.repositorio = repositorio
        self.auditoria = auditoria
        self.cache = cache

    def registrar_usuario(self, nombre_usuario, contrasena, correo="", rol="user"):
        """Registra un nuevo usuario."""
        creado = self.repositorio.crear_usuario(nombre_usuario, contrasena, correo, rol)
        self.auditoria.agregar_evento(f"crear:{nombre_usuario}")
        return creado

    def autenticar_usuario(self, nombre_usuario, contrasena):
        """Autentica un usuario validando credenciales."""
        fila = self.cache.obtener(nombre_usuario) or self.repositorio.obtener_por_nombre(nombre_usuario)
        if fila and fila[2] == contrasena:
            self.cache.guardar(nombre_usuario, fila)
            self.auditoria.agregar_evento(f"login_ok:{nombre_usuario}")
            return True, fila[4]
        else:
            self.auditoria.agregar_evento(f"login_fail:{nombre_usuario}")
            return False, None

# -------------------------
# Hilo de mantenimiento concurrente
# -------------------------
def tarea_mantenimiento(evento_detener, intervalo):
    """Tarea concurrente que simula mantenimiento periódico."""
    while not evento_detener.is_set():
        time.sleep(intervalo)
        print("[Mantenimiento] El sistema sigue activo...")

# -------------------------
# Interfaz de consola
# -------------------------
def menu_principal():
    """Menú principal de la aplicación en consola."""
    repositorio = RepositorioUsuariosSQLite()
    auditoria = RegistroAuditoria()
    cache = CacheUsuarios()
    gestor = GestorUsuarios(repositorio, auditoria, cache)

    evento_detener = threading.Event()
    hilo = threading.Thread(
        target=tarea_mantenimiento,
        args=(evento_detener, config["intervalo_mantenimiento"]),
        daemon=True
    )
    hilo.start()

    try:
        while True:
            print("\n--- Sistema de Gestión de Usuarios ---")
            print("1) Registrar usuario")
            print("2) Iniciar sesión")
            print("3) Listar usuarios")
            print("4) Actualizar correo")
            print("5) Eliminar usuario (solo admin)")
            print("6) Ver auditoría")
            print("7) Salir")
            opcion = input("Opción: ").strip()

            if opcion == "1":
                usuario = input("Nombre de Usuario: ").strip()
                clave = getpass("Contraseña: ")
                correo = input("Correo: ").strip()
                rol = input("Rol (user/admin): ").strip() or "user"
                creado = gestor.registrar_usuario(usuario, clave, correo, rol)
                print("Usuario creado." if creado else "Error:  Ya existe el usuario.")

            elif opcion == "2":
                usuario = input("Nombre de Usuario: ").strip()
                clave = getpass("Contraseña: ")
                ok, rol = gestor.autenticar_usuario(usuario, clave)
                if ok:
                    print(f"Autenticado. Rol: {rol}")
                    if rol == "admin":
                        print("Acceso completo: puede eliminar usuarios.")
                    else:
                        print("Acceso limitado: no puede eliminar usuarios.")
                else:
                    print("Credenciales inválidas.")

            elif opcion == "3":
                print("\nUsuarios registrados:")
                for u in repositorio.listar_usuarios():
                    print(u)

            elif opcion == "4":
                usuario = input("Nombre de Usuario a actualizar: ").strip()
                nuevo_correo = input("Nuevo email: ").strip()
                repositorio.actualizar_correo(usuario, nuevo_correo)
                auditoria.agregar_evento(f"actualizar_correo:{usuario}")
                print("Correo actualizado.")

            elif opcion == "5":
                usuario_admin = input("Nombre de Usuario admin: ").strip()
                clave_admin = getpass("Contraseña: ")
                fila = repositorio.obtener_por_nombre(usuario_admin)
                if fila and fila[2] == clave_admin and fila[4] == "admin":
                    admin = Admin(fila[0], fila[1], fila[3], fila[4], fila[5])
                    objetivo = input("Nombre de Usuario a eliminar: ").strip()
                    admin.eliminar_usuario(repositorio, objetivo)
                    auditoria.agregar_evento(f"eliminar_usuario(admin):{objetivo}")
                    print("Usuario eliminado por admin.")
                else:
                    print("Acceso denegado: solo admin puede eliminar usuarios.")

            elif opcion == "6":
                print("\nEventos de auditoría:")
                for evento in auditoria.obtener_eventos():
                    print(evento)

            elif opcion == "7":
                print("Saliendo...")
                break

            else:
                print("Opción inválida. Intente nuevamente.")
    finally:
        evento_detener.set()
        hilo.join(timeout=1)

# -------------------------
# Punto de entrada
# -------------------------
if __name__ == "__main__":
    menu_principal()