import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image
from duckduckgo_search import DDGS
import datetime
import json
import re
from fpdf import FPDF
import urllib.parse
import zipfile
import io
import subprocess

# ==========================================
# ⚙️ CONFIGURACIÓN Y ESTILOS - VYNTARA OS
# ==========================================

# --- CONFIGURACIÓN DE API KEY INICIAL ---
try:
    API_KEY_DEFAULT = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    API_KEY_DEFAULT = ""

NOMBRE_LOGO = "logo.jpg"
directorio_actual = os.getcwd()
ruta_logo = os.path.join(directorio_actual, NOMBRE_LOGO)

st.set_page_config(page_title="Vyntara OS | Agency Management System", page_icon="✨", layout="wide")

# --- LEER CLAVE GUARDADA AL CARGAR LA APP ---
if "api_key_activa" not in st.session_state or not st.session_state["api_key_activa"]:
    if os.path.exists("api_key.txt"):
        try:
            with open("api_key.txt", "r") as f:
                key_guardada = f.read().strip()
                st.session_state["api_key_activa"] = key_guardada if key_guardada else API_KEY_DEFAULT
        except Exception:
            st.session_state["api_key_activa"] = API_KEY_DEFAULT
    else:
        st.session_state["api_key_activa"] = API_KEY_DEFAULT

# CSS Avanzado para Interfaz Profesional (SaaS)
st.markdown("""
    <head><meta name="google" content="notranslate"></head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        .stApp { translate: no; background-color: #f1f5f9; color: #1e293b; font-family: 'Inter', sans-serif; }
        
        /* Tarjetas de Métricas */
        div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: all 0.2s ease;}
        div[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        
        /* Botones Primarios Modernos */
        .stButton>button[kind="primary"] { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: #ffffff; border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2); transition: all 0.2s ease;}
        .stButton>button[kind="primary"]:hover { opacity: 0.9; transform: translateY(-1px); box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3); }
        
        /* Tarjetas Personalizadas */
        .kanban-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-left: 4px solid #94a3b8; }
        .post-card-blue { background-color: white; border-left: 5px solid #2563eb; padding: 16px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 12px; }
        .post-card-indigo { background-color: white; border-left: 5px solid #4f46e5; padding: 16px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 12px; }
        
        /* Badges / Etiquetas */
        .badge-status { background-color: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-block; margin-top: 8px;}
    </style>
""", unsafe_allow_html=True)

# Variables de Sesión
if "api_key_activa" not in st.session_state:
    st.session_state["api_key_activa"] = API_KEY_DEFAULT
if "redes_disponibles" not in st.session_state:
    st.session_state["redes_disponibles"] = ["Instagram", "TikTok", "Facebook", "LinkedIn", "YouTube", "Threads", "X/Twitter"]

# Columnas estrictas de la Parrilla
columnas_parrilla = [
    "ID", "Cliente", "Red_Social", "Fecha_Publicacion", "Tipo_Contenido", 
    "Nombre_Publicacion", "Detalle_Visual_Diseno", "Copy_Texto", "Hashtags", 
    "Publico_Objetivo", "Tipo_Pauta", "Inversion_Pauta_COP", "Dias_Pauta_Recomendados", "Estado"
]

# Funciones de Soporte Generales
def cargar_datos(archivo, columnas):
    ruta = os.path.join(directorio_actual, archivo)
    if not os.path.exists(ruta):
        df = pd.DataFrame(columns=columnas)
        df.to_csv(ruta, index=False)
    else:
        df = pd.read_csv(ruta)
        for col in columnas:
            if col not in df.columns:
                df[col] = ""
        df = df.reindex(columns=columnas)
        df = df.astype(object)
        df.fillna("", inplace=True)
    return df

def guardar_datos(archivo, df):
    df.to_csv(os.path.join(directorio_actual, archivo), index=False)

import google.generativeai as genai

def obtener_modelos_sincronizados(api_key):
    """Sincroniza directamente con Google la lista de modelos activos en este instante."""
    try:
        genai.configure(api_key=api_key)
        modelos_disponibles = []
        for m in genai.list_models():
            # Filtramos solo los modelos capacitados para generar texto/contenido
            if 'generateContent' in m.supported_generation_methods:
                nombre_limpio = m.name.replace("models/", "").strip()
                modelos_disponibles.append(nombre_limpio)
        
        # Priorizamos las versiones flash más rápidas al inicio de la lista
        modelos_disponibles.sort(key=lambda x: ("flash" not in x, x))
        return modelos_disponibles if modelos_disponibles else ["gemini-2.5-flash"]
    except Exception:
        # Respaldo seguro en caso de falla de conexión
        return ["gemini-2.5-flash", "gemini-2.0-flash"]

def consultar_gemini(prompt, modelo_nombre=None, imagen=None):
    try:
        api_key = st.session_state.get("api_key_activa", "").strip()
        if not api_key:
            st.error("⚠️ Clave API de Gemini faltante.")
            return None

        genai.configure(api_key=api_key)

        # Usamos el modelo seleccionado en la barra lateral o el valor por defecto
        mod = modelo_nombre or st.session_state.get("modelo_ia_activo", "gemini-2.5-flash")
        mod_limpio = str(mod).replace("models/", "").strip()

        model = genai.GenerativeModel(mod_limpio)

        if imagen:
            return model.generate_content([prompt, imagen])
        return model.generate_content(prompt)

    except Exception as e:
        st.error(f"⚠️ Error al consultar el modelo '{mod_limpio}': {e}")
        return None

def limpiar_json_gemini(texto_respuesta):
    try:
        texto = texto_respuesta.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if match:
            texto = match.group(0)
        return json.loads(texto)
    except json.JSONDecodeError:
        return None

def buscar_en_internet(query, max_resultados=5):
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=max_resultados))
            return "".join([f"Título: {r['title']}\nResumen: {r['body']}\n\n" for r in resultados])
    except Exception as e:
        return f"Error en búsqueda web: {e}"

def obtener_datos_agent_reach(canal: str, objetivo: str) -> str:
    if not objetivo:
        return "Falta objetivo para Agent-Reach."
    try:
        cmd = ["agent-reach", "run", canal, objetivo]
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=35, encoding="utf-8", errors="replace")
        if resultado.returncode == 0 and resultado.stdout.strip():
            return resultado.stdout.strip()
        return f"[Agent-Reach] Sin resultados exitosos."
    except Exception as e:
        return f"[Agent-Reach Error] {str(e)}"

def sanitizar_texto_pdf(texto):
    texto_str = str(texto)
    reemplazos = {'“': '"', '”': '"', '‘': "'", '’': "'", '–': '-', '—': '-', '…': '...'}
    for k, v in reemplazos.items():
        texto_str = texto_str.replace(k, v)
    return texto_str.encode('latin-1', 'ignore').decode('latin-1')

def generar_pdf_cotizacion(empresa, atencion_a, tipo_trabajo, desglose, fee_total, observaciones):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, sanitizar_texto_pdf("VYNTARA DIGITAL AGENCY"), 0, 1, "C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 5, sanitizar_texto_pdf("Propuesta Comercial & Cotizacion de Servicios"), 0, 1, "C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, sanitizar_texto_pdf(f"CLIENTE / EMPRESA: {empresa}"), 0, 1)
    pdf.cell(0, 6, sanitizar_texto_pdf(f"ATENCION A: {atencion_a}"), 0, 1)
    pdf.cell(0, 6, sanitizar_texto_pdf(f"TIPO DE PROYECTO: {tipo_trabajo}"), 0, 1)
    pdf.cell(0, 6, sanitizar_texto_pdf(f"FECHA DE EMISION: {datetime.date.today().strftime('%d/%m/%Y')}"), 0, 1)
    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, sanitizar_texto_pdf("DESGLOSE TACTICO DE ENTREGABLES"), 0, 1)
    pdf.set_font("Arial", "", 10)
    for item in desglose:
        pdf.cell(0, 6, sanitizar_texto_pdf(f"- {item}"), 0, 1)
    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, sanitizar_texto_pdf(f"INVERSION TOTAL ESTIMADA: ${fee_total:,.0f} COP / mes"), 1, 1, "C")
    if observaciones:
        pdf.ln(6)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, sanitizar_texto_pdf("Alcance & Condiciones:"), 0, 1)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, sanitizar_texto_pdf(observaciones))
    pdf.ln(15)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 5, sanitizar_texto_pdf("Vyntara Digital | Transformando Marcas con Estrategia e IA"), 0, 1, "C")
    salida = pdf.output()
    if isinstance(salida, str):
        return salida.encode('latin-1', 'ignore')
    return bytes(salida)

