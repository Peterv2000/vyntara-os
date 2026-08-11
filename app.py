import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image
from duckduckgo_search import DDGS
import datetime
import json
from fpdf import FPDF
import urllib.parse
import zipfile
import io

# ==========================================
# ⚙️ CONFIGURACIÓN Y ESTILOS - VYNTARA
# ==========================================
API_KEY_DEFAULT = st.secrets.get("AQ.Ab8RN6LmCZhuxI6o37aBi4oMhQ2jZK74mBUrZn68OFtoMuoKog","") 
NOMBRE_LOGO = "logo.jpg" 

directorio_actual = os.getcwd()
ruta_logo = os.path.join(directorio_actual, NOMBRE_LOGO)

st.set_page_config(page_title="Vyntara OS | Agency Management System", page_icon="✨", layout="wide")

st.markdown("""
    <head><meta name="google" content="notranslate"></head>
    <style>
        .stApp { translate: no; background-color: #f8fafc; color: #0f172a; }
        div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
        .stButton>button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%); color: #ffffff; border-radius: 8px; border: none; font-weight: 600; }
        h1, h2, h3 { color: #0f172a !important; font-family: 'Inter', sans-serif; }
        .kanban-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
        .client-preview-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .alert-box-red { background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; color: #991b1b; font-weight: 500; }
        .alert-box-green { background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; color: #166534; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# Variables de Sesión
if "api_key_activa" not in st.session_state:
    st.session_state["api_key_activa"] = API_KEY_DEFAULT
if "redes_disponibles" not in st.session_state:
    st.session_state["redes_disponibles"] = ["Instagram", "TikTok", "Facebook", "LinkedIn", "YouTube", "Threads", "X/Twitter"]

# Funciones de Soporte
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
    return df

def guardar_datos(archivo, df):
    df.to_csv(os.path.join(directorio_actual, archivo), index=False)

def consultar_gemini(prompt, modelo_nombre, imagen=None):
    genai.configure(api_key=st.session_state["api_key_activa"])
    model = genai.GenerativeModel(modelo_nombre)
    return model.generate_content([prompt, imagen]) if imagen else model.generate_content(prompt)

def buscar_en_internet(query, max_resultados=5):
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=max_resultados))
            return "".join([f"Título: {r['title']}\nResumen: {r['body']}\n\n" for r in resultados])
    except Exception as e:
        return f"Error en búsqueda web: {e}"

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
    pdf.cell(0, 5, sanitizar_texto_pdf("Vyntara Digital | Transformando Marcas con Estrategia e Inteligencia Artificial"), 0, 1, "C")

    return pdf.output(dest='S').encode('latin-1', 'ignore')

def crear_link_whatsapp(numero, mensaje):
    num_limpio = "".join(filter(str.isdigit, str(numero)))
    msg_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{num_limpio}?text={msg_encoded}"

# Cargar Bases de Datos
archivos_csv = ["clientes.csv", "finanzas.csv", "parrilla_contenidos.csv", "ads_analytics.csv", "sla_entregables.csv", "vyntara_inhouse.csv", "brandkits.csv", "vyntara_leads.csv"]

df_clientes = cargar_datos("clientes.csv", ["Nombre", "Empresa", "Redes a Manejar", "Estado", "Telefono", "Nicho"])
df_finanzas = cargar_datos("finanzas.csv", ["Empresa", "Valor Contrato ($)", "Fecha Inicio", "Fecha Fin", "Estado Pago"])
columnas_parrilla = ["ID", "Cliente", "Red_Social", "Fecha_Publicacion", "Tipo_Contenido", "Detalle_Visual_Diseno", "Copy_Texto", "Hashtags", "Publico_Objetivo", "Tipo_Pauta", "Inversion_Pauta_COP", "Estado"]
df_parrilla = cargar_datos("parrilla_contenidos.csv", columnas_parrilla)
df_ads = cargar_datos("ads_analytics.csv", ["Cliente", "Campaña", "Plataforma", "Presupuesto Asignado ($)", "Gasto Actual ($)", "Impresiones", "Clics", "Estado"])
df_entregables = cargar_datos("sla_entregables.csv", ["Cliente", "Entregable", "Fecha_Limite", "Estado", "SLA_Cumplido"])
df_vyntara = cargar_datos("vyntara_inhouse.csv", ["Red_Social", "Usuario_Handle", "Seguidores", "Engagement_Rate", "Leads_Generados", "Experimento_Sandbox"])
df_brandkits = cargar_datos("brandkits.csv", ["Cliente", "Colores_HEX", "Tipografias", "Link_Drive_Canva", "Credenciales_Redes", "Notas_Marca"])
df_leads_vyntara = cargar_datos("vyntara_leads.csv", ["Empresa_Prospecto", "Contacto", "Telefono", "Valor_Cotizado", "Estado_Pipeline", "Notas"])

# ==========================================
# 🧭 NAVEGACIÓN PRINCIPAL
# ==========================================
st.sidebar.title("✨ Vyntara OS")

if os.path.exists(ruta_logo):
    try:
        st.sidebar.image(Image.open(ruta_logo), use_container_width=True)
    except:
        pass

modelo_seleccionado = None
if st.session_state.get("api_key_activa"):
    api_key_limpia = str(st.session_state["api_key_activa"]).strip()
    try:
        genai.configure(api_key=api_key_limpia)
        
        # Intentar listar los modelos, si falla se usan los modelos por defecto
        try:
            modelos = [m.name for m in genai.list_models() if 'gemini' in m.name and 'generateContent' in m.supported_generation_methods]
        except Exception:
            modelos = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-2.0-flash"]
            
        if not modelos:
            modelos = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]
            
        modelo_seleccionado = st.sidebar.selectbox("🤖 Modelo IA Activo", modelos)
        st.sidebar.success("✅ Conectado a Gemini")
    except Exception as e:
        st.sidebar.error(f"❌ Error de conexión: {e}")

st.sidebar.markdown("---")

espacio_trabajo = st.sidebar.radio(
    "📌 Módulos del Sistema:",
    [
        "🎛️ Torre de Control General (Finanzas & Alertas)",
        "🏢 Gestión de Clientes (Operación Individual)",
        "🔥 Agencia Vyntara (Estrategia In-House)",
        "📄 Cotizador & Generador de PDF (Ventas)",
        "👁️ Portal Cliente (Aprobación Externa)",
        "⚙️ Configuración Global & Copias de Seguridad"
    ]
)

st.sidebar.markdown("---")

# ==========================================
# 0. NUEVO MÓDULO: TORRE DE CONTROL GENERAL (FINANZAS Y ALERTAS)
# ==========================================
if espacio_trabajo == "🎛️ Torre de Control General (Finanzas & Alertas)":
    st.title("🎛️ Torre de Control General | Visión Global de la Agencia")
    st.caption("Central de monitoreo financiero, alertas operativas y estado de publicaciones de TODOS los clientes en tiempo real.")

    # Cálculos globales
    if not df_finanzas.empty:
        df_finanzas["Valor_Num"] = pd.to_numeric(df_finanzas["Valor Contrato ($)"], errors="coerce").fillna(0)
        monto_pendiente = df_finanzas[df_finanzas["Estado Pago"] == "Pendiente"]["Valor_Num"].sum()
        monto_cobrado = df_finanzas[df_finanzas["Estado Pago"] == "Pagado"]["Valor_Num"].sum()
        mrr_total = df_finanzas["Valor_Num"].sum()
    else:
        monto_pendiente = monto_cobrado = mrr_total = 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("💰 MRR (Facturación Mensual Recurrente)", f"${mrr_total:,.0f} COP")
    col_m2.metric("✅ Monto Total Cobrado / Recaudado", f"${monto_cobrado:,.0f} COP")
    col_m3.metric("🚨 TOTAL POR COBRAR (PENDIENTE)", f"${monto_pendiente:,.0f} COP", delta=f"{len(df_finanzas[df_finanzas['Estado Pago'] == 'Pendiente'])} Facturas", delta_color="inverse")

    st.markdown("---")

    tab_tc1, tab_tc2 = st.tabs([
        "🚨 Matriz de Alertas por Cliente (Pagos + Parrilla + SLA)", 
        "💵 Consolidador Financiero & Control de Cobranza"
    ])

    with tab_tc1:
        st.subheader("📋 Resumen Táctico de Clientes")
        st.caption("Verifica el estado de cartera, contenidos pendientes de aprobación y entregables de cada cuenta.")
        
        if not df_clientes.empty:
            for idx, cli in df_clientes.iterrows():
                nombre_emp = cli["Empresa"]
                tel_cli = cli.get("Telefono", "573000000000")
                
                # Datos financieros
                fin_cli = df_finanzas[df_finanzas["Empresa"] == nombre_emp]
                est_pago = fin_cli["Estado Pago"].values[0] if not fin_cli.empty else "Sin Registro"
                monto_cli = fin_cli["Valor Contrato ($)"].values[0] if not fin_cli.empty else 0
                
                # Datos de parrilla
                parrilla_cli = df_parrilla[df_parrilla["Cliente"] == nombre_emp]
                posts_pendientes = len(parrilla_cli[parrilla_cli["Estado"].isin(["💡 Idea", "✍️ Guión / Copy", "🎨 Diseño / Edición"])])
                posts_listos = len(parrilla_cli[parrilla_cli["Estado"] == "✅ Programado"])
                
                # Datos SLA
                sla_cli = df_entregables[df_entregables["Cliente"] == nombre_emp]
                sla_pendientes = len(sla_cli[sla_cli["Estado"] != "Completado"]) if not sla_cli.empty else 0

                # Badge visual
                es_moroso = (est_pago == "Pendiente")
                badge_pago = "🔴 COBRO PENDIENTE" if es_moroso else "🟢 PAGO AL DÍA"
                
                with st.expander(f"🏢 **{nombre_emp}** | Estado: {badge_pago} | 📝 {posts_pendientes} Posts pendientes por aprobar", expanded=es_moroso):
                    c_info1, c_info2, c_info3 = st.columns(3)
                    
                    with c_info1:
                        st.markdown("**💰 Situación Financiera:**")
                        st.write(f"- Contrato Mensual: **${monto_cli:,.0f} COP**")
                        st.write(f"- Estado de Pago: **{est_pago}**")
                        if es_moroso:
                            msg_cobro = f"Hola {cli.get('Nombre', '')}! Te escribimos de Vyntara Digital para recordarte la gestión del pago mensual (${monto_cli:,.0f} COP) para {nombre_emp}. Quedamos atentos al comprobante. ¡Gracias!"
                            link_wa_cobro = crear_link_whatsapp(tel_cli, msg_cobro)
                            st.markdown(f'[![Cobrar por WA](https://img.shields.io/badge/Enviar_Recordatorio_Cobro-WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({link_wa_cobro})')

                    with c_info2:
                        st.markdown("**📅 Estado de Publicaciones:**")
                        st.write(f"- Posts en Borrador / Revisión: **{posts_pendientes}**")
                        st.write(f"- Posts Aprobados / Listos: **{posts_listos}**")
                        if posts_pendientes > 0:
                            msg_p = f"Hola! Te escribimos de Vyntara Digital. Tienes {posts_pendientes} publicaciones listas para revisar en tu portal de aprobación para {nombre_emp}."
                            link_p_wa = crear_link_whatsapp(tel_cli, msg_p)
                            st.markdown(f'[![Notificar Parrilla](https://img.shields.io/badge/Aviso_Parrilla-WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({link_p_wa})')

                    with c_info3:
                        st.markdown("**📦 Entregables & SLA:**")
                        st.write(f"- Entregables SLA Pendientes: **{sla_pendientes}**")
                        st.write(f"- Contacto: **{cli.get('Nombre', 'N/A')}**")
                        st.write(f"- Nicho: **{cli.get('Nicho', 'N/A')}**")
        else:
            st.info("No hay clientes registrados en el sistema.")

    with tab_tc2:
        st.subheader("💵 Matriz Financiera Completa de la Agencia")
        st.caption("Edita directamente los valores o estados de pago de tus clientes.")
        if not df_finanzas.empty:
            df_fin_edit = st.data_editor(df_finanzas, num_rows="dynamic", use_container_width=True, key="ed_fin_tc")
            if st.button("💾 Guardar Cambios Financieros", type="primary"):
                guardar_datos("finanzas.csv", df_fin_edit)
                st.success("Tabla financiera guardada correctamente.")
                st.rerun()

# ==========================================
# 1. MÓDULO: GESTIÓN DE CLIENTES
# ==========================================
elif espacio_trabajo == "🏢 Gestión de Clientes (Operación Individual)":
    lista_empresas = df_clientes["Empresa"].unique().tolist() if not df_clientes.empty else ["Sin Clientes"]
    if "cliente_activo" not in st.session_state or st.session_state["cliente_activo"] not in lista_empresas:
        st.session_state["cliente_activo"] = lista_empresas[0]

    cliente_global = st.sidebar.selectbox("🏢 Cliente Activo:", lista_empresas, index=lista_empresas.index(st.session_state["cliente_activo"]))
    st.session_state["cliente_activo"] = cliente_global

    bloque_cliente = st.sidebar.radio("Sección Cliente:", [
        "📊 [Métricas] Performance Ads & ROAS Proyectado",
        "📅 [Contenidos] Generador IA, Visual Studio, Kanban & Guiones",
        "📦 [Brandkit] Guía de Estilo & Vault de Accesos",
        "👥 [CRM & SLA] Alta de Cliente, Contrato y Entregables"
    ])

    if bloque_cliente == "📊 [Métricas] Performance Ads & ROAS Proyectado":
        st.title(f"📊 Métricas & Proyecciones: {st.session_state['cliente_activo']}")
        st.caption("Analiza las campañas activas de publicidad, proyecta el retorno de inversión y consulta tendencias de mercado.")
        
        tab_d1, tab_d2, tab_d3 = st.tabs([
            "📈 Campañas de Publicidad (Ads Analytics)", 
            "🧮 Calculadora de Retorno (Simulador ROAS)", 
            "📡 Radar AI de Mercado & Competencia"
        ])
        
        with tab_d1:
            st.subheader("Rendimiento de Anuncios Activos")
            c1, c2, c3 = st.columns(3)
            c1.metric("Posts Totales", len(df_parrilla[df_parrilla["Cliente"] == st.session_state["cliente_activo"]]))
            c2.metric("Inversión Ads Registrada", f"${df_ads[df_ads['Cliente'] == st.session_state['cliente_activo']]['Gasto Actual ($)'].sum():,.0f} COP" if not df_ads.empty else "$0 COP")
            c3.metric("Estado de la Cuenta", "🟢 Activa")
            st.markdown("---")
            df_ads_cli = df_ads[df_ads["Cliente"] == st.session_state["cliente_activo"]]
            if not df_ads_cli.empty:
                st.dataframe(df_ads_cli, use_container_width=True)
            else:
                st.info("No hay métricas de pauta registradas para este cliente.")

        with tab_d2:
            st.subheader("Simulador Proyectivo de ROAS")
            st.caption("Calcula el volumen estimado de clics, conversiones e ingresos según el presupuesto publicitario asignado.")
            c_roas1, c_roas2 = st.columns(2)
            presupuesto_inv = c_roas1.number_input("Inversión estimada en Ads ($ COP):", min_value=100000.0, value=1000000.0, step=100000.0)
            cpc_est = c_roas1.number_input("Costo por Clic estimado (CPC $ COP):", min_value=100.0, value=800.0, step=50.0)
            tasa_conv = c_roas2.number_input("Tasa de Conversión estimada (%):", min_value=0.1, value=2.5, step=0.5) / 100
            ticket_prom = c_roas2.number_input("Ticket Promedio de Venta ($ COP):", min_value=10000.0, value=150000.0, step=10000.0)

            clics_est = presupuesto_inv / cpc_est if cpc_est > 0 else 0
            ventas_est = clics_est * tasa_conv
            ingresos_est = ventas_est * ticket_prom
            roas_est = ingresos_est / presupuesto_inv if presupuesto_inv > 0 else 0

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clics Estimados", f"{clics_est:,.0f}")
            m2.metric("Ventas Proyectadas", f"{ventas_est:,.1f}")
            m3.metric("Ingresos Proyectados", f"${ingresos_est:,.0f} COP")
            m4.metric("ROAS Proyectado", f"{roas_est:.2f}x")

        with tab_d3:
            st.subheader("Radar de Tendencias de Nicho")
            st.caption("Realiza una búsqueda inteligente de tendencias recientes relacionadas con el nicho del cliente.")
            if st.button("🔎 Rastrear Tendencias Actuales"):
                with st.spinner("Buscando información de mercado..."):
                    res_w = buscar_en_internet(f"tendencias recientes de marketing para {st.session_state['cliente_activo']}")
                    st.markdown(res_w)

    elif bloque_cliente == "📅 [Contenidos] Generador IA, Visual Studio, Kanban & Guiones":
        st.title(f"📅 Gestión y Producción de Contenidos: {st.session_state['cliente_activo']}")
        st.caption("Suite completa para la creación masiva, desarrollo visual, organización Kanban y redacción de copys.")
        
        tab_c1, tab_c2, tab_c3, tab_c4, tab_c5 = st.tabs([
            "🤖 Generador Masivo (IA)", 
            "🎨 Prompt Studio (IA Visual)", 
            "📋 Tablero Kanban de Producción", 
            "🎬 Creador de Guiones Tácticos", 
            "✏️ Tabla Editora de Parrilla"
        ])

        with tab_c1:
            st.subheader("Generación Automática de Parrilla Mensual")
            st.caption("Crea múltiples publicaciones estratégicas listas para ser editadas o aprobadas.")
            col1, col2 = st.columns(2)
            f_in = col1.date_input("Fecha Inicio:", datetime.date.today())
            f_fi = col1.date_input("Fecha Fin:", datetime.date.today() + datetime.timedelta(days=14))
            redes_p = col2.multiselect("Redes Destino:", st.session_state["redes_disponibles"], default=["Instagram", "TikTok"])
            pauta_p = col2.number_input("Presupuesto de Pauta Sugerido ($ COP):", min_value=0.0, value=200000.0)
            
            if st.button("✨ Generar Parrilla Estratégica con Gemini", type="primary"):
                with st.spinner("Redactando estrategia y copys..."):
                    prompt = f"""
                    Genera 4 publicaciones estratégicas para '{st.session_state['cliente_activo']}' entre {f_in} y {f_fi} en redes {redes_p}. Presupuesto pauta: ${pauta_p}.
                    Devuelve SOLO un JSON estricto con la clave "publicaciones":
                    [{{"Red_Social": "Instagram", "Fecha_Publicacion": "{f_in}", "Tipo_Contenido": "Reel", "Detalle_Visual_Diseno": "Texto overlay...", "Copy_Texto": "Copy completo...", "Hashtags": "#Nicho", "Publico_Objetivo": "B2B", "Tipo_Pauta": "Tráfico", "Inversion_Pauta_COP": 50000}}]
                    """
                    try:
                        raw = consultar_gemini(prompt, modelo_seleccionado).text.replace("```json", "").replace("```", "").strip()
                        posts = json.loads(raw).get("publicaciones", [])
                        df_new = pd.DataFrame(posts)
                        df_new["Cliente"] = st.session_state["cliente_activo"]
                        df_new["Estado"] = "💡 Idea"
                        df_new["ID"] = [f"POST-{len(df_parrilla)+i+1}" for i in range(len(df_new))]
                        df_parrilla = pd.concat([df_parrilla, df_new[columnas_parrilla]], ignore_index=True)
                        guardar_datos("parrilla_contenidos.csv", df_parrilla)
                        st.success("¡Parrilla generada e integrada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generando contenido: {e}")

        with tab_c2:
            st.subheader("Studio de Prompts para Imagen e Inteligencia Visual")
            st.caption("Crea indicaciones de arte técnica en inglés optimizadas para Midjourney v6, DALL-E 3, Flux.1 o Imagen 3.")
            
            col_pr1, col_pr2 = st.columns(2)
            engine_ia = col_pr1.selectbox("Motor Visual Objetivos:", ["Midjourney v6", "DALL-E 3", "Flux.1", "Google Imagen 3"])
            aspect_ratio = col_pr1.selectbox("Formato / Aspect Ratio:", ["1:1 (Feed Cuadrado)", "9:16 (Stories / Reels / Vertical)", "16:9 (Horizontal / Youtube/ Banner)"])
            idea_img = col_pr2.text_input("Idea u Objeto Central del Prompt:", "Producto estrella presentado de forma elegante en mesa minimalista")
            estilo_art = col_pr2.selectbox("Estilo Visual & Iluminación:", ["Fotografía Realista 8K, Luz Cine Studio", "3D Render Minimalista Octane", "Estilo Editorial Vogue / Lujo", "Ilustración Vectorial Corporativa"])
            
            if st.button("🚀 Generar Prompt Artístico Técnico", type="primary"):
                with st.spinner("Construyendo prompt técnico..."):
                    ar_code = "--ar 9:16" if "9:16" in aspect_ratio else ("--ar 16:9" if "16:9" in aspect_ratio else "--ar 1:1")
                    prompt_req = f"Genera un prompt hiperdetallado en INGLÉS optimizado para {engine_ia}. Concepto: {idea_img}, Estilo: {estilo_art}. Incluye detalles cinematográficos, tipo de lente (85mm f/1.8), renderizado y parámetros de composición. Al final añade los parámetros: {ar_code}"
                    res_p = consultar_gemini(prompt_req, modelo_seleccionado).text
                    st.code(res_p, language="markdown")

        with tab_c3:
            st.subheader("Tablero Kanban de Estado de Producción")
            st.caption("Monitorea la evolución de cada pieza publicitaria según su etapa del flujo de trabajo.")
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            df_cli = df_parrilla[df_parrilla["Cliente"] == st.session_state["cliente_activo"]]
            estados_k = [("💡 Ideas / Borradores", "💡 Idea", col_k1), ("✍️ En Guión / Copy", "✍️ Guión / Copy", col_k2), ("🎨 En Diseño / Edición", "🎨 Diseño / Edición", col_k3), ("✅ Aprobado / Programado", "✅ Programado", col_k4)]

            for titulo, est_nombre, columna in estados_k:
                with columna:
                    st.markdown(f"**{titulo}**")
                    items = df_cli[df_cli["Estado"] == est_nombre]
                    if not items.empty:
                        for idx, row in items.iterrows():
                            st.markdown(f"""
                            <div class="kanban-card">
                                <b>{row['Red_Social']}</b> - {row['Tipo_Contenido']}<br>
                                <small>📅 {row['Fecha_Publicacion']}</small><br>
                                <p style="margin-top:5px; font-size:12px;">{str(row['Detalle_Visual_Diseno'])[:50]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("Sin elementos en esta etapa")

        with tab_c4:
            st.subheader("Creador de Guiones para Reels / TikTok")
            st.caption("Redacta estructuras completas divididas en gancho, desarrollo visual y llamado a la acción.")
            hook = st.selectbox("Ángulo o Gancho Emocional:", ["Curiosidad Disruptiva", "Problema Directo", "Error Común", "Caso de Éxito / Transformación"])
            prod = st.text_input("Producto o Oferta Central:", f"Oferta principal de {st.session_state['cliente_activo']}")
            if st.button("🚀 Redactar Guión Técnico Completo", type="primary"):
                with st.spinner("Escribiendo guión estructurado..."):
                    res = consultar_gemini(f"Crea un guión táctico de Reel/TikTok para {prod} usando el gancho: {hook}. Incluye indicación visual y locución.", modelo_seleccionado).text
                    st.markdown(res)

        with tab_c5:
            st.subheader("Tabla Editora Directa de Parrilla")
            st.caption("Modifica fechas, copys, textos de diseño o estados de forma tabular rápida.")
            df_cli = df_parrilla[df_parrilla["Cliente"] == st.session_state["cliente_activo"]]
            if not df_cli.empty:
                df_edited = st.data_editor(df_cli, num_rows="dynamic", use_container_width=True, key="ed_p_cli")
                if st.button("💾 Guardar Cambios en Parrilla", type="primary"):
                    df_parrilla.update(df_edited)
                    guardar_datos("parrilla_contenidos.csv", df_parrilla)
                    st.success("¡Parrilla de contenidos actualizada!")
                    st.rerun()
            else:
                st.info("No existen publicaciones registradas aún para este cliente.")

    elif bloque_cliente == "📦 [Brandkit] Guía de Estilo & Vault de Accesos":
        st.title(f"📦 Brandkit & Bóveda de Accesos: {st.session_state['cliente_activo']}")
        st.caption("Almacena de forma centralizada la paleta de colores, recursos visuales, credenciales y lineamientos del cliente.")
        
        df_bk_cli = df_brandkits[df_brandkits["Cliente"] == st.session_state["cliente_activo"]]
        
        with st.form("bk_form"):
            col_b1, col_b2 = st.columns(2)
            c_hex = col_b1.text_input("Codigos HEX Colores Corporativos:", value=df_bk_cli["Colores_HEX"].values[0] if not df_bk_cli.empty else "#0F172A, #2563EB")
            c_fonts = col_b1.text_input("Tipografías Oficiales:", value=df_bk_cli["Tipografias"].values[0] if not df_bk_cli.empty else "Inter / Montserrat")
            c_drive = col_b2.text_input("Link Carpeta Drive / Archivos Canva:", value=df_bk_cli["Link_Drive_Canva"].values[0] if not df_bk_cli.empty else "https://drive.google.com/...")
            c_pass = col_b2.text_area("Credenciales & Accesos Privados (Vault):", value=df_bk_cli["Credenciales_Redes"].values[0] if not df_bk_cli.empty else "IG: @usuario | Pass: ***")
            c_notes = st.text_area("Notas de Marca / Tono de Comunicación:", value=df_bk_cli["Notas_Marca"].values[0] if not df_bk_cli.empty else "Tono sofisticado, cercano y profesional.")
            
            if st.form_submit_button("💾 Guardar Brandkit"):
                df_brandkits = df_brandkits[df_brandkits["Cliente"] != st.session_state["cliente_activo"]]
                nueva_fila = pd.DataFrame([[st.session_state["cliente_activo"], c_hex, c_fonts, c_drive, c_pass, c_notes]], columns=["Cliente", "Colores_HEX", "Tipografias", "Link_Drive_Canva", "Credenciales_Redes", "Notas_Marca"])
                df_brandkits = pd.concat([df_brandkits, nueva_fila], ignore_index=True)
                guardar_datos("brandkits.csv", df_brandkits)
                st.success("¡Brandkit actualizado correctamente!")
                st.rerun()

    elif bloque_cliente == "👥 [CRM & SLA] Alta de Cliente, Contrato y Entregables":
        st.title("👥 Gestión CRM, Altas y Cumplimiento de Entregables (SLA)")
        st.caption("Administra la relación comercial, registra nuevos clientes y evalúa los tiempos de entrega.")
        
        tab_crm1, tab_crm2, tab_crm3 = st.tabs([
            "📋 Directorio General de Clientes", 
            "➕ Dar de Alta Nuevo Cliente", 
            "💼 Tiempos de Entrega & SLA"
        ])
        
        with tab_crm1:
            st.subheader("Clientes Actualmente Registrados")
            st.dataframe(df_clientes, use_container_width=True)

        with tab_crm2:
            st.subheader("Registro de Nuevo Cliente y Creación de Contrato")
            with st.form("form_nuevo_cliente"):
                nc_empresa = st.text_input("Nombre Comercial de la Empresa / Marca:")
                nc_contacto = st.text_input("Persona de Contacto Principal:")
                nc_telefono = st.text_input("WhatsApp con Indicativo País (ej: 573000000000):", value="573000000000")
                nc_nicho = st.text_input("Industria / Nicho de Mercado:")
                nc_redes = st.multiselect("Redes a Administrar:", st.session_state["redes_disponibles"], default=["Instagram"])
                nc_valor = st.number_input("Valor Mensual del Contrato ($ COP):", min_value=0.0, value=1500000.0, step=100000.0)
                
                if st.form_submit_button("🚀 Dar de Alta Cliente"):
                    if nc_empresa:
                        row_c = pd.DataFrame([[nc_contacto, nc_empresa, ", ".join(nc_redes), "Activo", nc_telefono, nc_nicho]], columns=df_clientes.columns)
                        df_clientes = pd.concat([df_clientes, row_c], ignore_index=True)
                        guardar_datos("clientes.csv", df_clientes)
                        
                        row_f = pd.DataFrame([[nc_empresa, nc_valor, str(datetime.date.today()), str(datetime.date.today() + datetime.timedelta(days=365)), "Pendiente"]], columns=df_finanzas.columns)
                        df_finanzas = pd.concat([df_finanzas, row_f], ignore_index=True)
                        guardar_datos("finanzas.csv", df_finanzas)
                        
                        st.success(f"¡Cliente {nc_empresa} dado de alta con éxito!")
                        st.rerun()

        with tab_crm3:
            st.subheader("Cumplimiento de Entregables (SLA)")
            st.caption("Listado de tareas pactadas y sus fechas límites contractuales.")
            st.dataframe(df_entregables[df_entregables["Cliente"] == st.session_state["cliente_activo"]], use_container_width=True)

# ==========================================
# 2. MÓDULO: AGENCIA VYNTARA IN-HOUSE
# ==========================================
elif espacio_trabajo == "🔥 Agencia Vyntara (Estrategia In-House)":
    st.title("🔥 Agencia Vyntara Digital | Módulo de Crecimiento Propio")
    st.caption("Gestiona la estrategia de marketing, generación de contenido y captación de clientes de la propia agencia.")

    menu_vyntara = st.sidebar.radio("Sección Vyntara:", [
        "🤖 [Parrilla Vyntara] Contenido Automático",
        "💡 [Creatividad] Hooks & Copys Disruptivos",
        "🎯 [Pipeline Leads] CRM Prospectos B2B",
        "📈 [Métricas Canales] Canales Oficiales"
    ])

    if menu_vyntara == "🤖 [Parrilla Vyntara] Contenido Automático":
        st.subheader("Generador Estratégico para Redes de Vyntara")
        col_v1, col_v2 = st.columns(2)
        objetivo_v = col_v1.selectbox("Objetivo de Contenido:", ["Captación de Leads B2B", "Posicionamiento de Autoridad", "Presentación de Casos de Éxito"])
        redes_v = col_v2.multiselect("Canales Oficiales:", st.session_state["redes_disponibles"], default=["LinkedIn", "Instagram"])

        if st.button("✨ Generar Contenido para Vyntara", type="primary"):
            with st.spinner("Creando posts para la marca propia..."):
                prompt = f"Genera 3 posts de alto valor B2B para Agencia Vyntara enfocados en {objetivo_v} para {redes_v}. Devuelve JSON con clave 'publicaciones'."
                try:
                    raw = consultar_gemini(prompt, modelo_seleccionado).text.replace("```json", "").replace("```", "").strip()
                    posts = json.loads(raw).get("publicaciones", [])
                    df_new = pd.DataFrame(posts)
                    df_new["Cliente"] = "Vyntara Digital"
                    df_new["Estado"] = "💡 Idea"
                    df_new["ID"] = [f"VYN-{len(df_parrilla)+i+1}" for i in range(len(df_new))]
                    df_parrilla = pd.concat([df_parrilla, df_new[columnas_parrilla]], ignore_index=True)
                    guardar_datos("parrilla_contenidos.csv", df_parrilla)
                    st.success("¡Contenido guardado en la parrilla propia!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Parrilla Vigente de Vyntara Digital")
        df_v_parrilla = df_parrilla[df_parrilla["Cliente"] == "Vyntara Digital"]
        if not df_v_parrilla.empty:
            st.dataframe(df_v_parrilla, use_container_width=True)

    elif menu_vyntara == "💡 [Creatividad] Hooks & Copys Disruptivos":
        st.subheader("Laboratorio de Ideas & Ganchos B2B")
        if st.button("🚀 Generar 3 Ganchos Disruptivos para Vyntara"):
            res = consultar_gemini("Genera 3 hooks tácticos de 3 segundos para vender servicios de marketing de Vyntara Digital.", modelo_seleccionado).text
            st.markdown(res)

    elif menu_vyntara == "🎯 [Pipeline Leads] CRM Prospectos B2B":
        st.subheader("Pipeline de Ventas y Prospectos Comerciales")
        
        tab_l1, tab_l2 = st.tabs(["📊 Embudo de Prospectos Activos", "➕ Registrar Nuevo Prospecto B2B"])
        
        with tab_l1:
            if not df_leads_vyntara.empty:
                df_leads_edited = st.data_editor(df_leads_vyntara, num_rows="dynamic", use_container_width=True, key="ed_leads_v")
                if st.button("💾 Guardar Pipeline de Ventas", type="primary"):
                    guardar_datos("vyntara_leads.csv", df_leads_edited)
                    st.success("Pipeline actualizado.")
                    st.rerun()
            else:
                st.info("No hay prospectos en seguimiento actualmente.")

        with tab_l2:
            with st.form("add_lead_v"):
                l_emp = st.text_input("Empresa Prospecto:")
                l_contacto = st.text_input("Contacto Principal:")
                l_tel = st.text_input("WhatsApp con Indicativo:", value="573000000000")
                l_val = st.number_input("Valor Estimado Oferta ($ COP):", min_value=0.0, step=100000.0)
                l_est = st.selectbox("Estado en Embudo:", ["Contacto Inicial", "Reunión Agendada", "Cotización Enviada", "Ganado / Cerrado", "Perdido"])
                l_notas = st.text_area("Requerimientos y Notas:")
                
                if st.form_submit_button("💾 Agregar Lead al CRM"):
                    nueva_f = pd.DataFrame([[l_emp, l_contacto, l_tel, l_val, l_est, l_notas]], columns=df_leads_vyntara.columns)
                    df_leads_vyntara = pd.concat([df_leads_vyntara, nueva_f], ignore_index=True)
                    guardar_datos("vyntara_leads.csv", df_leads_vyntara)
                    st.success("Prospecto guardado exitosamente.")
                    st.rerun()

    elif menu_vyntara == "📈 [Métricas Canales] Canales Oficiales":
        st.subheader("Métricas de Autoridad Propias")
        st.dataframe(df_vyntara, use_container_width=True)

# ==========================================
# 3. MÓDULO: COTIZADOR & PROPUESTAS PDF
# ==========================================
elif espacio_trabajo == "📄 Cotizador & Generador de PDF (Ventas)":
    st.title("📄 Cotizador Inteligente & Creador de Propuestas PDF")
    st.caption("Calcula tarifas según entregables, aplica márgenes de agencia, genera el archivo PDF y envía la propuesta vía WhatsApp.")

    with st.form("form_cotizador"):
        st.subheader("1. Datos del Cliente & Alcance")
        col_c1, col_c2 = st.columns(2)
        empresa_cotiz = col_c1.text_input("Empresa Solicitante:", "Empresa Ejemplo S.A.S.")
        atencion_cotiz = col_c1.text_input("Dirigido a (Nombre / Cargo):", "Juan Pérez - Gerente Comercial")
        tel_cotiz = col_c1.text_input("WhatsApp del Cliente (con indicativo):", "573001234567")
        tipo_trabajo = col_c2.selectbox("Tipo de Servicio:", ["Gestión Mensual de Redes & Ads", "Branding & Identidad Visual", "Producción de Reels / Videos Cortos", "Auditoría & Consultoría Digital", "Proyecto a Medida"])
        
        st.markdown("---")
        st.subheader("2. Desglose Operativo & Fee Mensual")
        
        d_col1, d_col2 = st.columns(2)
        reels_cant = d_col1.number_input("Cantidad de Reels / Videos Cortos:", min_value=0, value=8)
        posts_cant = d_col1.number_input("Cantidad de Carruseles / Post Estáticos:", min_value=0, value=12)
        presupuesto_ads_gest = d_col2.number_input("Presupuesto de Ads a Administrar ($ COP):", min_value=0.0, value=1000000.0, step=500000.0)
        fee_pauta_pct = d_col2.slider("% Fee de Gestión sobre Pauta Publicitaria:", min_value=5, max_value=30, value=15) / 100

        servicios_extra = st.multiselect("Servicios Adicionales a Incluir:", ["Diseño de Identidad Visual", "Estrategia de Email Marketing", "Diseño de Landing Page", "Reportes Semanales VIP"], default=["Reportes Semanales VIP"])
        
        costo_base = (reels_cant * 50000) + (posts_cant * 30000) + (presupuesto_ads_gest * fee_pauta_pct) + (len(servicios_extra) * 150000)
        margen_agencia = st.slider("Margen de Ganancia Agencia (%):", min_value=20, max_value=70, value=40) / 100
        
        fee_total_calculado = costo_base / (1 - margen_agencia) if margen_agencia < 1 else costo_base
        observaciones_cotiz = st.text_area("Condiciones Generales & Alcance:", "Incluye 2 rondas de corrección por entrega. Pagos dentro de los primeros 5 días de cada mes.")

        btn_calcular = st.form_submit_button("🧮 Generar Cotización Formal")

    if btn_calcular or fee_total_calculado > 0:
        st.markdown("---")
        st.subheader("📋 Resumen Financiero del Proyecto")
        
        m_cot1, m_cot2 = st.columns(2)
        m_cot1.metric("Costo Operativo Interno Estimado", f"${costo_base:,.0f} COP")
        m_cot2.metric("PROPUESTA FINAL / FEE MENSUAL CLIENTE", f"${fee_total_calculado:,.0f} COP", delta=f"{margen_agencia*100:.0f}% Margen")

        desglose_lista = [
            f"Gestion y produccion de {reels_cant} Reels / Videos Cortos mensuales.",
            f"Diseno y redaccion para {posts_cant} publicaciones de imagen / carruseles.",
            f"Administracion de pauta publicitaria (Presupuesto Ads gestionado: ${presupuesto_ads_gest:,.0f} COP)."
        ] + [f"Servicio extra: {s}" for s in servicios_extra]

        bytes_pdf = generar_pdf_cotizacion(
            empresa=empresa_cotiz,
            atencion_a=atencion_cotiz,
            tipo_trabajo=tipo_trabajo,
            desglose=desglose_lista,
            fee_total=fee_total_calculado,
            observaciones=observaciones_cotiz
        )

        col_desc1, col_desc2 = st.columns(2)
        
        col_desc1.download_button(
            label="📄 Descargar Propuesta en PDF",
            data=bytes_pdf,
            file_name=f"Cotizacion_Vyntara_{empresa_cotiz.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary"
        )

        msg_wa = f"Hola {atencion_cotiz}, un gusto saludarte de Vyntara Digital. 👋\n\nTe comparto la propuesta formal para {empresa_cotiz}:\n• Proyecto: {tipo_trabajo}\n• Inversión Mensual: ${fee_total_calculado:,.0f} COP\n\nQuedamos atentos a tus comentarios.✨"
        link_wa = crear_link_whatsapp(tel_cotiz, msg_wa)
        col_desc2.markdown(f'[![Enviar por WhatsApp](https://img.shields.io/badge/Enviar_Cotizacion-WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({link_wa})')

# ==========================================
# 4. MÓDULO: VISTA CLIENTE
# ==========================================
elif espacio_trabajo == "👁️ Portal Cliente (Aprobación Externa)":
    st.title("👁️ Portal de Revisión y Aprobación de Clientes")
    st.caption("Entorno de interfaz limpia pensado para que los clientes finales revisen, aprueben o soliciten ajustes en sus contenidos sin entrar al panel interno.")

    lista_empresas = df_clientes["Empresa"].unique().tolist() if not df_clientes.empty else []
    if lista_empresas:
        cliente_vista = st.selectbox("👁️ Selecciona la Empresa para Simular la Vista del Cliente:", lista_empresas)
        st.markdown("---")
        
        st.markdown(f"### 📋 Publicaciones en Proceso para: **{cliente_vista}**")
        df_p_cli = df_parrilla[df_parrilla["Cliente"] == cliente_vista]
        
        if not df_p_cli.empty:
            for idx, row in df_p_cli.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="client-preview-card">
                        <h4>{row['Red_Social']} - {row['Tipo_Contenido']} ({row['Fecha_Publicacion']})</h4>
                        <p><b>Propuesta Visual / Diseño:</b> {row['Detalle_Visual_Diseno']}</p>
                        <p><b>Copy / Texto sugerido:</b><br><i>"{row['Copy_Texto']}"</i></p>
                        <p><b>Hashtags:</b> {row['Hashtags']}</p>
                        <p><b>Estado Actual:</b> <code>{row['Estado']}</code></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_act1, c_act2 = st.columns(2)
                    if c_act1.button(f"✅ Aprobar Post #{row['ID']}", key=f"app_{row['ID']}"):
                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Estado"] = "✅ Programado"
                        guardar_datos("parrilla_contenidos.csv", df_parrilla)
                        st.success(f"Publicación #{row['ID']} aprobada con éxito.")
                        st.rerun()

                    if c_act2.button(f"💬 Solicitar Ajuste #{row['ID']}", key=f"adj_{row['ID']}"):
                        df_parrilla.loc[df_parrilla["ID"] == row['ID'], "Estado"] = "✍️ Guión / Copy"
                        guardar_datos("parrilla_contenidos.csv", df_parrilla)
                        st.warning(f"Publicación #{row['ID']} marcada para revisión.")
                        st.rerun()
        else:
            st.info("No hay contenidos asignados actualmente para este cliente.")

# ==========================================
# 5. MÓDULO: CONFIGURACIÓN GLOBAL & BACKUPS
# ==========================================
elif espacio_trabajo == "⚙️ Configuración Global & Copias de Seguridad":
    st.title("⚙️ Ajustes del Sistema & Centro de Respaldos")
    st.caption("Administración de credenciales API y descarga empaquetada de copias de seguridad de las bases de datos.")
    
    st.subheader("🔑 Clave de Acceso API Google Gemini")
    api_key_in = st.text_input("Clave API Activa:", value=st.session_state["api_key_activa"], type="password")
    
    if st.button("💾 Guardar Clave API", type="primary"):
        st.session_state["api_key_activa"] = api_key_in
        st.success("Clave API guardada.")

    st.markdown("---")
    st.subheader("💾 Backup y Descarga de Bases de Datos (.ZIP)")
    st.caption("Empaqueta todos los archivos `.csv` del sistema en un único archivo comprimido listo para resguardo local.")

    if st.button("📦 Generar Archivo de Backup (.ZIP)", type="primary"):
        buffer = io.BytesIO()
        archivos_incluidos = 0
        with zipfile.ZipFile(buffer, "w") as zf:
            for archivo in archivos_csv:
                ruta_a = os.path.join(directorio_actual, archivo)
                if os.path.exists(ruta_a):
                    zf.write(ruta_a, arcname=archivo)
                    archivos_incluidos += 1
        
        st.success(f"¡Copia de seguridad empaquetada con éxito! ({archivos_incluidos} bases de datos).")
        
        st.download_button(
            label="💾 Descargar Respaldo Completo ZIP",
            data=buffer.getvalue(),
            file_name=f"Vyntara_OS_Backup_{datetime.date.today()}.zip",
            mime="application/zip"
        )
