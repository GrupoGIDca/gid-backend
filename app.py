# ════════════════════════════════════════════════════════════════
# GID C.A. — Backend API
# Flask + ReportLab + Google Sheets
# ════════════════════════════════════════════════════════════════

import os, io, json, base64
import requests as req_lib
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

app = Flask(__name__)
CORS(app)  # Permite que el panel admin (GitHub Pages) llame a este backend

W, H = A4
BG      = colors.HexColor('#0d1a0f')
GREEN   = colors.HexColor('#4ade80')
WHITE   = colors.white
MUTED   = colors.HexColor('#6b8f6b')
CARD_BG = colors.HexColor('#132213')
DIVIDER = colors.HexColor('#1e3a1e')
DARK_BG = colors.HexColor('#071007')
DARK2   = colors.HexColor('#0a150a')
AMBER   = colors.HexColor('#fbbf24')
AMBER_BG= colors.HexColor('#1e1700')
AMBER_TX= colors.HexColor('#fde68a')
RED     = colors.HexColor('#f87171')

# ── HELPERS PDF ─────────────────────────────────────────────────
def rrect(c, x, y, w, h, r, fill, stroke=None):
    c.saveState()
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(0.5 if stroke else 0)
    p = c.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y, x+w, y+2*r, startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r, x+w, y+h, startAng=0, extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-2*r, x+2*r, y+h, startAng=90, extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x, y, x+2*r, y+2*r, startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1, stroke=1 if stroke else 0)
    c.restoreState()

def circ(c, cx, cy, r, fill):
    c.saveState(); c.setFillColor(fill)
    c.circle(cx, cy, r, fill=1, stroke=0); c.restoreState()

def hline(c, x1, x2, y, lw=0.3):
    c.saveState(); c.setStrokeColor(DIVIDER)
    c.setLineWidth(lw); c.line(x1, y, x2, y); c.restoreState()

def wrap_text(c, text, font, size, max_w):
    words = text.split(); lines = []; cur = ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if c.stringWidth(test, font, size) <= max_w: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fmt(n):
    return f"$ {float(n):,.2f}"

def draw_header(cv, mg, cw, cx, doc_num, fecha, titulo):
    hh = 48*mm; hy = H - 24*mm - hh
    PAD = 8*mm
    rrect(cv, cx, hy, cw, hh, 8, CARD_BG, DIVIDER)
    cv.setFillColor(GREEN); cv.rect(cx, hy+hh-2, cw, 2, fill=1, stroke=0)
    cv.saveState(); cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold', 44)
    cv.drawString(cx+PAD, hy+20*mm, 'GID'); cv.restoreState()
    circ(cv, cx+PAD+76, hy+20*mm+10, 5, GREEN)
    cv.saveState(); cv.setFillColor(MUTED); cv.setFont('Helvetica', 7)
    cv.drawString(cx+PAD, hy+15*mm, 'INTELIGENCIA FINANCIERA · VENEZUELA')
    cv.drawRightString(cx+cw-PAD, hy+36*mm, str(titulo))
    cv.setFillColor(GREEN); cv.setFont('Helvetica-Bold', 9)
    cv.drawRightString(cx+cw-PAD, hy+30*mm, str(doc_num))
    cv.setFillColor(MUTED); cv.setFont('Helvetica', 7)
    cv.drawRightString(cx+cw-PAD, hy+24*mm, str(fecha))
    cv.restoreState()
    return hy

def draw_footer(cv, mg):
    cv.saveState(); cv.setFillColor(DIVIDER)
    cv.rect(0, 0, W, 11*mm, fill=1, stroke=0)
    cv.setFillColor(MUTED); cv.setFont('Helvetica', 7)
    cv.drawString(mg, 4*mm, 'GID C.A. · Inteligencia Financiera · © 2026 · Todos los derechos reservados')
    cv.setFillColor(GREEN); cv.setFont('Helvetica-Bold', 7)
    cv.drawRightString(W-mg, 4*mm, 'CONFIDENCIAL')
    cv.restoreState()