def crear_link_whatsapp(numero, mensaje):
    num_limpio = "".join(filter(str.isdigit, str(numero)))
    msg_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{num_limpio}?text={msg_encoded}"

# Cargar Bases de Datos CSV
df_clientes = cargar_datos("clientes.csv", ["Nombre", "Empresa", "Redes a Manejar", "Estado", "Telefono", "Nicho"])
df_finanzas = cargar_datos("finanzas.csv", ["Empresa", "Valor Contrato ($)", "Fecha Inicio", "Fecha Fin", "Estado Pago", "Enlace_Contrato", "Soporte_Pago"])
df_parrilla = cargar_datos("parrilla_contenidos.csv", columnas_parrilla)
df_ads = cargar_datos("ads_analytics.csv", ["Cliente", "Campaña", "Plataforma", "Presupuesto Asignado ($)", "Gasto Actual ($)", "Impresiones", "Clics", "Estado"])
df_entregables = cargar_datos("sla_entregables.csv", ["Cliente", "Entregable", "Fecha_Limite", "Estado", "SLA_Cumplido"])
df_vyntara = cargar_datos("vyntara_inhouse.csv", ["Red_Social", "Usuario_Handle", "Seguidores", "Engagement_Rate", "Leads_Generados", "Experimento_Sandbox"])
df_brandkits = cargar_datos("brandkits.csv", ["Cliente", "Colores_HEX", "Tipografias", "Link_Drive_Canva", "Credenciales_Redes", "Notas_Marca"])
df_leads_vyntara = cargar_datos("vyntara_leads.csv", ["Empresa_Prospecto", "Contacto", "Telefono", "Valor_Cotizado", "Estado_Pipeline", "Notas"])
df_briefings = cargar_datos("briefings_clientes.csv", ["Cliente", "Sector", "Objetivos", "Audiencia", "Competidores", "URL_Competidor", "Canal_Reach", "Tono", "Presupuesto", "Fecha"])
df_contratos = cargar_datos("contratos.csv", ["ID_Contrato", "Cliente", "Servicios", "Redes", "Valor_Contrato", "Estado_Pago", "Fecha_Inicio", "Fecha_Fin", "Estado_Contrato", "Notas", "Acuerdos"])

ESTADOS_POSIBLES = ["💡 Idea", "✍️ Guión / Copy", "🎨 Diseño / Edición", "✅ Programado", "🚀 Publicado / Pautado"]
ESTADOS_PAGO = ["Pendiente", "Abono / Pago Parcial", "Pagado"]

# ==========================================
# 🧭 NAVEGACIÓN Y MENÚ LATERAL
# ==========================================
st.sidebar.title("✨ Vyntara OS")

if os.path.exists(ruta_logo):
    try:
        st.sidebar.image(Image.open(ruta_logo), use_container_width=True)
    except:
        pass

# --- SINCRONIZACIÓN AUTOMÁTICA EN LA BARRA LATERAL ---
api_key_limpia = str(st.session_state.get("api_key_activa", "")).strip()

if api_key_limpia:
    modelos_disponibles = obtener_modelos_sincronizados(api_key_limpia)
else:
    modelos_disponibles = ["gemini-2.5-flash", "gemini-2.0-flash"]

modelo_seleccionado = st.sidebar.selectbox(
    "⚙️ Modelo IA Activo (Sincronizado)",
    options=modelos_disponibles,
    key="modelo_ia_activo"
)

if api_key_limpia:
    st.sidebar.success("🟢 Conectado a Gemini")
else:
    st.sidebar.warning("⚠️ Sin API Key")

st.sidebar.markdown("---")

espacio_trabajo = st.sidebar.radio(
    "📌 Módulos del Sistema:",
    [
        "🎛️ Torre de Control General (Finanzas & Alertas)",
        "👥 Directorio de Clientes (CRM)",
        "🏢 Gestión de Clientes (Operación Individual)",
        "🔍 Módulo C: Auditoría & Briefing Express",
        "🔥 Agencia Vyntara (Estrategia In-House)",
        "📄 Cotizador & Generador de PDF",
        "👁️ Portal Cliente (Aprobación Externa)",
        "⚙️ Configuración Global & Respaldos"
    ]
)
st.sidebar.markdown("---")

