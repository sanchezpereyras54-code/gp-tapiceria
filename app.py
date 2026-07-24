from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from database import crear_tablas

app = Flask(__name__)
app.secret_key = "gp-tapiceria"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

crear_tablas()


@app.route("/")
def inicio():

    if "usuario" not in session:
        return redirect("/login")


    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = cursor.fetchone()[0]


    cursor.execute("SELECT COUNT(*) FROM trabajos WHERE estado != 'Entregado'")
    trabajos_pendientes = cursor.fetchone()[0]


    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Ingreso'
    """)
    ingresos = cursor.fetchone()[0] or 0


    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Gasto'
    """)
    gastos = cursor.fetchone()[0] or 0


    cursor.execute("SELECT COUNT(*) FROM inventario")
    materiales = cursor.fetchone()[0]


    db.close()


    return render_template(
        "inicio.html",
        usuario=session["usuario"],
        clientes=total_clientes,
        pendientes=trabajos_pendientes,
        ingresos=ingresos,
        gastos=gastos,
        materiales=materiales
    )


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        clave = request.form["clave"]

        db = sqlite3.connect("database.db")
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT usuario, rol
            FROM usuarios
            WHERE usuario=? AND clave=?
            """,
            (usuario, clave)
        )

        resultado = cursor.fetchone()

        db.close()


        if resultado:

            session["usuario"] = resultado[0]
            session["rol"] = resultado[1]

            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/clientes", methods=["GET","POST"])
def clientes():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    if request.method == "POST":

        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        direccion = request.form["direccion"]

        cursor.execute("""
        INSERT INTO clientes(nombre,telefono,direccion)
        VALUES (?,?,?)
        """,
        (nombre, telefono, direccion))

        db.commit()

    busqueda = request.args.get("buscar")

    if busqueda:

        cursor.execute("""
        SELECT * FROM clientes
        WHERE nombre LIKE ?
        OR telefono LIKE ?
        """,
        (
            "%" + busqueda + "%",
            "%" + busqueda + "%"
        ))

    else:

        cursor.execute("SELECT * FROM clientes")

    lista = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*)

    FROM inventario

    WHERE cantidad <= 5

    """)

    bajos = cursor.fetchone()[0]

    db.close()

    return render_template(
        "clientes.html",
        clientes=lista
    )


@app.route("/trabajos", methods=["GET","POST"])
def trabajos():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        precio = float(request.form["precio"])
        adelanto = float(request.form["adelanto"])

        balance = precio - adelanto

        datos = (
            request.form["cliente_id"],
            request.form["mueble"],
            request.form["descripcion"],
            request.form["tela"],
            precio,
            adelanto,
            request.form["estado"],
            request.form["fecha_entrega"],
            balance
        )


        cursor.execute("""
        INSERT INTO trabajos(
            cliente_id,
            mueble,
            descripcion,
            tela,
            precio,
            adelanto,
            estado,
            fecha_entrega,
            balance
        )
        VALUES (?,?,?,?,?,?,?,?,?)
        """, datos)


        db.commit()



    busqueda = request.args.get("buscar")


    if busqueda:

        cursor.execute("""
        SELECT
            trabajos.id,
            clientes.nombre,
            trabajos.mueble,
            trabajos.descripcion,
            trabajos.tela,
            trabajos.precio,
            trabajos.adelanto,
            trabajos.estado,
            trabajos.fecha_entrega,
            trabajos.balance

        FROM trabajos

        JOIN clientes
        ON clientes.id = trabajos.cliente_id

        WHERE clientes.nombre LIKE ?
        OR trabajos.mueble LIKE ?

        """,
        (
            "%" + busqueda + "%",
            "%" + busqueda + "%"
        ))


    else:

        cursor.execute("""
        SELECT
            trabajos.id,
            clientes.nombre,
            trabajos.mueble,
            trabajos.descripcion,
            trabajos.tela,
            trabajos.precio,
            trabajos.adelanto,
            trabajos.estado,
            trabajos.fecha_entrega,
            trabajos.balance

        FROM trabajos

        JOIN clientes
        ON clientes.id = trabajos.cliente_id

        """)



    lista_trabajos = cursor.fetchall()


    cursor.execute("SELECT * FROM clientes")
    lista_clientes = cursor.fetchall()


    db.close()


    return render_template(
        "trabajos.html",
        trabajos=lista_trabajos,
        clientes=lista_clientes
    )