def draw_client_card(cv, cx, cw, y, nombre, cedula, subtitulo, initiales, segunda_linea=None):
    PAD = 8*mm; RAD = 5; GAP = 6*mm
    cl_h = 20*mm if segunda_linea else 16*mm
    cl_y = y - GAP - cl_h
    rrect(cv, cx, cl_y, cw, cl_h, RAD, CARD_BG, DIVIDER)
    circ(cv, cx+13*mm, cl_y+cl_h/2, 8.5, GREEN)
    cv.saveState(); cv.setFillColor(CARD_BG); cv.setFont('Helvetica-Bold', 7)
    cv.drawCentredString(cx+13*mm, cl_y+cl_h/2-2.5, str(initiales)); cv.restoreState()
    cv.saveState()
    cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold', 11)
    name_y = cl_y + cl_h - 7*mm
    cv.drawString(cx+24*mm, name_y, str(nombre))
    if segunda_linea:
        cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold', 11)
        cv.drawString(cx+24*mm, name_y - 6*mm, str(segunda_linea))
    cv.setFillColor(MUTED); cv.setFont('Helvetica', 7)
    sub_y = cl_y + 3.5*mm
    cv.drawString(cx+24*mm, sub_y, f"{str(cedula) + '  ·  ' if cedula else ''}{subtitulo}")
    cv.restoreState()
    return cl_y

def draw_data_card(cv, cx, cw, y, rows, gap=6*mm):
    PAD = 8*mm; RH = 7*mm; RAD = 5
    d_h = len(rows)*RH + 4*mm
    d_y = y - gap - d_h
    rrect(cv, cx, d_y, cw, d_h, RAD, CARD_BG, DIVIDER)
    for i, (lbl, val, hi) in enumerate(rows):
        ry = d_y + d_h - 2*mm - (i+1)*RH + 1.5*mm
        if i < len(rows)-1: hline(cv, cx+PAD, cx+cw-PAD, ry)
        cv.saveState()
        cv.setFillColor(MUTED); cv.setFont('Helvetica', 8)
        cv.drawString(cx+PAD, ry+2.2*mm, str(lbl))
        cv.setFillColor(GREEN if hi else WHITE)
        cv.setFont('Helvetica-Bold' if hi else 'Helvetica', 8)
        cv.drawRightString(cx+cw-PAD, ry+2.2*mm, str(val))
        cv.restoreState()
    return d_y