# ==========================================
# 0. TORRE DE CONTROL GENERAL (ACTUALIZADA)
# ==========================================
if espacio_trabajo == "🎛️ Torre de Control General (Finanzas & Alertas)":
    st.title("🎛️ Torre de Control General | Visión Global de la Agencia")
    
    # 1. FILTROS GLOBALES DE FECHA
    st.markdown("### 🗓️ Rango de Fechas Global")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_inicio_filtro = st.date_input("Desde:", datetime.date.today().replace(day=1))
    with col_f2:
        fecha_fin_filtro = st.date_input("Hasta:", datetime.date.today())
        
    st.markdown("---")

    # 2. PROCESAMIENTO DE DATOS DE CONTRATOS Y FINANZAS
    mrr_total = 0.0
    cobrado_total = 0.0
    por_cobrar_total = 0.0
    facturas_pendientes = 0

    # Prioridad 1: Usar df_contratos si tiene datos
    if not df_contratos.empty:
        df_c_temp = df_contratos.copy()
        df_c_temp["Fecha_Inicio_dt"] = pd.to_datetime(df_c_temp["Fecha_Inicio"], errors='coerce').dt.date
        df_c_temp["Valor_Num"] = pd.to_numeric(df_c_temp["Valor_Contrato"], errors='coerce').fillna(0.0)

        mask = (df_c_temp["Fecha_Inicio_dt"] >= fecha_inicio_filtro) & (df_c_temp["Fecha_Inicio_dt"] <= fecha_fin_filtro)
        df_filtrado = df_c_temp[mask]

        mrr_total = df_filtrado["Valor_Num"].sum()
        
        cobrado_df = df_filtrado[df_filtrado["Estado_Pago"].isin(["Al Día", "Pagado"])]
        cobrado_total = cobrado_df["Valor_Num"].sum()

        por_cobrar_df = df_filtrado[df_filtrado["Estado_Pago"].isin(["Pendiente", "Mora", "Abono / Pago Parcial"])]
        por_cobrar_total = por_cobrar_df["Valor_Num"].sum()
        facturas_pendientes = len(por_cobrar_df)

    # Prioridad 2: Usar df_finanzas si contratos está vacío
    elif not df_finanzas.empty:
        df_f_temp = df_finanzas.copy()
        df_f_temp["Valor_Num"] = pd.to_numeric(df_f_temp["Valor Contrato ($)"], errors='coerce').fillna(0.0)
        mrr_total = df_f_temp["Valor_Num"].sum()
        cobrado_total = df_f_temp[df_f_temp["Estado Pago"] == "Pagado"]["Valor_Num"].sum()
        por_cobrar_df = df_f_temp[df_f_temp["Estado Pago"].isin(["Pendiente", "Abono / Pago Parcial"])]
        por_cobrar_total = por_cobrar_df["Valor_Num"].sum()
        facturas_pendientes = len(por_cobrar_df)

    # 3. METRICAS GLOBALES
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    col_m1.metric(label="💰 MRR Global (Total)", value=f"${mrr_total:,.0f} COP")
    col_m2.metric(label="✅ Cobrado + Abonos", value=f"${cobrado_total:,.0f} COP", delta="Liquidez")
    col_m3.metric(label="🚨 POR COBRAR", value=f"${por_cobrar_total:,.0f} COP", delta=f"{facturas_pendientes} Pendientes", delta_color="inverse")
    
    gasto_pauta_total = pd.to_numeric(df_ads["Gasto Actual ($)"], errors="coerce").fillna(0).sum() if not df_ads.empty else 0.0
    col_m4.metric(label="📈 Inversión Pauta (Ads)", value=f"${gasto_pauta_total:,.0f} COP", delta="Gasto de Clientes")

    st.markdown("---")
    
    # 4. TABS DE LA TORRE DE CONTROL
    tab_tc1, tab_tc2, tab_tc3 = st.tabs(["📊 Estadísticas de Producción", "💵 Control de Cobranza & Soportes", "🚨 Matriz de Alertas por Cliente"])

    with tab_tc1:
        st.subheader("📊 Embudo de Producción de Contenidos")
        st.caption("Conteo general del estado de las publicaciones para todos los clientes.")
        
        # Filtro de fechas en Parrilla para mostrar estadísticas reales
        df_parrilla["Fecha_DT"] = pd.to_datetime(df_parrilla["Fecha_Publicacion"], errors="coerce")
        mask_fechas = (df_parrilla["Fecha_DT"].dt.date >= fecha_inicio_filtro) & (df_parrilla["Fecha_DT"].dt.date <= fecha_fin_filtro)
        parrilla_filtrada = df_parrilla.loc[mask_fechas]
        
        if not parrilla_filtrada.empty:
            conteos_estado = parrilla_filtrada["Estado"].value_counts().to_dict()
            
            c_e1, c_e2, c_e3, c_e4, c_e5 = st.columns(5)
            c_e1.metric("💡 Ideas", conteos_estado.get("💡 Idea", 0))
            c_e2.metric("✍️ Guiones/Copys", conteos_estado.get("✍️ Guión / Copy", 0))
            c_e3.metric("🎨 Diseño/Edición", conteos_estado.get("🎨 Diseño / Edición", 0))
            c_e4.metric("✅ Programados", conteos_estado.get("✅ Programado", 0))
            c_e5.metric("🚀 Publicados", conteos_estado.get("🚀 Publicado / Pautado", 0))
        else:
            st.info(f"No hay publicaciones registradas en el rango seleccionado ({fecha_inicio_filtro} a {fecha_fin_filtro}).")

    with tab_tc2:
        st.subheader("💵 Matriz Financiera & Gestión de Contratos")
        st.caption("Consulta y edita los montos, estados de pago y enlaces a soportes o contratos.")

        # Prioridad 1: Mostrar la tabla de contratos si tiene datos
        if not df_contratos.empty:
            df_mostrar = df_contratos.copy()
            st.data_editor(
                df_mostrar,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_tc2_contratos"
            )
        # Prioridad 2: Mostrar finanzas antiguas como respaldo
        elif not df_finanzas.empty:
            st.data_editor(
                df_finanzas,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_tc2_finanzas"
            )
        else:
            st.info("No hay datos financieros ni contratos registrados. Registre un nuevo contrato en la pestaña CRM.")

    with tab_tc3:
        st.subheader("📋 Resumen Táctico Operativo")
        
        if not df_clientes.empty:
            for _, c_row in df_clientes.iterrows():
                nom_cli = c_row.get("Empresa", c_row.get("Nombre", ""))
                
                # --- 1. BUSCAR FINANZAS EN df_contratos PRIMERO ---
                monto_cli = 0.0
                estado_pago_cli = "Sin Registro"
                
                if not df_contratos.empty:
                    match_c = df_contratos[df_contratos["Cliente"] == nom_cli]
                    if not match_c.empty:
                        monto_cli = pd.to_numeric(match_c["Valor_Contrato"].iloc[-1], errors='coerce') or 0.0
                        estado_pago_cli = match_c["Estado_Pago"].iloc[-1]
                
                # Si no hay contrato, buscar en finanzas
                if monto_cli == 0 and estado_pago_cli == "Sin Registro" and not df_finanzas.empty:
                    match_f = df_finanzas[df_finanzas["Empresa"] == nom_cli]
                    if not match_f.empty:
                        monto_cli = pd.to_numeric(match_f["Valor Contrato ($)"].iloc[-1], errors='coerce') or 0.0
                        estado_pago_cli = match_f["Estado Pago"].iloc[-1]

                # --- 2. BUSCAR PRODUCCIÓN EN PARRILLA ---
                p_pendientes = 0
                p_listos = 0
                if not df_parrilla.empty:
                    match_p = df_parrilla[df_parrilla["Cliente"] == nom_cli]
                    if not match_p.empty:
                        p_pendientes = len(match_p[match_p["Estado"] != "🚀 Publicado"])
                        p_listos = len(match_p[match_p["Estado"] == "🚀 Publicado"])

                # --- 3. DIBUJAR DESPLEGABLE DEL CLIENTE ---
                ic_est = "🟢" if estado_pago_cli in ["Al Día", "Pagado"] else "🔴" if estado_pago_cli in ["Mora", "Pendiente"] else "🟡"
                
                with st.expander(f"🏢 **{nom_cli}** | Estado: {ic_est} {estado_pago_cli} | 📝 {p_pendientes} Posts pendientes"):
                    col_a1, col_a2 = st.columns(2)
                    
                    with col_a1:
                        st.markdown("💰 **Situación Financiera:**")
                        st.write(f"* **Contrato:** ${monto_cli:,.0f} COP")
                        st.write(f"* **Estado:** {estado_pago_cli}")
                        
                    with col_a2:
                        st.markdown("🎬 **Producción Total:**")
                        st.write(f"* **En Proceso (Cuello de Botella):** {p_pendientes}")
                        st.write(f"* **Listos / Publicados:** {p_listos}")
        else:
            st.info("No hay clientes registrados en la base de datos.")

# ==========================================
# 👥 DIRECTORIO DE CLIENTES (CRM)
# ==========================================
elif espacio_trabajo == "👥 Directorio de Clientes (CRM)":
    st.title("👥 Gestión CRM, Altas y Contratos")
    st.caption("Administra clientes, registra nuevos contratos y gestiona el historial comercial.")

    tab_crm1, tab_crm2, tab_crm3 = st.tabs([
        "📋 Directorio de Clientes", 
        "➕ Alta de Cliente", 
        "📝 Gestión y Historial de Contratos"
    ])

    with tab_crm1:
        st.subheader("Directorio General")
        st.markdown("Agregue o edite clientes directamente en la tabla.")
        df_clientes_editado = st.data_editor(
            df_clientes,
            num_rows="dynamic",
            use_container_width=True,
            key="ed_clientes_main"
        )
        if st.button("💾 Guardar Cambios en Clientes", type="primary"):
            guardar_datos("clientes.csv", df_clientes_editado)
            st.success("Directorio de clientes actualizado.")
            st.rerun()

    with tab_crm2:
        st.subheader("Registro de Nuevo Cliente")
        with st.form("form_nuevo_cliente"):
            nc_empresa = st.text_input("Nombre Comercial de la Empresa / Marca:")
            nc_contacto = st.text_input("Persona de Contacto Principal:")
            nc_telefono = st.text_input("WhatsApp con Indicativo País (ej: 573000000000):", value="573000000000")
            nc_nicho = st.text_input("Industria / Nicho de Mercado:")
            nc_valor = st.number_input("Valor Mensual del Contrato ($ COP):", min_value=0.0, value=1500000.0, step=100000.0)
            
            if st.form_submit_button("🚀 Dar de Alta Cliente"):
                if nc_empresa:
                    row_c = pd.DataFrame([[nc_contacto, nc_empresa, "Activo", nc_telefono, nc_nicho]], columns=df_clientes.columns)
                    df_clientes = pd.concat([df_clientes, row_c], ignore_index=True)
                    guardar_datos("clientes.csv", df_clientes)
                    
                    row_f = pd.DataFrame([[nc_empresa, nc_valor, str(datetime.date.today()), str(datetime.date.today() + datetime.timedelta(days=365)), "Pendiente"]], columns=df_finanzas.columns)
                    df_finanzas = pd.concat([df_finanzas, row_f], ignore_index=True)
                    guardar_datos("finanzas.csv", df_finanzas)
                    
                    st.success(f"¡Cliente {nc_empresa} dado de alta con éxito!")
                    st.rerun()

    with tab_crm3:
        st.subheader("📝 Historial de Contratos Comercial")
        
        lista_cli = df_clientes["Empresa"].unique().tolist() if not df_clientes.empty else []
        if lista_cli:
            cli_sel = st.selectbox("Selecciona Cliente para gestionar sus contratos:", lista_cli)
            df_contratos_cli = df_contratos[df_contratos["Cliente"] == cli_sel] if "df_contratos" in locals() or "df_contratos" in globals() else pd.DataFrame()
            
            if not df_contratos_cli.empty:
                st.markdown("**📁 Historial Activo (Edita o elimina filas directamente):**")
                df_c_edit = st.data_editor(df_contratos_cli, num_rows="dynamic", use_container_width=True, key="ed_contratos")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Guardar Cambios en Historial", type="primary"):
                    df_contratos = df_contratos[df_contratos["Cliente"] != cli_sel]
                    df_contratos = pd.concat([df_contratos, df_c_edit], ignore_index=True)
                    guardar_datos("contratos.csv", df_contratos)
                    st.success("Historial de contratos actualizado.")
                    st.rerun()
                
                csv_historial = df_c_edit.to_csv(index=False).encode('utf-8')
                col_btn2.download_button(
                    label="🖨️ Imprimir / Descargar Historial",
                    data=csv_historial,
                    file_name=f"Contratos_{cli_sel}.csv",
                    mime="text/csv"
                )
            else:
                st.info(f"No hay contratos registrados en el historial para {cli_sel}.")

            st.markdown("---")
            st.markdown("### ➕ Registrar Nuevo Contrato")
            with st.form("nuevo_contrato_form"):
                c_servicios = st.text_area("¿Qué se le va a hacer? (Desglose de Servicios):", placeholder="Ej: Gestión de 12 posts, pauta en Meta Ads...")
                c_redes = st.text_input("Redes Sociales / Canales a Trabajar:")
                
                # 💵 Campo de Valor agregado
                c_valor = st.number_input("Valor Mensual / Total del Contrato ($ COP):", min_value=0.0, value=1500000.0, step=100000.0)
                
                c_c1, c_c2 = st.columns(2)
                c_est_pago = c_c1.selectbox("Estado de Pago Inicial:", ["Al Día", "Pendiente", "Mora", "Anticipo Pagado"])
                c_est_cont = c_c2.selectbox("Estado del Contrato:", ["Sin Iniciar", "En Desarrollo", "En Espera", "Cumplió"])
                
                c_fecha_in = c_c1.date_input("Día de Inicio:")
                c_fecha_fin = c_c2.date_input("Día de Fin / Vencimiento:", datetime.date.today() + datetime.timedelta(days=30))
                
                c_acuerdos = st.text_area("Acuerdos / Compromisos:", placeholder="Tiempos de revisión, penalidades, etc.")
                c_notas = st.text_input("Notas Internas:")
                
                if st.form_submit_button("Añadir Contrato al Historial"):
                    nuevo_id = f"CONT-{len(df_contratos) + 1}" if 'df_contratos' in locals() else "CONT-1"
                    nuevo_c = pd.DataFrame([[
                        nuevo_id, 
                        cli_sel, 
                        c_servicios, 
                        c_redes, 
                        c_valor,
                        c_est_pago, 
                        str(c_fecha_in), 
                        str(c_fecha_fin), 
                        c_est_cont, 
                        c_notas, 
                        c_acuerdos
                    ]], columns=["ID_Contrato", "Cliente", "Servicios", "Redes", "Valor_Contrato", "Estado_Pago", "Fecha_Inicio", "Fecha_Fin", "Estado_Contrato", "Notas", "Acuerdos"])
                    
                    if 'df_contratos' in locals() or 'df_contratos' in globals():
                        df_contratos = pd.concat([df_contratos, nuevo_c], ignore_index=True)
                    else:
                        df_contratos = nuevo_c
                        
                    guardar_datos("contratos.csv", df_contratos)
                    st.success("¡Contrato registrado y anexado al historial exitosamente!")
                    st.rerun()

