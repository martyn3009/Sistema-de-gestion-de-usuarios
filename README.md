# Sistema de Gestión de Usuarios en Consola

## Descripción
Este proyecto implementa un **Sistema de Gestión de Usuarios** en consola utilizando el lenguaje **Python** para la funcionalidades y **SQLite** para construir la base de datos.    

El sistema permite:
- Registrar usuarios con distintos roles (`user` o `admin`).
- Autenticar usuarios mediante credenciales.
- Listar usuarios registrados.
- Actualizar correos electrónicos.
- Eliminar usuarios (solo aquellos con el de administrador).
- Registrar eventos en una auditoría ( uso de lista enlazada).
- Ejecutar tareas concurrentes de mantenimiento.

---

## Funcionalidades principales
1. **Registro de usuarios** con nombre, contraseña, correo y rol.  
2. **Autenticación** con control de acceso según rol.  
3. **Operaciones CRUD** sobre usuarios.  
4. **Auditoría** de eventos mediante lista enlazada.  
5. **Caché en memoria** con tabla hash para búsquedas rápidas.  
6. **Archivo de configuración (`config.json`)** para parámetros del sistema.  
7. **Concurrencia**: hilo de mantenimiento que ejecuta tareas periódicas.  

---

## Arquitectura
- **Usuario / Admin** → clases base y derivada con encapsulamiento y herencia.  
- **RepositorioUsuariosSQLite** → persistencia en SQLite.  
- **IRepositorioUsuarios** → interfaz que define operaciones CRUD.  
- **GestorUsuarios** → lógica de negocio desacoplada.  
- **RegistroAuditoria** → lista enlazada para eventos.  
- **CacheUsuarios** → tabla hash para cachear usuarios.  
- **menu_principal()** → interfaz de consola interactiva.  

---

## Estructura del proyecto
```
Sistema de gestión de Usuario.py        # Código principal
usuarios.db                # Base de datos SQLite (se crea automáticamente)
config.json                # Archivo de configuración
README.md                  # Documento de instrucciones
```

---

## Instalación y uso

### Requisitos
- Python 3.8 o superior.
- Librería estándar de Python (no requiere paquetes externos).

### Pasos
1. Clona este repositorio:
   ```bash
   git clone 
   cd sistema-usuarios
   ```
2. Ejecuta el programa:
   ```bash
   python Sistema de gestión de Usuario.py
   ```
3. El sistema creará automáticamente:
   - `usuarios.db` (base de datos SQLite).
   - `config.json` (archivo de configuración).

---

## Control de acceso
- **Usuarios (`user`)**: pueden registrarse, iniciar sesión, listar y actualizar su correo.  
- **Administradores (`admin`)**: cumplen con los permisos anteriores, se diferencian en que sólo éstos pueden eliminar usuarios.  

---

## Persistencia
Los datos se almacenan en **`usuarios.db`** utilizando **SQLite**.  
Tablas:
- `roles`: contiene los roles básicos (`user`, `admin`).  
- `usuarios`: almacena credenciales, correo y rol asociado.  

---

## Auditoría (Registro de Eventos)
Cada acción importante (registro, login, actualización, eliminación) se guarda en una **lista enlazada** con timestamp.  
La opción **6 del menú** permite visualizar todos los eventos registrados.

---

## Concurrencia
Un **hilo de mantenimiento** se ejecuta en segundo plano mostrando mensajes periódicos de actividad sin bloquear la interfaz principal.

---

## Autor
- *Donner Chacón*  
- Proyecto académico final del 2do cuatrimestre integrando los conocimientos de: **Programación Orientada a Objetos (POO), Estructuras de Datos, Bases de Datos I y Sistemas Operativos**.  
