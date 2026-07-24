import sqlite3


def crear_tablas():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        clave TEXT
    )
    """)


    cursor.execute("""
    INSERT OR IGNORE INTO usuarios (usuario, clave)
    VALUES ('admin', '1234')
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT,
        direccion TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trabajos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        mueble TEXT,
        descripcion TEXT,
        tela TEXT,
        precio REAL,
        adelanto REAL,
        estado TEXT,
        fecha_entrega TEXT,
        balance REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fotos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trabajo_id INTEGER,
        imagen TEXT,
        descripcion TEXT,
        fecha TEXT,
        imprimir INTEGER DEFAULT 1,

        FOREIGN KEY(trabajo_id)
        REFERENCES trabajos(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT,
        categoria TEXT,
        cantidad REAL,
        unidad TEXT,
        precio REAL
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        descripcion TEXT,
        monto REAL,
        fecha TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresa(

        id INTEGER PRIMARY KEY,

        nombre TEXT,

        telefono TEXT,

        whatsapp TEXT,

        direccion TEXT,

        correo TEXT,

        rnc TEXT,

        mensaje TEXT,

        logo TEXT

    )
    """)

    cursor.execute("""
INSERT OR IGNORE INTO empresa(
id,
nombre,
telefono,
whatsapp,
direccion,
correo,
rnc,
mensaje,
logo
)
VALUES(
1,
'GP TAPICERÍA',
'',
'',
'',
'',
'',
'Gracias por confiar en nosotros.',
'logo.png'
)
""")


    db.commit()
    db.close()