# ==========================================
# 1. GESTIÓN DE CLIENTES (OPERACIÓN INDIVIDUAL)
# ==========================================
elif espacio_trabajo == "🏢 Gestión de Clientes (Operación Individual)":
    empresas_validas = df_clientes[df_clientes["Empresa"].notna() & (df_clientes["Empresa"] != "")]
    lista_empresas = empresas_validas["Empresa"].unique().tolist() if not empresas_validas.empty else ["Sin Clientes"]
    
    if "cliente_activo" not in st.session_state or st.session_state["cliente_activo"] not in lista_empresas:
        st.session_state["cliente_activo"] = lista_empresas[0]

    st.session_state["cliente_activo"] = st.sidebar.selectbox("🏢 Cliente Activo:", lista_empresas, index=lista_empresas.index(st.session_state["cliente_activo"]))
    bloque_cliente = st.sidebar.radio("Sección Operativa:", ["📅 [Contenidos] Generador & Calendario", "📊 [Métricas] Ads & ROAS", "📦 [Brandkit] Accesos"])

    if bloque_cliente == "📅 [Contenidos] Generador & Calendario":
        st.title(f"📅 Producción de Contenidos: {st.session_state['cliente_activo']}")

        with st.expander("✨ Generar Nuevos Contenidos con IA", expanded=False):
            with st.form(f"form_gen_cli_{st.session_state['cliente_activo']}"):
                c1, c2, c3 = st.columns(3)
                f_in = c1.date_input("Fecha Inicio:", datetime.date.today())
                f_fi = c2.date_input("Fecha Fin:", datetime.date.today() + datetime.timedelta(days=14))
                num_posts_c = c3.number_input("Cantidad Posts:", min_value=1, max_value=20, value=4)
                
                col_g1, col_g2 = st.columns(2)
                redes_p = col_g1.multiselect("Redes Sociales:", st.session_state["redes_disponibles"], default=["Instagram"])
                pauta_p = col_g2.number_input("Presupuesto Pauta ($ COP):", min_value=0.0, value=200000.0, step=50000.0)
                enfoque_c = st.text_input("Objetivo:", placeholder="Ej: Vender productos de temporada.")

                btn_gen_cli = st.form_submit_button("✨ Generar Contenidos con IA", type="primary")

            if btn_gen_cli:
                with st.spinner("Generando estructura estricta..."):
                    prompt = f"""
                    Genera {num_posts_c} publicaciones para '{st.session_state['cliente_activo']}' (del {f_in} al {f_fi}) en {redes_p}. Enfoque: {enfoque_c}. Presupuesto ads: ${pauta_p} COP.
                    Devuelve SOLO una lista JSON de objetos con estas claves EXACTAS (no omitas ninguna):
                    "Red_Social", "Fecha_Publicacion", "Tipo_Contenido", "Nombre_Publicacion", "Detalle_Visual_Diseno", "Copy_Texto", "Hashtags", "Publico_Objetivo", "Tipo_Pauta", "Inversion_Pauta_COP", "Dias_Pauta_Recomendados"
                    """
                    res = consultar_gemini(prompt, modelo_seleccionado)
                    if res and hasattr(res, "text"):
                        posts = limpiar_json_gemini(res.text)
                        if posts:
                            df_new = pd.DataFrame(posts)
                            for col in columnas_parrilla:
                                if col not in df_new.columns:
                                    df_new[col] = ""
                            df_new = df_new.reindex(columns=columnas_parrilla, fill_value="")
                            df_new["Cliente"] = st.session_state["cliente_activo"]
                            df_new["Estado"] = "💡 Idea"
                            df_new["ID"] = [f"CLI-{len(df_parrilla)+i+1}" for i in range(len(df_new))]
                            
                            df_parrilla = pd.concat([df_parrilla, df_new], ignore_index=True)
                            guardar_datos("parrilla_contenidos.csv", df_parrilla)
                            st.success("¡Contenidos generados e integrados sin perder datos!")
                            st.rerun()
                        else:
                            st.error("Error al procesar el JSON generado por la IA. Por favor, reintente.")

        st.markdown("---")
        
        st.subheader("📊 Tabla y Calendario en Tiempo Real")
        df_cli_parrilla = df_parrilla[df_parrilla["Cliente"] == st.session_state["cliente_activo"]].copy()

        if not df_cli_parrilla.empty:
            tab_view1, tab_view2, tab_view3 = st.tabs(["📆 Calendario Visual", "✏️ Editor Masivo en Tabla", "📋 Tablero Kanban"])

            with tab_view1:
                fechas_unicas = df_cli_parrilla["Fecha_Publicacion"].unique()
                for fecha in fechas_unicas:
                    st.markdown(f"#### 📅 Fecha: `{fecha}`")
                    posts_dia = df_cli_parrilla[df_cli_parrilla["Fecha_Publicacion"] == fecha]
                    cols = st.columns(len(posts_dia)) if len(posts_dia) <= 3 else st.columns(3)
                    col_idx = 0
                    
                    for idx, row in posts_dia.iterrows():
                        with cols[col_idx]:
                            st.markdown(f"""
                            <div class="post-card-blue">
                                <span style="font-size: 11px; color: #64748b; font-weight: bold;">{row['Red_Social']} | {row['Tipo_Contenido']}</span>
                                <h5 style="margin-top: 4px; margin-bottom: 6px;">{row.get('Nombre_Publicacion', 'Sin Título')}</h5>
                                <span class="badge-status">{row['Estado']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander(f"✏️ Editar #{row['ID']}", expanded=False):
                                with st.form(f"form_edit_cli_{row['ID']}"):
                                    e_nombre = st.text_input("Título:", value=str(row.get('Nombre_Publicacion', '')))
                                    e_estado = st.selectbox("Estado:", ESTADOS_POSIBLES, index=ESTADOS_POSIBLES.index(row['Estado']) if row['Estado'] in ESTADOS_POSIBLES else 0)
                                    e_copy = st.text_area("Copy:", value=str(row.get('Copy_Texto', '')))
                                    if st.form_submit_button("💾 Guardar"):
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Nombre_Publicacion"] = e_nombre
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Estado"] = e_estado
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Copy_Texto"] = e_copy
                                        guardar_datos("parrilla_contenidos.csv", df_parrilla)
                                        st.rerun()
                        col_idx = (col_idx + 1) % 3

            with tab_view2:
                df_edited_c = st.data_editor(
                    df_cli_parrilla[columnas_parrilla],
                    column_config={"Estado": st.column_config.SelectboxColumn("Estado", options=ESTADOS_POSIBLES)},
                    num_rows="dynamic",
                    use_container_width=True, key="ed_mass_cli"
                )
                if st.button("💾 Guardar Cambios Masivos", type="primary"):
                    df_temp_c = df_parrilla[df_parrilla["Cliente"] != st.session_state["cliente_activo"]].copy()
                    df_parrilla = pd.concat([df_temp_c, df_edited_c], ignore_index=True)
                    guardar_datos("parrilla_contenidos.csv", df_parrilla)
                    st.success("¡Sincronizado!")
                    st.rerun()

            with tab_view3:
                c_k1, c_k2, c_k3, c_k4 = st.columns(4)
                for titulo, est, col in [("💡 Ideas", "💡 Idea", c_k1), ("✍️ Copys", "✍️ Guión / Copy", c_k2), ("🎨 Diseño", "🎨 Diseño / Edición", c_k3), ("🚀 Listos", "✅ Programado", c_k4)]:
                    with col:
                        st.markdown(f"**{titulo}**")
                        for idx, row in df_cli_parrilla[df_cli_parrilla["Estado"] == est].iterrows():
                            st.markdown(f'<div class="kanban-card"><b>{row.get("Nombre_Publicacion", "Post")}</b><br><small>{row["Red_Social"]}</small></div>', unsafe_allow_html=True)
        else:
            st.info("Sin publicaciones registradas. Genere contenido arriba.")

    elif bloque_cliente == "📊 [Métricas] Ads & ROAS":
        st.title("📊 Métricas de Pauta")
        
        df_ads_editado = st.data_editor(
            df_ads[df_ads["Cliente"] == st.session_state["cliente_activo"]],
            num_rows="dynamic",
            use_container_width=True
        )
        if st.button("💾 Guardar Datos de Pauta", type="primary"):
            df_temp_ads = df_ads[df_ads["Cliente"] != st.session_state["cliente_activo"]].copy()
            df_ads = pd.concat([df_temp_ads, df_ads_editado], ignore_index=True)
            guardar_datos("ads_analytics.csv", df_ads)
            st.success("Estadísticas de Pauta Actualizadas.")
            st.rerun()
        
    elif bloque_cliente == "📦 [Brandkit] Accesos":
        st.title("📦 Brandkit & Credenciales")
        st.dataframe(df_brandkits[df_brandkits["Cliente"] == st.session_state["cliente_activo"]], use_container_width=True)

# ==========================================
# 2. MÓDULO C: AUDITORÍA & BRIEFING EXPRESS
# ==========================================
elif espacio_trabajo == "🔍 Módulo C: Auditoría & Briefing Express":
    st.title("🔍 Módulo C: Auditoría Estratégica & Captación Express")
    st.caption("Herramienta dual: Diagnósticos veloces para prospección de clientes y auditorías estratégicas profundas respaldadas por IA.")

    # --- DEFINICIÓN DE COLUMNAS ESTÁNDAR ---
    cols_esperadas = [
        "Cliente", "Sector", "Tipo_Auditoria", "Objetivos", 
        "Audiencia", "Competidores", "URL_Competidor", 
        "Canal_Reach", "Tono", "Presupuesto", "Resumen_Diagnostico", "Fecha"
    ]

    # --- CARGA Y PERSISTENCIA DE DATOS EN SESSION STATE ---
    if "df_briefings" not in st.session_state or st.session_state["df_briefings"] is None:
        if os.path.exists("briefings.csv"):
            try:
                st.session_state["df_briefings"] = pd.read_csv("briefings.csv")
            except Exception:
                st.session_state["df_briefings"] = pd.DataFrame(columns=cols_esperadas)
        else:
            st.session_state["df_briefings"] = pd.DataFrame(columns=cols_esperadas)

    # Garantizar que todas las columnas existan y no haya valores nulos destructivos
    for col in cols_esperadas:
        if col not in st.session_state["df_briefings"].columns:
            st.session_state["df_briefings"][col] = "Sin datos"
    
    st.session_state["df_briefings"] = st.session_state["df_briefings"].fillna("Sin datos")

    tab_aud1, tab_aud2, tab_aud3 = st.tabs([
        "⚡ Auditoría Express (Prospectos / Leads)",
        "🎯 Auditoría Estratégica & Briefing (Clientes)",
        "📂 Historial, Edición & Registros"
    ])

    # ----------------------------------------------------
    # TAB 1: AUDITORÍA EXPRESS (CAPTACIÓN DE PROSPECTOS)
    # ----------------------------------------------------
    with tab_aud1:
        st.subheader("⚡ Auditoría Express para Prospectos (Lead Magnet)")
        st.info("Analiza el estado actual de un prospecto que aún no es cliente para descubrir fallas clave, oportunidades de mejora y generar una propuesta irrenunciable.")

        with st.form("form_auditoria_express"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                prospecto_nombre = st.text_input("🏢 Nombre de la Marca / Prospecto:", placeholder="Ej: Café Gourmet D'Origen")
                prospecto_nicho = st.text_input("🎯 Nicho / Industria:", placeholder="Ej: Gastronomía, Moda, Software B2B...")
                prospecto_ig = st.text_input("📸 Instagram / TikTok / Web:", placeholder="@marca_ejemplo")
                prospecto_objetivo = st.text_input("💡 Objetivo para Captarlo:", placeholder="Ej: Ofrecerle gestión integral de contenidos y pauta meta")

            with col_e2:
                prospecto_competidores = st.text_input("⚔️ Competidores Directos:", placeholder="Ej: MarcaX, MarcaY")
                prospecto_url_comp = st.text_input("🔗 URL Competidor / Referencia:", placeholder="https://instagram.com/competidor")
                prospecto_problemas = st.text_area(
                    "🚨 Fallas Visibles / Puntos Débiles Observados:",
                    placeholder="Ej: Publican sin constancia, portadas desordenadas, sin estrategia de Reels...",
                    height=100
                )

            btn_generar_express = st.form_submit_button("🚀 Generar Auditoría Express con IA")

        if btn_generar_express:
            if not prospecto_nombre:
                st.warning("⚠️ Por favor ingresa al menos el nombre de la marca o prospecto.")
            else:
                with st.spinner("🤖 Analizando marca y estructurando diagnóstico de captación..."):
                    prompt_express = f"""
                    Actúa como un Director Estratégico de Marketing Digital de la Agencia Vyntara.
                    Genera un informe de Auditoría Express de Captación para el siguiente prospecto:

                    * **Nombre del Prospecto:** {prospecto_nombre}
                    * **Nicho/Industria:** {prospecto_nicho}
                    * **Canal/Red Social:** {prospecto_ig}
                    * **Competidores Identificados:** {prospecto_competidores} ({prospecto_url_comp})
                    * **Problemas/Fallas Detectadas:** {prospecto_problemas}
                    * **Objetivo Comercial:** {prospecto_objetivo}

                    Estructura la respuesta en formato Markdown:
                    ### 📊 DIAGNÓSTICO RÁPIDO: {prospecto_nombre.upper()}
                    ---
                    #### 🛑 1. Principales Cuellos de Botella Visibles
                    #### ⚔️ 2. Comparativa FRENTE a Competidores ({prospecto_competidores or 'Sector'})
                    #### 🚀 3. Oportunidades de Alto Impacto (Quick Wins)
                    #### 💡 4. Propuesta de Valor & Gancho de Cierre (Pitch Vyntara)
                    """

                    res = consultar_gemini(prompt_express)
                    if res and hasattr(res, "text"):
                        st.success("✅ ¡Auditoría Express Generada con Éxito!")
                        st.markdown(res.text)

                        # Preparar fila con TODOS los campos completos
                        texto_resumen = res.text[:300].replace("\n", " ") + "..."
                        nueva_fila = pd.DataFrame([{
                            "Cliente": prospecto_nombre,
                            "Sector": prospecto_nicho if prospecto_nicho else "Sin especificar",
                            "Tipo_Auditoria": "Express (Prospecto)",
                            "Objetivos": prospecto_objetivo if prospecto_objetivo else "Por definir",
                            "Audiencia": "Prospecto General",
                            "Competidores": prospecto_competidores if prospecto_competidores else "No especificado",
                            "URL_Competidor": prospecto_url_comp if prospecto_url_comp else "N/A",
                            "Canal_Reach": prospecto_ig if prospecto_ig else "N/A",
                            "Tono": "Comercial / Captación",
                            "Presupuesto": "Por cotizar",
                            "Resumen_Diagnostico": texto_resumen,
                            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d")
                        }])

                        # Actualizar Memoria de Sesión y guardar CSV
                        st.session_state["df_briefings"] = pd.concat([st.session_state["df_briefings"], nueva_fila], ignore_index=True)
                        st.session_state["df_briefings"].to_csv("briefings.csv", index=False)
                        st.success("💾 Auditoría guardada exitosamente en el historial.")

                        st.download_button(
                            label="📥 Descargar Auditoría (TXT)",
                            data=res.text,
                            file_name=f"Auditoria_Express_{prospecto_nombre.replace(' ', '_')}.txt",
                            mime="text/plain"
                        )

    # ----------------------------------------------------
    # TAB 2: AUDITORÍA ESTRATÉGICA Y BRIEFING PROFUNDO
    # ----------------------------------------------------
    with tab_aud2:
        st.subheader("🎯 Briefing y Auditoría Estratégica (Clientes Activos)")
        st.caption("Crea o actualiza la radiografía estratégica completa de un cliente de la agencia.")

        cliente_sel = "Cliente General"
        if not df_clientes.empty:
            lista_cli = df_clientes["Empresa"].tolist() if "Empresa" in df_clientes.columns else df_clientes["Nombre"].tolist()
            cliente_sel = st.selectbox("📌 Seleccionar Cliente para Briefing:", lista_cli)

        with st.form("form_briefing_profundo"):
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                b_propuesta = st.text_area("💎 Propuesta Única de Valor:", placeholder="¿Qué hace única a esta marca frente a sus competidores?")
                b_audiencia = st.text_area("👥 Público Objetivo / Buyer Persona:", placeholder="Demografía, dolores, deseos...")
                b_competencia = st.text_input("⚔️ Principales Competidores:", placeholder="Competidor A, Competidor B...")
                b_url_comp = st.text_input("🔗 URL Competidores:", placeholder="https://... / @competidores")

            with col_b2:
                b_pilares = st.text_area("🏛️ Pilares de Contenido:", placeholder="Ej: 40% Educativo, 30% Entretenimiento, 20% Venta...")
                b_tono = st.text_input("🎙️ Tono de Voz de la Marca:", placeholder="Ej: Cercano, Profesional, Disruptivo...")
                b_kpis = st.text_input("📈 KPIs Principales / Objetivos:", placeholder="Ej: Leads mensuales, Engagement Rate")

            btn_generar_estrategico = st.form_submit_button("🧠 Generar Plan Estratégico AI Profundo")

        if btn_generar_estrategico:
            with st.spinner("🧠 Diseñando matriz estratégica integral con IA..."):
                prompt_profundo = f"""
                Eres el Chief Strategy Officer de Agencia Vyntara. Crea un Plan Estratégico de Auditoría Profunda para '{cliente_sel}':
                * **Propuesta de Valor:** {b_propuesta}
                * **Audiencia Objetivo:** {b_audiencia}
                * **Competencia & URLs:** {b_competencia} ({b_url_comp})
                * **Pilares:** {b_pilares}
                * **Tono:** {b_tono}
                * **KPIs:** {b_kpis}

                Estructura:
                ### 🎯 MATRIZ ESTRATÉGICA INTEGRAL - {cliente_sel.upper()}
                ---
                1. **Análisis FODA Digital**
                2. **Estrategia Táctica por Pilar**
                3. **Plan de Acción (30 Días)**
                """

                res_prof = consultar_gemini(prompt_profundo)
                if res_prof and hasattr(res_prof, "text"):
                    st.markdown(res_prof.text)
                    
                    texto_resumen_prof = res_prof.text[:300].replace("\n", " ") + "..."
                    nueva_fila_prof = pd.DataFrame([{
                        "Cliente": cliente_sel,
                        "Sector": "Estratégico / Cliente Activo",
                        "Tipo_Auditoria": "Profunda (Cliente Activo)",
                        "Objetivos": b_kpis if b_kpis else "Alineación de marca",
                        "Audiencia": b_audiencia if b_audiencia else "Público Objetivo",
                        "Competidores": b_competencia if b_competencia else "No especificado",
                        "URL_Competidor": b_url_comp if b_url_comp else "N/A",
                        "Canal_Reach": "Multicanal",
                        "Tono": b_tono if b_tono else "Corporativo",
                        "Presupuesto": "Plan Activo",
                        "Resumen_Diagnostico": texto_resumen_prof,
                        "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d")
                    }])

                    # Actualizar memoria y guardar CSV
                    st.session_state["df_briefings"] = pd.concat([st.session_state["df_briefings"], nueva_fila_prof], ignore_index=True)
                    st.session_state["df_briefings"].to_csv("briefings.csv", index=False)
                    st.success("💾 Plan estratégico registrado en el historial.")

    # ----------------------------------------------------
    # TAB 3: HISTORIAL, EDICIÓN Y GESTIÓN DE DATOS
    # ----------------------------------------------------
    with tab_aud3:
        st.subheader("📂 Base de Datos de Briefings y Auditorías")
        st.caption("Consulta, añade, edita o elimina registros de auditorías guardadas.")

        st.markdown("✏️ **Tabla interactiva (haz doble clic en cualquier casilla para editar o agregar filas al final):**")
        
        # Cargar datos protegidos desde st.session_state
        df_editado_briefings = st.data_editor(
            st.session_state["df_briefings"],
            use_container_width=True,
            num_rows="dynamic",
            key="editor_briefings_tabla_estable"
        )

        if st.button("💾 Guardar Cambios en la Base de Datos (CSV)"):
            try:
                # Sincronizar editor -> memoria de sesión -> archivo físico CSV
                st.session_state["df_briefings"] = df_editado_briefings
                df_editado_briefings.to_csv("briefings.csv", index=False)
                st.success("✅ ¡Base de datos de auditorías guardada y actualizada correctamente!")
            except Exception as e:
                st.error(f"❌ Error al guardar el archivo: {e}")

# ==========================================
# 3. AGENCIA VYNTARA (ESTRATEGIA IN-HOUSE)
# ==========================================
elif espacio_trabajo == "🔥 Agencia Vyntara (Estrategia In-House)":
    st.title("🔥 Agencia Vyntara | Estrategia In-House")
    st.caption("Central de operaciones, generación de contenidos propios y CRM de ventas de la agencia.")

    cliente_vyntara = "Vyntara Digital"

    tab_v_gen, tab_v_crm = st.tabs(["📅 Contenidos Vyntara", "🎯 CRM Leads (Ventas)"])
    
    with tab_v_gen:
        with st.expander("✨ Generar Nuevos Contenidos In-House con IA", expanded=False):
            with st.form("form_gen_vyntara"):
                c1, c2, c3 = st.columns(3)
                f_in = c1.date_input("Fecha Inicio:", datetime.date.today(), key="fi_vyn")
                f_fi = c2.date_input("Fecha Fin:", datetime.date.today() + datetime.timedelta(days=14), key="ff_vyn")
                num_posts_c = c3.number_input("Cantidad Posts:", min_value=1, max_value=20, value=4, key="np_vyn")
                
                col_g1, col_g2 = st.columns(2)
                redes_p = col_g1.multiselect("Redes Sociales:", st.session_state["redes_disponibles"], default=["Instagram", "LinkedIn"], key="rs_vyn")
                pauta_p = col_g2.number_input("Presupuesto Pauta ($ COP):", min_value=0.0, value=0.0, step=50000.0, key="pp_vyn")
                enfoque_c = st.text_input("Objetivo / Enfoque:", placeholder="Ej: Captar clientes B2B para servicios de marketing digital.", key="enf_vyn")

                btn_gen_vyn = st.form_submit_button("✨ Generar Contenidos Vyntara", type="primary")

            if btn_gen_vyn:
                with st.spinner("Diseñando estrategia in-house de Vyntara..."):
                    prompt = f"""
                    Genera {num_posts_c} publicaciones para la agencia de marketing digital '{cliente_vyntara}' (del {f_in} al {f_fi}) en {redes_p}. Enfoque: {enfoque_c}. Presupuesto ads: ${pauta_p} COP.
                    Devuelve SOLO una lista JSON de objetos con estas claves EXACTAS:
                    "Red_Social", "Fecha_Publicacion", "Tipo_Contenido", "Nombre_Publicacion", "Detalle_Visual_Diseno", "Copy_Texto", "Hashtags", "Publico_Objetivo", "Tipo_Pauta", "Inversion_Pauta_COP", "Dias_Pauta_Recomendados"
                    """
                    res = consultar_gemini(prompt, modelo_seleccionado)
                    if res and hasattr(res, "text"):
                        posts = limpiar_json_gemini(res.text)
                        if posts:
                            df_new = pd.DataFrame(posts)
                            for col in columnas_parrilla:
                                if col not in df_new.columns:
                                    df_new[col] = ""
                            df_new = df_new.reindex(columns=columnas_parrilla, fill_value="")
                            df_new["Cliente"] = cliente_vyntara
                            df_new["Estado"] = "💡 Idea"
                            df_new["ID"] = [f"VYN-{len(df_parrilla)+i+1}" for i in range(len(df_new))]
                            
                            df_parrilla = pd.concat([df_parrilla, df_new], ignore_index=True)
                            guardar_datos("parrilla_contenidos.csv", df_parrilla)
                            st.success("¡Estrategia de Vyntara generada con éxito!")
                            st.rerun()
                        else:
                            st.error("Error al procesar el JSON generado por la IA. Por favor, reintente.")

        st.markdown("---")
        st.subheader("📊 Parrilla In-House Vyntara")
        df_v_parrilla = df_parrilla[df_parrilla["Cliente"] == cliente_vyntara].copy()
        
        if not df_v_parrilla.empty:
            tab_v_cal, tab_v_edit, tab_v_kan = st.tabs(["📆 Calendario Visual", "✏️ Editor Masivo en Tabla", "📋 Tablero Kanban"])
            
            with tab_v_cal:
                fechas_unicas = df_v_parrilla["Fecha_Publicacion"].unique()
                for fecha in fechas_unicas:
                    st.markdown(f"#### 📅 Fecha: `{fecha}`")
                    posts_dia = df_v_parrilla[df_v_parrilla["Fecha_Publicacion"] == fecha]
                    cols = st.columns(len(posts_dia)) if len(posts_dia) <= 3 else st.columns(3)
                    col_idx = 0
                    
                    for idx, row in posts_dia.iterrows():
                        with cols[col_idx]:
                            st.markdown(f"""
                            <div class="post-card-indigo">
                                <span style="font-size: 11px; color: #64748b; font-weight: bold;">{row['Red_Social']} | {row['Tipo_Contenido']}</span>
                                <h5 style="margin-top: 4px; margin-bottom: 6px;">{row.get('Nombre_Publicacion', 'Sin Título')}</h5>
                                <span class="badge-status">{row['Estado']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander(f"✏️ Editar #{row['ID']}", expanded=False):
                                with st.form(f"form_edit_vyn_{row['ID']}"):
                                    e_nombre = st.text_input("Título:", value=str(row.get('Nombre_Publicacion', '')))
                                    e_estado = st.selectbox("Estado:", ESTADOS_POSIBLES, index=ESTADOS_POSIBLES.index(row['Estado']) if row['Estado'] in ESTADOS_POSIBLES else 0)
                                    e_copy = st.text_area("Copy:", value=str(row.get('Copy_Texto', '')))
                                    if st.form_submit_button("💾 Guardar"):
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Nombre_Publicacion"] = e_nombre
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Estado"] = e_estado
                                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Copy_Texto"] = e_copy
                                        guardar_datos("parrilla_contenidos.csv", df_parrilla)
                                        st.rerun()
                        col_idx = (col_idx + 1) % 3

            with tab_v_edit:
                df_edited_v = st.data_editor(
                    df_v_parrilla[columnas_parrilla],
                    column_config={"Estado": st.column_config.SelectboxColumn("Estado", options=ESTADOS_POSIBLES)},
                    num_rows="dynamic",
                    use_container_width=True, key="ed_mass_vyn"
                )
                if st.button("💾 Guardar Cambios Masivos Vyntara", type="primary"):
                    df_temp_v = df_parrilla[df_parrilla["Cliente"] != cliente_vyntara].copy()
                    df_parrilla = pd.concat([df_temp_v, df_edited_v], ignore_index=True)
                    guardar_datos("parrilla_contenidos.csv", df_parrilla)
                    st.success("¡Parrilla Vyntara Sincronizada!")
                    st.rerun()

            with tab_v_kan:
                c_k1, c_k2, c_k3, c_k4 = st.columns(4)
                for titulo, est, col in [("💡 Ideas", "💡 Idea", c_k1), ("✍️ Copys", "✍️ Guión / Copy", c_k2), ("🎨 Diseño", "🎨 Diseño / Edición", c_k3), ("🚀 Listos", "✅ Programado", c_k4)]:
                    with col:
                        st.markdown(f"**{titulo}**")
                        for idx, row in df_v_parrilla[df_v_parrilla["Estado"] == est].iterrows():
                            st.markdown(f'<div class="kanban-card"><b>{row.get("Nombre_Publicacion", "Post")}</b><br><small>{row["Red_Social"]}</small></div>', unsafe_allow_html=True)
        else:
            st.info("No hay publicaciones in-house registradas. Utilice el generador superior.")
            
    with tab_v_crm:
        st.subheader("🎯 CRM & Gestión de Leads")
        st.dataframe(df_leads_vyntara, use_container_width=True)

# ==========================================
# 4. COTIZADOR Y GENERADOR PDF
# ==========================================
elif espacio_trabajo == "📄 Cotizador & Generador de PDF":
    st.title("📄 Cotizador Rápido PDF")
    with st.form("form_cotizador"):
        c1, c2 = st.columns(2)
        emp = c1.text_input("Empresa:", "Empresa Ejemplo")
        atn = c1.text_input("Atención a:", "Juan Pérez")
        tipo = c2.selectbox("Servicio:", ["Gestión Redes & Ads", "Auditoría Digital"])
        costo = c2.number_input("Costo Total (COP):", min_value=100000.0, value=1500000.0)
        btn = st.form_submit_button("🧮 Generar PDF", type="primary")

    if btn:
        pdf_bytes = generar_pdf_cotizacion(emp, atn, tipo, [f"Servicio Integral: {tipo}"], costo, "Términos estándar.")
        st.download_button("📄 Descargar PDF", data=pdf_bytes, file_name=f"Cotizacion_{emp}.pdf", mime="application/pdf")

# ==========================================
# 5. PORTAL CLIENTE
# ==========================================
elif espacio_trabajo == "👁️ Portal Cliente (Aprobación Externa)":
    st.title("👁️ Portal del Cliente")

    # Cargar lista de clientes registrados
    lista_clientes = []
    if "df_clientes" in locals() and not df_clientes.empty:
        lista_clientes = df_clientes["Empresa"].tolist() if "Empresa" in df_clientes.columns else df_clientes["Nombre"].tolist()

    if not lista_clientes:
        st.info("ℹ️ No hay clientes activos registrados en el CRM para mostrar en el portal.")
    else:
        # --- CONTROL DE ACCESO PRIVADO POR URL ---
        params = st.query_params
        cliente_url = params.get("cliente", None)

        # Si el cliente entra mediante su link único (?cliente=Nombre)
        if cliente_url and cliente_url in lista_clientes:
            cliente_sel = cliente_url
            st.success(f"🏢 Bienvenido/a al Portal de **{cliente_sel}**")
            st.caption("Panel de control exclusivo para revisión de contenidos, reportes y estados de cuenta.")
        else:
            # Modo Administración (Vista para la Agencia)
            st.subheader("⚙️ Panel de Administración del Portal")
            col_admin1, col_admin2 = st.columns([2, 1])
            
            with col_admin1:
                cliente_sel = st.selectbox("📌 Selecciona un cliente para previsualizar su portal:", lista_clientes)
            
            with col_admin2:
                # 1. Preparar el nombre del cliente para la dirección web
                cliente_encode = cliente_sel.replace(" ", "%20")
                
                # 2. Tu URL real y oficial del sistema Vyntara OS
                url_base = "https://vyntara-os-alddkcpncvqdtpsww6qge.streamlit.app"
                
                # 3. Construcción del enlace privado
                link_cliente = f"{url_base}/?cliente={cliente_encode}"
                
                st.markdown("**🔗 Enlace Privado para enviar al cliente:**")
                st.code(link_cliente, language="text")
                st.caption("Copia este enlace y envíaselo directamente por WhatsApp o correo.")

        st.divider()

        # Pestañas de Navegación del Cliente
        tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs([
            "📅 Parrilla & Aprobación",
            "📊 Métricas & Analytics",
            "🔍 Auditorías & Estrategia",
            "💳 Estado de Cuenta"
        ])

        # ----------------------------------------------------
        # TAB 1: PARRILLA DE CONTENIDOS Y APROBACIÓN
        # ----------------------------------------------------
        with tab_p1:
            st.subheader("📅 Revisión y Aprobación de Publicaciones")
            st.caption("Aprueba las publicaciones o solicita ajustes directamente al equipo de la agencia.")

            df_parrilla = pd.DataFrame()
            if os.path.exists("parrilla_contenidos.csv"):
                try:
                    df_parrilla = pd.read_csv("parrilla_contenidos.csv")
                except Exception:
                    df_parrilla = pd.DataFrame()

            if not df_parrilla.empty and "Cliente" in df_parrilla.columns:
                parrilla_cliente = df_parrilla[df_parrilla["Cliente"] == cliente_sel]
            else:
                parrilla_cliente = pd.DataFrame()

            if parrilla_cliente.empty:
                st.warning(f"📌 No hay publicaciones registradas pendientes para **{cliente_sel}**.")
            else:
                for idx, row in parrilla_cliente.iterrows():
                    estado_actual = row.get("Estado", "En Revisión")
                    color_badge = "🔵" if "Revisión" in estado_actual else ("🟢" if "Aprobado" in estado_actual or "Programado" in estado_actual else "🟠")

                    with st.expander(f"{color_badge} Post #{idx+1} | {row.get('Red_Social', 'Red Social')} - {row.get('Fecha', 'Sin fecha')} [{estado_actual}]", expanded=("Revisión" in estado_actual)):
                        c_p1, c_p2 = st.columns([2, 1])
                        
                        with c_p1:
                            st.markdown(f"**🎯 Pilar de Contenido:** {row.get('Pilar', 'General')}")
                            st.markdown(f"**🎨 Formato:** {row.get('Formato', 'Post / Reel')}")
                            st.text_area("📝 Copy / Texto propuesta:", value=str(row.get("Copy", "")), height=120, disabled=True, key=f"copy_{idx}")
                            
                            if "Notas_Cliente" in row and str(row["Notas_Cliente"]) not in ["nan", "None", ""]:
                                st.info(f"💬 **Último comentario registrado:** {row['Notas_Cliente']}")

                        with c_p2:
                            st.markdown("### 🛠️ Acción de Aprobación")
                            
                            if st.button("✅ Aprobar Publicación", key=f"btn_app_{idx}", type="primary"):
                                df_parrilla.at[idx, "Estado"] = "✅ Aprobado / Programado"
                                df_parrilla.to_csv("parrilla_contenidos.csv", index=False)
                                st.success("🎉 ¡Publicación aprobada!")
                                st.rerun()

                            st.markdown("---")
                            
                            comentario_cliente = st.text_input("💬 Comentarios / Sugerencias:", key=f"input_obs_{idx}")
                            if st.button("💬 Solicitar Ajustes", key=f"btn_corr_{idx}"):
                                if comentario_cliente.strip():
                                    df_parrilla.at[idx, "Estado"] = "🟠 Cambios Solicitados"
                                    df_parrilla.at[idx, "Notas_Cliente"] = comentario_cliente.strip()
                                    df_parrilla.to_csv("parrilla_contenidos.csv", index=False)
                                    st.warning("📩 Sugerencias enviadas al equipo.")
                                    st.rerun()
                                else:
                                    st.error("Escribe un comentario antes de solicitar ajustes.")

        # ----------------------------------------------------
        # TAB 2: MÉTRICAS Y ANALYTICS (SOLO LECTURA)
        # ----------------------------------------------------
        with tab_p2:
            st.subheader("📊 Métricas de Rendimiento & Campañas")
            
            df_ads = pd.DataFrame()
            if os.path.exists("ads_analytics.csv"):
                try:
                    df_ads = pd.read_csv("ads_analytics.csv")
                except Exception:
                    df_ads = pd.DataFrame()

            if not df_ads.empty and "Cliente" in df_ads.columns:
                ads_cliente = df_ads[df_ads["Cliente"] == cliente_sel]
            else:
                ads_cliente = pd.DataFrame()

            if ads_cliente.empty:
                st.info("📈 No hay reportes de analítica registrados para esta marca actualmente.")
            else:
                st.dataframe(ads_cliente, use_container_width=True)

        # ----------------------------------------------------
        # TAB 3: STRATEGIC BRIEFING & AUDITORÍAS (SOLO LECTURA)
        # ----------------------------------------------------
        with tab_p3:
            st.subheader("🔍 Diagnóstico & Matriz Estratégica")

            if "df_briefings" in st.session_state and not st.session_state["df_briefings"].empty:
                briefs_cliente = st.session_state["df_briefings"][st.session_state["df_briefings"]["Cliente"] == cliente_sel]
                
                if briefs_cliente.empty:
                    st.info("📄 No se encontraron auditorías registradas para esta marca.")
                else:
                    for _, b_row in briefs_cliente.iterrows():
                        with st.expander(f"📌 Auditoría / Briefing - {b_row.get('Tipo_Auditoria', 'Estratégica')} ({b_row.get('Fecha', 'Fecha N/A')})"):
                            st.write(f"**Sector:** {b_row.get('Sector', 'N/A')}")
                            st.write(f"**Objetivos:** {b_row.get('Objetivos', 'N/A')}")
                            st.write(f"**Público Objetivo:** {b_row.get('Audiencia', 'N/A')}")
                            st.write(f"**Tono:** {b_row.get('Tono', 'N/A')}")
                            st.markdown("---")
                            st.markdown(f"**Diagnóstico:** {b_row.get('Resumen_Diagnostico', 'Sin detalles')}")
            else:
                st.info("📄 No hay base de datos de briefing disponible.")

        # ----------------------------------------------------
        # TAB 4: ESTADO DE CUENTA (SOLO LECTURA)
        # ----------------------------------------------------
        with tab_p4:
            st.subheader("💳 Estado de Cuenta & Facturación")

            df_fin = pd.DataFrame()
            if os.path.exists("finanzas.csv"):
                try:
                    df_fin = pd.read_csv("finanzas.csv")
                except Exception:
                    df_fin = pd.DataFrame()

            if not df_fin.empty and "Cliente" in df_fin.columns:
                fin_cliente = df_fin[df_fin["Cliente"] == cliente_sel]
            else:
                fin_cliente = pd.DataFrame()

            if fin_cliente.empty:
                st.info("💵 No hay cobros o facturas registradas actualmente para este cliente.")
            else:
                if "Monto" in fin_cliente.columns:
                    total_facturado = fin_cliente["Monto"].sum() if not fin_cliente["Monto"].empty else 0
                    st.metric("Monto Total Servicios", f"${total_facturado:,.2f}")

                st.markdown("### 📋 Historial de Pagos y Facturas")
                st.dataframe(fin_cliente, use_container_width=True)
                
# ==========================================
# 6. CONFIGURACIÓN Y BACKUPS
# ==========================================
elif espacio_trabajo == "⚙️ Configuración Global & Respaldos":
    st.title("⚙️ Sistema & Backups")

    # --- SECCIÓN 1: GUARDA Y CONEXIÓN DE API KEY ---
    st.subheader("🔑 Configuración de Clave API Gemini")
    st.caption("Ingresa tu clave de Google AI Studio. Se guardará de forma segura en tu equipo.")

    key_actual = st.session_state.get("api_key_activa", "")

    nueva_key = st.text_input(
        "Clave API Gemini:",
        value=key_actual,
        type="password",
        help="Pega aquí tu clave API que empieza por AIzaSy..."
    )

    if st.button("💾 Guardar y Conectar API Key"):
        if nueva_key.strip():
            st.session_state["api_key_activa"] = nueva_key.strip()
            # Guardar físicamente en el disco duro
            with open("api_key.txt", "w") as f:
                f.write(nueva_key.strip())
            st.success("✅ ¡API Key guardada y conectada con éxito!")
            st.rerun()  # Recarga la página para activar el indicador verde inmediatamente
        else:
            st.warning("⚠️ La clave API no puede estar vacía.")

    st.divider()

    # --- SECCIÓN 2: GENERACIÓN DE RESPALDOS ---
    st.subheader("📦 Respaldos de Información")
    st.caption("Genera una copia de seguridad comprimida de todas las bases de datos del sistema.")

    if st.button("📦 Generar Backup ZIP", type="primary"):
        buffer = io.BytesIO()
        archivos_sistema = [
            "clientes.csv", "finanzas.csv", "parrilla_contenidos.csv", 
            "ads_analytics.csv", "briefings.csv", "api_key.txt"
        ]
        
        with zipfile.ZipFile(buffer, "w") as zf:
            for arc in archivos_sistema:
                ruta = os.path.join(directorio_actual, arc)
                if os.path.exists(ruta):
                    zf.write(ruta, arcname=arc)

        st.download_button(
            label="💾 Descargar Sistema Completo (ZIP)",
            data=buffer.getvalue(),
            file_name=f"Backup_Vyntara_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip"
        )