def draw_credit_card(cv, cx, cw, y, titulo, badge_txt, data_rows, pago_min, cancelacion, gap=6*mm):
    PAD = 8*mm; RH = 7*mm; HDR = 10*mm; RAD = 5; TR = 9*mm
    data_h = len(data_rows)*RH
    j_h = HDR + data_h + 2*mm + TR*2
    j_y = y - gap - j_h
    rrect(cv, cx, j_y, cw, j_h, RAD, CARD_BG, DIVIDER)
    rrect(cv, cx, j_y+j_h-HDR, cw, HDR, RAD, DIVIDER, DIVIDER)
    cv.saveState()
    cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold', 9)
    cv.drawString(cx+PAD, j_y+j_h-HDR+3*mm, str(titulo))
    bw = 30*mm; bx = cx+cw-PAD-bw
    rrect(cv, bx, j_y+j_h-HDR+2*mm, bw, 5.5*mm, 2.5, colors.HexColor('#1a3a1a'))
    cv.setFillColor(GREEN); cv.setFont('Helvetica-Bold', 7)
    cv.drawCentredString(bx+bw/2, j_y+j_h-HDR+4.2*mm, str(badge_txt))
    cv.restoreState()
    data_top = j_y + j_h - HDR
    for i, (lbl, val, hi) in enumerate(data_rows):
        row_top = data_top - (i+1)*RH
        ry = row_top + 2*mm
        hline(cv, cx+PAD, cx+cw-PAD, row_top)
        cv.saveState()
        cv.setFillColor(MUTED); cv.setFont('Helvetica', 8)
        cv.drawString(cx+PAD, ry, str(lbl))
        cv.setFillColor(GREEN if hi else WHITE)
        cv.setFont('Helvetica-Bold' if hi else 'Helvetica', 8)
        cv.drawRightString(cx+cw-PAD, ry, str(val))
        cv.restoreState()
    hline(cv, cx, cx+cw, j_y+TR*2, lw=0.5)
    # Pago minimo
    rrect(cv, cx, j_y+TR, cw, TR, 0, DARK_BG)
    hline(cv, cx, cx+cw, j_y+TR, lw=0.4)
    cv.saveState()
    cv.setFillColor(MUTED); cv.setFont('Helvetica', 6.5)
    cv.drawString(cx+PAD, j_y+TR+5.5*mm, 'PAGO MINIMO — Renueva el credito un mes mas')
    cv.setFillColor(colors.HexColor('#9ca89c')); cv.setFont('Helvetica', 6)
    cv.drawString(cx+PAD, j_y+TR+2.5*mm, 'Solo interes mensual')
    cv.setFillColor(GREEN); cv.setFont('Helvetica-Bold', 13)
    cv.drawRightString(cx+cw-PAD, j_y+TR+3*mm, str(pago_min))
    cv.restoreState()
    # Cancelacion total
    rrect(cv, cx, j_y, cw, TR, RAD, DARK2)
    cv.saveState()
    cv.setFillColor(MUTED); cv.setFont('Helvetica', 6.5)
    cv.drawString(cx+PAD, j_y+5.5*mm, 'CANCELACION TOTAL — Capital + interes')
    cv.setFillColor(colors.HexColor('#9ca89c')); cv.setFont('Helvetica', 6)
    cap_str = str(cancelacion.get('detalle', ''))
    cv.drawString(cx+PAD, j_y+2.5*mm, cap_str)
    cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold', 13)
    cv.drawRightString(cx+cw-PAD, j_y+3*mm, str(cancelacion['total']))
    cv.restoreState()
    return j_y

def draw_amber_note(cv, cx, cw, y, titulo, paragraphs, gap=5*mm):
    PAD = 8*mm
    NOTE_FONT = 'Helvetica'; NOTE_SIZE = 7.5; NOTE_LH = 4.2*mm; NOTE_PGAP = 2.5*mm
    inner_w = cw - 2*PAD - 3
    note_h = 9*mm + 2*mm
    for para in paragraphs:
        if para == '': note_h += NOTE_PGAP
        else: note_h += len(wrap_text(cv, para, NOTE_FONT, NOTE_SIZE, inner_w)) * NOTE_LH
    note_h += 5*mm
    note_y = y - gap - note_h
    rrect(cv, cx, note_y, cw, note_h, 5, AMBER_BG, AMBER)
    cv.saveState(); cv.setFillColor(AMBER)
    cv.rect(cx, note_y, 3, note_h, fill=1, stroke=0); cv.restoreState()
    cv.saveState(); cv.setFillColor(AMBER); cv.setFont('Helvetica-Bold', 8.5)
    cv.drawString(cx+PAD, note_y+note_h-7*mm, titulo); cv.restoreState()
    hline(cv, cx+PAD, cx+cw-PAD, note_y+note_h-9*mm, lw=0.4)
    text_y = note_y + note_h - 9*mm - 1*mm
    cv.saveState(); cv.setFillColor(AMBER_TX)
    for para in paragraphs:
        if para == '': text_y -= NOTE_PGAP; continue
        for line in wrap_text(cv, para, NOTE_FONT, NOTE_SIZE, inner_w):
            cv.setFont(NOTE_FONT, NOTE_SIZE)
            cv.drawString(cx+PAD, text_y, line)
            text_y -= NOTE_LH
    cv.restoreState()
    return note_y

