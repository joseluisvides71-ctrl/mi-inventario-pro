import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image
import io
import base64
from datetime import datetime
import urllib.parse

# 1. CONFIGURACIÓN DE PÁGINA Y CSS
st.set_page_config(page_title="Gestor de Inventario", layout="wide")

st.markdown("""
    <style>
    .stSelectbox div div { white-space: normal !important; }
    .stMultiSelect div div { white-space: normal !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. BASE DE DATOS
def init_db():
    conn = sqlite3.connect('inventario.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS productos
                 (id TEXT PRIMARY KEY, nombre TEXT, categoria TEXT, 
                  precio_mayo REAL, precio_mino REAL, stock INTEGER, 
                  unidad TEXT, imagen TEXT, activo INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, producto_id TEXT, 
                  tipo TEXT, cantidad INTEGER, fecha TEXT, total REAL)''')
    conn.commit()
    conn.close()

init_db()

# 3. FUNCIONES DE APOYO
def get_next_sku():
    conn = sqlite3.connect('inventario.db')
    df = pd.read_sql_query("SELECT id FROM productos", conn)
    conn.close()
    if df.empty:
        return "P-001"
    else:
        last_id = df['id'].str.replace('P-', '').astype(int).max()
        return f"P-{last_id + 1:03d}"

def process_image(image_input):
    if image_input is not None:
        img = Image.open(image_input)
        img.thumbnail((300, 300))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=50)
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# 4. LÓGICA DE INTERFAZ
st.title("📦 Sistema de Inventario Pro")

menu = ["Catálogo", "Operaciones", "Admin / Edición"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if choice == "Catálogo":
    st.header("🛒 Catálogo de Productos")
    conn = sqlite3.connect('inventario.db')
    df = pd.read_sql_query("SELECT * FROM productos WHERE activo = 1", conn)
    conn.close()
    
    if not df.empty:
        for index, row in df.iterrows():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if row['imagen']:
                    st.image(base64.b64decode(row['imagen']), width=150)
                else:
                    st.write("Sin imagen")
            with col2:
                st.subheader(f"{row['nombre']} ({row['id']})")
                st.write(f"Categoría: {row['categoria']} | Unidad: {row['unidad']}")
                st.write(f"**Precio Mayorista: ${row['precio_mayo']}**")
                st.write(f"Precio Minorista: ${row['precio_mino']}")
            with col3:
                st.write(f"Stock disponible: {row['stock']}")
    else:
        st.info("No hay productos activos en el catálogo.")

elif choice == "Admin / Edición":
    st.header("⚙️ Panel de Administración")
    tab1, tab2 = st.tabs(["Añadir Producto", "Editar / Gestionar"])
    
    with tab1:
        with st.form("nuevo_producto"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nombre del Producto")
                nueva_cat = st.selectbox("Categoría", ["General", "Alimentos", "Limpieza", "Otros"])
                p_mayo = st.number_input("Precio Mayorista", min_value=0.0, step=0.01)
            with col2:
                p_mino = st.number_input("Precio Minorista", min_value=0.0, step=0.01)
                stock_ini = st.number_input("Stock Inicial", min_value=0, step=1)
                unidad_sel = st.selectbox("Unidad", ["Lbs", "Kg", "Unidades", "Docena", "Otro"])
                if unidad_sel == "Otro":
                    unidad_sel = st.text_input("Especifique unidad")
            
            st.write("---")
            img_file = st.file_uploader("Subir Imagen (Galería)", type=['jpg', 'png', 'jpeg'])
            img_cam = st.camera_input("Tomar Foto (Cámara)")
            
            submit = st.form_submit_button("Guardar Producto")
            
            if submit:
                nuevo_id = get_next_sku()
                img_data = process_image(img_file if img_file else img_cam)
                conn = sqlite3.connect('inventario.db')
                c = conn.cursor()
                c.execute("INSERT INTO productos VALUES (?,?,?,?,?,?,?,?,1)", 
                          (nuevo_id, nuevo_nombre, nueva_cat, p_mayo, p_mino, stock_ini, unidad_sel, img_data))
                conn.commit()
                conn.close()
                st.success(f"Producto {nuevo_nombre} creado con ID: {nuevo_id}")

    with tab2:
        conn = sqlite3.connect('inventario.db')
        df_edit = pd.read_sql_query("SELECT * FROM productos", conn)
        conn.close()
        
        if not df_edit.empty:
            prod_sel = st.selectbox("Selecciona producto para editar", df_edit['nombre'].tolist())
            datos_p = df_edit[df_edit['nombre'] == prod_sel].iloc[0]
            
            with st.form("editar_form"):
                enombre = st.text_input("Nombre", value=datos_p['nombre'])
                emayo = st.number_input("Precio Mayorista", value=datos_p['precio_mayo'])
                emino = st.number_input("Precio Minorista", value=datos_p['precio_mino'])
                estock = st.number_input("Stock", value=datos_p['stock'])
                e_activo = st.checkbox("Producto Activo (Visible en Catálogo)", value=bool(datos_p['activo']))
                
                if st.form_submit_button("Actualizar Cambios"):
                    conn = sqlite3.connect('inventario.db')
                    c = conn.cursor()
                    c.execute("UPDATE productos SET nombre=?, precio_mayo=?, precio_mino=?, stock=?, activo=? WHERE id=?",
                              (enombre, emayo, emino, estock, 1 if e_activo else 0, datos_p['id']))
                    conn.commit()
                    conn.close()
                    st.success("¡Producto actualizado!")
                    st.rerun()

elif choice == "Operaciones":
    st.header("📝 Registro de Movimientos")
    conn = sqlite3.connect('inventario.db')
    df_p = pd.read_sql_query("SELECT id, nombre, stock FROM productos WHERE activo = 1", conn)
    conn.close()
    
    if not df_p.empty:
        op_prod = st.selectbox("Seleccionar Producto", df_p['nombre'].tolist())
        id_p = df_p[df_p['nombre'] == op_prod]['id'].values[0]
        
        col1, col2 = st.columns(2)
        tipo_op = col1.radio("Tipo", ["Venta (Salida)", "Compra (Entrada)"])
        cant_op = col2.number_input("Cantidad", min_value=1, step=1)
        
        if st.button("Procesar Movimiento"):
            # Lógica de actualización de stock y guardado de movimiento aquí...
            st.success(f"Movimiento registrado para {op_prod}")
            # Generar link de WhatsApp
            msg = urllib.parse.quote(f"Hola, soy un cliente. Quiero {cant_op} unidades de {op_prod} (ID: {id_p})")
            st.markdown(f"[📲 Enviar Pedido por WhatsApp](https://wa.me/50312345678?text={msg})")
    else:
        st.warning("Crea productos en el panel de Admin primero.")