@app.route("/actualizar_estado/<int:id>", methods=["POST"])
def actualizar_estado(id):

    nuevo_estado = request.form["estado"]

    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    cursor.execute("""
    UPDATE trabajos
    SET estado=?
    WHERE id=?
    """,
    (nuevo_estado, id))

    db.commit()

    db.close()

    return redirect("/trabajos")

@app.route("/orden/<int:id>")
def orden(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    SELECT 
    trabajos.id,
    clientes.nombre,
    trabajos.mueble,
    trabajos.descripcion,
    trabajos.tela,
    trabajos.precio,
    trabajos.adelanto,
    trabajos.estado,
    trabajos.fecha_entrega,
    trabajos.balance

    FROM trabajos

    JOIN clientes
    ON clientes.id = trabajos.cliente_id

    WHERE trabajos.id=?
    """,(id,))


    trabajo = cursor.fetchone()

    cursor.execute("""
    SELECT *
    FROM fotos
    WHERE trabajo_id=?
    AND imprimir=1
    """,(id,))


    fotos = cursor.fetchall()

    cursor.execute("SELECT * FROM empresa WHERE id=1")
    empresa = cursor.fetchone()


    db.close()


    return render_template(
         "orden.html",
         trabajo=trabajo,
         fotos=fotos,
         empresa=empresa
    )

@app.route("/inventario", methods=["GET","POST"])
def inventario():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        datos = (
            request.form["material"],
            request.form["categoria"],
            request.form["cantidad"],
            request.form["unidad"],
            request.form["precio"]
        )


        cursor.execute("""
        INSERT INTO inventario(
            material,
            categoria,
            cantidad,
            unidad,
            precio
        )
        VALUES (?,?,?,?,?)
        """, datos)


        db.commit()



    busqueda = request.args.get("buscar")



    if busqueda:


        cursor.execute("""
        SELECT *
        FROM inventario
        WHERE material LIKE ?
        OR categoria LIKE ?

        """,
        (
            "%" + busqueda + "%",
            "%" + busqueda + "%"
        ))


    else:


        cursor.execute("""
        SELECT *
        FROM inventario
        ORDER BY id DESC
        """)



        lista = cursor.fetchall()


    cursor.execute("""
    SELECT *
    FROM inventario
    WHERE cantidad <= 5
    """)

    bajos = cursor.fetchall()


    db.close()


    return render_template(
        "inventario.html",
        inventario=lista,
        bajos=bajos
    )

@app.route("/caja", methods=["GET","POST"])
def caja():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        datos = (
            request.form["tipo"],
            request.form["descripcion"],
            request.form["monto"],
            request.form["fecha"]
        )


        cursor.execute("""
        INSERT INTO caja(
            tipo,
            descripcion,
            monto,
            fecha
        )
        VALUES (?,?,?,?)
        """, datos)


        db.commit()



    cursor.execute("""
    SELECT *
    FROM caja
    ORDER BY id DESC
    """)

    movimientos = cursor.fetchall()



    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Ingreso'
    """)

    ingresos = cursor.fetchone()[0] or 0




    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Gasto'
    """)

    gastos = cursor.fetchone()[0] or 0




    balance = ingresos - gastos



    db.close()



    return render_template(
        "caja.html",
        caja=movimientos,
        ingresos=ingresos,
        gastos=gastos,
        balance=balance
    )

@app.route("/editar_cliente/<int:id>", methods=["GET","POST"])
def editar_cliente(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    if request.method == "POST":

        cursor.execute("""
        UPDATE clientes
        SET nombre=?, telefono=?, direccion=?
        WHERE id=?
        """,(
            request.form["nombre"],
            request.form["telefono"],
            request.form["direccion"],
            id
        ))

        db.commit()
        db.close()

        return redirect("/clientes")

    cursor.execute("SELECT * FROM clientes WHERE id=?", (id,))
    cliente = cursor.fetchone()

    db.close()

    return render_template(
        "editar_cliente.html",
        cliente=cliente
    )

@app.route("/eliminar_cliente/<int:id>")
def eliminar_cliente(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM clientes WHERE id=?",
        (id,)
    )

    db.commit()
    db.close()

    return redirect("/clientes")

@app.route("/fotos/<int:id>", methods=["GET","POST"])
def fotos(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        archivo = request.files["imagen"]

        if archivo:

            nombre = secure_filename(archivo.filename)

            ruta = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nombre
            )

            archivo.save(ruta)


            cursor.execute("""
            INSERT INTO fotos(
                trabajo_id,
                imagen,
                descripcion,
                fecha,
                imprimir
            )
            VALUES (?,?,?,?,?)
            """,
            (
                id,
                nombre,
                request.form["descripcion"],
                request.form["fecha"],
                1
            ))


            db.commit()



    cursor.execute("""
    SELECT *
    FROM fotos
    WHERE trabajo_id=?
    """,(id,))


    lista_fotos = cursor.fetchall()


    db.close()


    return render_template(
        "fotos.html",
        fotos=lista_fotos,
        trabajo_id=id
    )

@app.route("/actualizar_foto/<int:id>", methods=["POST"])
def actualizar_foto(id):

    imprimir = 1 if "imprimir" in request.form else 0


    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    UPDATE fotos
    SET imprimir=?
    WHERE id=?
    """,
    (
        imprimir,
        id
    ))


    db.commit()

    db.close()


    return redirect(request.referrer)