# ══════════════════════════════════════════════════════════════════
# GENERADOR DE PDF PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def generar_pdf(data):
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    mg = 26*mm; cw = W - 2*mg; cx = mg
    GAP = 6*mm

    cv.setFillColor(BG); cv.rect(0, 0, W, H, fill=1, stroke=0)

    tipo = str(data.get('tipo', 'simple'))
    nombre = str(data.get('nombre', ''))
    cedula = str(data.get('cedula', ''))
    segunda_linea = data.get('segunda_linea', None)
    if segunda_linea: segunda_linea = str(segunda_linea)
    doc_num = str(data.get('doc_num', 'GID-2026-0000'))
    fecha = str(data.get('fecha', '10 de junio de 2026'))
    titulo_doc = str(data.get('titulo_doc', 'ESTADO DE CUENTA'))
    initiales = str(data.get('initiales', nombre[:2].upper() if nombre else 'GD'))

    hy = draw_header(cv, mg, cw, cx, doc_num, fecha, titulo_doc)
    cl_y = draw_client_card(cv, cx, cw, hy, nombre, cedula,
                             data.get('subtitulo_cliente', 'Cliente activo · 1 credito vigente'),
                             initiales, segunda_linea)
    y = cl_y

    # Sección resumen de pago (si hay abono previo)
    if data.get('resumen_mayo'):
        cv.saveState(); cv.setFillColor(MUTED); cv.setFont('Helvetica', 6.5)
        cv.drawString(cx, y-6*mm, data['resumen_mayo']['titulo']); cv.restoreState()
        y = draw_data_card(cv, cx, cw, y-6*mm, data['resumen_mayo']['rows'], gap=3*mm)

    # Créditos (uno o varios)
    for credito in data.get('creditos', []):
        lbl_y = y - 6*mm
        cv.saveState(); cv.setFillColor(MUTED); cv.setFont('Helvetica', 6.5)
        cv.drawString(cx, lbl_y, credito.get('seccion', 'COBRO CORRESPONDIENTE')); cv.restoreState()

        if credito.get('tipo') == 'detalle':
            # Solo detalle sin totales dobles (crédito nuevo)
            y = draw_data_card(cv, cx, cw, lbl_y, credito['rows'], gap=3*mm)
            lbl_y2 = y - 6*mm
            cv.saveState(); cv.setFillColor(MUTED); cv.setFont('Helvetica', 6.5)
            cv.drawString(cx, lbl_y2, credito.get('seccion2', 'COBRO CORRESPONDIENTE')); cv.restoreState()
            y = draw_credit_card(cv, cx, cw, lbl_y2, credito['card_titulo'],
                                  credito['badge'], credito['data_rows'],
                                  credito['pago_min'], credito['cancelacion'], gap=3*mm)
        else:
            y = draw_credit_card(cv, cx, cw, lbl_y, credito['card_titulo'],
                                  credito['badge'], credito['data_rows'],
                                  credito['pago_min'], credito['cancelacion'], gap=3*mm)

    # Nota ámbar (ajuste de tasa, aviso legal, etc.)
    if data.get('nota_amber'):
        y = draw_amber_note(cv, cx, cw, y, data['nota_amber']['titulo'], data['nota_amber']['paragraphs'])

    draw_footer(cv, mg)
    cv.save()
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════
# RUTAS API
# ══════════════════════════════════════════════════════════════════

SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbzCZUcXeB9up4IYEfIbl0Y5W7pQ9e06NXuu9H73r_2o4cofGvdJKttSYHYJBRWSecyi/exec'

@app.route('/', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'sistema': 'GID C.A. Backend', 'version': '1.1'})

@app.route('/pdf/enviar-email', methods=['POST'])
def enviar_email():
    """Genera PDF y lo envía por email via Apps Script."""
    try:
        data = request.json
        correo = data.get('correo','')
        nombre = data.get('nombre','Cliente')
        if not correo or '@' not in correo:
            return jsonify({'error': 'Correo inválido'}), 400

        # Generar PDF
        buf = generar_pdf(data)
        pdf_b64 = base64.b64encode(buf.read()).decode('utf-8')

        # Enviar via Apps Script
        payload = {
            'tipo': 'enviar_recibo',
            'correo': correo,
            'nombre': nombre,
            'pdf_base64': pdf_b64,
            'filename': f'Recibo_{nombre.replace(" ","_")}_GID.pdf'
        }
        r = req_lib.post(SCRIPT_URL, json=payload, timeout=30, allow_redirects=True)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf/generar', methods=['POST'])