@app.route("/orden_ticket/<int:id>")
def orden_ticket(id):

    db = sqlite3.connect("database.db")

    cursor = db.cursor()


    cursor.execute("""
    SELECT

    trabajos.id,
    clientes.nombre,
    trabajos.mueble,
    trabajos.descripcion,
    trabajos.tela,
    trabajos.precio,
    trabajos.adelanto,
    trabajos.estado,
    trabajos.fecha_entrega,
    trabajos.balance


    FROM trabajos


    JOIN clientes

    ON clientes.id = trabajos.cliente_id


    WHERE trabajos.id=?

    """,(id,))


    trabajo = cursor.fetchone()

    cursor.execute("SELECT * FROM empresa WHERE id=1")
    empresa = cursor.fetchone()

    db.close()


    return render_template(
        "orden_ticket.html",
        trabajo=trabajo,
        empresa=empresa
    )

@app.route("/editar_inventario/<int:id>", methods=["GET","POST"])
def editar_inventario(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        cursor.execute("""
        UPDATE inventario

        SET material=?,
            categoria=?,
            cantidad=?,
            unidad=?,
            precio=?

        WHERE id=?

        """,
        (
            request.form["material"],
            request.form["categoria"],
            request.form["cantidad"],
            request.form["unidad"],
            request.form["precio"],
            id
        ))


        db.commit()

        db.close()

        return redirect("/inventario")



    cursor.execute("""
    SELECT *

    FROM inventario

    WHERE id=?
    """,(id,))


    item = cursor.fetchone()


    db.close()



    return render_template(
        "editar_inventario.html",
        item=item
    )

@app.route("/eliminar_inventario/<int:id>")
def eliminar_inventario(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    DELETE FROM inventario

    WHERE id=?
    """,(id,))


    db.commit()

    db.close()


    return redirect("/inventario")

@app.route("/backup")
def backup():

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")

    carpeta = "backup/" + fecha


    os.makedirs(carpeta)



    # Copiar base de datos

    shutil.copy(
        "database.db",
        carpeta + "/database.db"
    )



    # Copiar fotos

    if os.path.exists("static/uploads"):

        shutil.copytree(
            "static/uploads",
            carpeta + "/uploads"
        )



    return redirect("/")

@app.route("/restaurar", methods=["POST"])
def restaurar():

    carpeta = request.form["carpeta"]


    origen_db = carpeta + "/database.db"


    if os.path.exists(origen_db):

        shutil.copy(
            origen_db,
            "database.db"
        )


    origen_fotos = carpeta + "/uploads"


    if os.path.exists(origen_fotos):

        if os.path.exists("static/uploads"):

            shutil.rmtree("static/uploads")


        shutil.copytree(
            origen_fotos,
            "static/uploads"
        )


    return render_template(
        "restaurar_ok.html"
    )

@app.route("/restaurar")
def pagina_restaurar():

    backups = []


    if os.path.exists("backup"):

        backups = [
            "backup/" + x
            for x in os.listdir("backup")
        ]


    return render_template(
        "restaurar.html",
        backups=backups
    )


@app.route("/reportes")
def reportes():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    # Trabajos

    cursor.execute("""
    SELECT COUNT(*)
    FROM trabajos
    """)

    total_trabajos = cursor.fetchone()[0]



    cursor.execute("""
    SELECT COUNT(*)
    FROM trabajos
    WHERE estado != 'Entregado'
    """)

    pendientes = cursor.fetchone()[0]



    cursor.execute("""
    SELECT SUM(precio)
    FROM trabajos
    """)

    vendido = cursor.fetchone()[0] or 0



    cursor.execute("""
    SELECT SUM(adelanto)
    FROM trabajos
    """)

    cobrado = cursor.fetchone()[0] or 0



    cursor.execute("""
    SELECT SUM(balance)
    FROM trabajos
    """)

    pendiente_cobro = cursor.fetchone()[0] or 0




    # Caja


    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Ingreso'
    """)

    ingresos = cursor.fetchone()[0] or 0




    cursor.execute("""
    SELECT SUM(monto)
    FROM caja
    WHERE tipo='Gasto'
    """)

    gastos = cursor.fetchone()[0] or 0



    balance = ingresos - gastos



    db.close()



    return render_template(
        "reportes.html",
        total_trabajos=total_trabajos,
        pendientes=pendientes,
        vendido=vendido,
        cobrado=cobrado,
        pendiente_cobro=pendiente_cobro,
        ingresos=ingresos,
        gastos=gastos,
        balance=balance
    )

@app.route("/eliminar_foto/<int:id>")
def eliminar_foto(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    SELECT imagen
    FROM fotos
    WHERE id=?
    """,(id,))


    foto = cursor.fetchone()


    if foto:

        archivo = "static/uploads/" + foto[0]

        if os.path.exists(archivo):

            os.remove(archivo)



        cursor.execute("""
        DELETE FROM fotos
        WHERE id=?
        """,(id,))


        db.commit()



    db.close()


    return redirect(request.referrer)

@app.route("/configuracion", methods=["GET","POST"])
def configuracion():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    if request.method == "POST":

        cursor.execute("""
        UPDATE empresa
        SET
        nombre=?,
        telefono=?,
        whatsapp=?,
        direccion=?,
        correo=?,
        rnc=?,
        mensaje=?
        WHERE id=1
        """,
        (
            request.form["nombre"],
            request.form["telefono"],
            request.form["whatsapp"],
            request.form["direccion"],
            request.form["correo"],
            request.form["rnc"],
            request.form["mensaje"]
        ))

        db.commit()

    cursor.execute("SELECT * FROM empresa WHERE id=1")

    empresa = cursor.fetchone()

    db.close()

    return render_template(
        "configuracion.html",
        empresa=empresa
    )

@app.route("/usuarios", methods=["GET","POST"])
def usuarios():

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    if request.method == "POST":

        cursor.execute("""
        INSERT INTO usuarios(
            usuario,
            clave,
            rol
        )
        VALUES (?,?,?)
        """,
        (
            request.form["usuario"],
            request.form["clave"],
            request.form["rol"]
        ))

        db.commit()


    cursor.execute("""
    SELECT id, usuario, rol
    FROM usuarios
    ORDER BY id DESC
    """)

    lista = cursor.fetchall()


    db.close()


    return render_template(
        "usuarios.html",
        usuarios=lista
    )

@app.route("/eliminar_usuario/<int:id>")
def eliminar_usuario(id):

    db = sqlite3.connect("database.db")
    cursor = db.cursor()


    cursor.execute("""
    DELETE FROM usuarios
    WHERE id=?
    """,(id,))


    db.commit()
    db.close()


    return redirect("/usuarios")

import os
import shutil
from datetime import datetime


def crear_backup():

    carpeta = "backups"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")

    destino = f"{carpeta}/backup_{fecha}.db"

    shutil.copy(
        "database.db",
        destino
    )

from waitress import serve

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=5000)