def generar():
    """Genera un PDF y lo devuelve como descarga."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        buf = generar_pdf(data)
        nombre_archivo = data.get('nombre', 'cliente').replace(' ', '_')
        return send_file(buf, mimetype='application/pdf',
                         as_attachment=True,
                         download_name=f"Recibo_{nombre_archivo}_GID.pdf")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf/base64', methods=['POST'])
def generar_base64():
    """Genera un PDF y lo devuelve en base64 (para adjuntar a emails)."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        buf = generar_pdf(data)
        pdf_b64 = base64.b64encode(buf.read()).decode('utf-8')
        nombre_archivo = data.get('nombre', 'cliente').replace(' ', '_')
        return jsonify({
            'status': 'ok',
            'filename': f"Recibo_{nombre_archivo}_GID.pdf",
            'base64': pdf_b64
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sheets/creditos', methods=['GET'])
def leer_creditos():
    """Lee los créditos desde Google Sheets."""
    return _leer_hoja('Creditos')

@app.route('/sheets/pagos', methods=['GET'])
def leer_pagos():
    """Lee los pagos desde Google Sheets."""
    return _leer_hoja('Pagos')

@app.route('/sheets/solicitudes', methods=['GET'])
def leer_solicitudes():
    """Lee las solicitudes desde Google Sheets."""
    return _leer_hoja('Solicitudes')

def _leer_hoja(nombre):
    try:
        url = SCRIPT_URL + '?sheet=' + nombre
        r = req_lib.get(url, timeout=15, allow_redirects=True)
        data = r.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'resultado': 'error', 'detalle': str(e)}), 500

@app.route('/sheets/actualizar-pago', methods=['POST'])
def actualizar_pago():
    """Actualiza el estado de un pago en Google Sheets."""
    try:
        data = request.json
        fila = data.get('fila')
        estado = data.get('estado', 'APROBADO')
        payload = {
            'tipo': 'actualizar_pago',
            'fila': fila,
            'estado': estado
        }
        r = req_lib.post(SCRIPT_URL, json=payload, timeout=15, allow_redirects=True)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'resultado': 'error', 'detalle': str(e)}), 500

@app.route('/sheets/notificar-aprobacion', methods=['POST'])
def notificar_aprobacion():
    """Envía email de aprobación al cliente via Apps Script."""
    try:
        data = request.json
        payload = {
            'tipo': 'notificar_aprobacion',
            'nombre': data.get('nombre',''),
            'correo': data.get('correo',''),
            'capital': data.get('capital',0),
            'tasa': data.get('tasa',0),
            'interes': data.get('interes',0),
            'dia': data.get('dia',0),
            'mes': data.get('mes',0),
            'notas': data.get('notas','')
        }
        r = req_lib.post(SCRIPT_URL, json=payload, timeout=15, allow_redirects=True)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'resultado': 'error', 'detalle': str(e)}), 500

@app.route('/sheets/sync', methods=['POST'])
def sync_creditos():
    """Sincroniza la cartera con Google Sheets via Apps Script."""
    try:
        import urllib.request, urllib.parse
        payload = request.json
        if not payload:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Enviar al Apps Script desde el servidor (sin problemas de CORS)
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            SCRIPT_URL,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return jsonify(data)
    except Exception as e:
        return jsonify({'resultado': 'error', 'detalle': str(e)}), 500

@app.route('/sheets/pago', methods=['POST'])
def registrar_pago():
    """Registra un pago manual en Google Sheets."""
    try:
        import urllib.request
        payload = request.json
        if not payload:
            return jsonify({'error': 'No se recibieron datos'}), 400
        payload['tipo'] = 'pago'
        r = req_lib.post(SCRIPT_URL, json=payload, timeout=15, allow_redirects=True)
        data = r.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'resultado': 'error', 'detalle': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
