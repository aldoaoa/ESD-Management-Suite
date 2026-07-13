from datetime import datetime

def generate_esd_html_report(asset_data, meas_data, site_name, auditor_name):
    """
    Genera el reporte HTML de Validación Integral basado en el estándar ANSI/ESD S20.20-2021.
    """
    db_id = asset_data.get("id", "000")
    # Si es UUID y queremos un corto
    if isinstance(db_id, str) and len(db_id) > 8:
        db_id = db_id[:8].upper()
        
    año_actual = datetime.today().strftime("%y")
    fecha_ejecucion = datetime.today().strftime("%Y-%m-%d")
    
    custom_id = asset_data.get("custom_id", "N/A")
    category = asset_data.get("category", "N/A")
    classification = asset_data.get("classification", "N/A")
    location = asset_data.get("location", "N/A")
    
    # Extraer mediciones individuales
    mediciones_str = []
    if "extra_data" in meas_data and meas_data["extra_data"]:
        # Se asume que extra_data tiene llaves tipo m1, m2, m3...
        for key in sorted(meas_data["extra_data"].keys()):
            val = meas_data["extra_data"][key]
            try:
                val_num = float(val)
                # Formatear a notación científica si es muy grande
                val_str = f"{val_num:.2E}" if val_num > 1000 or val_num < 0.01 else str(val)
            except:
                val_str = str(val)
            mediciones_str.append(val_str)
    else:
        # Si no hay extra_data, usar la medición principal (resistencia)
        res = meas_data.get("resistance_value", "N/A")
        try:
            val_num = float(res)
            val_str = f"{val_num:.2E}" if val_num > 1000 or val_num < 0.01 else str(res)
        except:
            val_str = str(res)
        mediciones_str.append(val_str)

    # Promedio
    promedio = meas_data.get("resistance_value", 0)
    try:
        promedio_num = float(promedio)
        promedio_str = f"{promedio_num:.2E}" if promedio_num > 0 else "N/A"
    except:
        promedio_str = str(promedio)
        
    # Limite de Referencia (Aproximado basado en categoría)
    limite = "1.00E+09" if category != "Maquinaria" else "1.00"

    html_rows = ""
    for i, val_str in enumerate(mediciones_str, 1):
        html_rows += f"""
        <tr class="border-b border-gray-200 hover:bg-blue-50 print:hover:bg-transparent text-center">
            <td class="p-1 border-r border-gray-300 font-bold">{i}</td>
            <td class="p-1 border-r border-gray-300 font-mono">{limite}</td>
            <td class="p-1 border-r border-gray-300 bg-yellow-50 print:bg-transparent font-mono font-bold">{val_str}</td>
            <td class="p-1 border-r border-gray-300">RTG / P2P</td>
            <td class="p-1 border-r border-gray-300">Ohms</td>
            <td class="p-1 border-r border-gray-300">{location}</td>
        </tr>
        """
        
    resultado_str = str(meas_data.get('status_result', 'N/A')).upper()
    
    if "FAIL" in resultado_str or "RECHAZADO" in resultado_str:
        res_color = "text-red-600"
    else:
        res_color = "text-green-600"
        
    observaciones = meas_data.get("observaciones", "Sin observaciones adicionales.")
    if not observaciones:
        observaciones = "Sin observaciones adicionales."
        
    temperatura = meas_data.get("temperatura", "N/A")
    humedad = meas_data.get("humedad", "N/A")
        
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BCS-PV-{db_id}-{año_actual}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>@media print {{ body {{ -webkit-print-color-adjust: exact; }} }}</style>
</head>
<body class="bg-gray-100 p-4 md:p-8 font-sans text-sm print:bg-white print:p-0">
    <div class="max-w-5xl mx-auto mb-6 bg-white p-4 rounded-lg shadow flex justify-end print:hidden">
        <button onclick="window.print()" class="bg-blue-600 text-white px-6 py-2 rounded font-bold shadow-sm">🖨️ Imprimir / Guardar PDF</button>
    </div>
    <div class="max-w-5xl mx-auto bg-white shadow-xl print:shadow-none print:w-full">
        <div class="border-b-2 border-gray-800 p-6 flex items-start justify-between">
            <div class="w-1/3">
                <!-- <img src="https://via.placeholder.com/150x50?text=Logo+BCS" alt="Logo" class="h-16 object-contain" /> -->
                <div class="text-2xl font-bold text-gray-800">ESD SYSTEM</div>
            </div>
            <div class="w-1/3 text-center">
                <h1 class="text-lg font-bold text-gray-800">FORMATO DE VALIDACIÓN DE PRODUCTO (ESD)</h1>
                <p class="text-xs text-gray-600">ANSI/ESD S20.20-2021</p>
                <p class="text-xs text-gray-500">{site_name}</p>
            </div>
            <div class="w-1/3 text-right text-sm">
                <div class="font-bold text-red-700 text-lg mb-2">Reporte: PV-{db_id}-{año_actual}</div>
                <div class="flex justify-end gap-2 mb-1">
                    <span class="font-bold">Fecha de Ejecución:</span><span>{fecha_ejecucion}</span>
                </div>
                <div class="flex justify-end gap-2 mb-1">
                    <span class="font-bold">Auditor:</span><span>{auditor_name}</span>
                </div>
            </div>
        </div>
        <div class="p-6 space-y-6">
            <div class="grid grid-cols-2 gap-6">
                <div>
                    <div class="bg-gray-800 text-white font-bold px-2 py-1 uppercase text-xs">Datos del Elemento de Control</div>
                    <table class="w-full text-sm border-collapse border border-gray-300">
                        <tr class="border-b border-gray-300"><td class="w-1/3 font-bold bg-gray-100 p-1 border-r border-gray-300">ID:</td><td class="p-1">{custom_id}</td></tr>
                        <tr class="border-b border-gray-300"><td class="w-1/3 font-bold bg-gray-100 p-1 border-r border-gray-300">Elemento:</td><td class="p-1">{classification}</td></tr>
                        <tr class="border-b border-gray-300"><td class="w-1/3 font-bold bg-gray-100 p-1 border-r border-gray-300">Ubicación:</td><td class="p-1">{location}</td></tr>
                    </table>
                </div>
                <div>
                    <div class="bg-gray-800 text-white font-bold px-2 py-1 uppercase text-xs">Condiciones Ambientales</div>
                    <table class="w-full text-sm border-collapse border border-gray-300">
                        <tr class="border-b border-gray-300"><td class="w-1/3 font-bold bg-gray-100 p-1 border-r border-gray-300">Temperatura:</td><td class="p-1">{temperatura} °C</td></tr>
                        <tr class="border-b border-gray-300"><td class="w-1/3 font-bold bg-gray-100 p-1 border-r border-gray-300">Humedad:</td><td class="p-1">{humedad} %</td></tr>
                    </table>
                </div>
            </div>
            <div>
                <div class="bg-gray-800 text-white font-bold px-2 py-1 uppercase text-xs">Resultados (ANSI/ESD S20.20)</div>
                <table class="w-full text-sm border-collapse border border-gray-300 text-center">
                    <tr class="bg-gray-100 border-b border-gray-300">
                        <th class="p-2 border-r border-gray-300">No.</th>
                        <th class="p-2 border-r border-gray-300">Referencia (Máx)</th>
                        <th class="p-2 border-r border-gray-300">Resultado Obtenido</th>
                        <th class="p-2 border-r border-gray-300">Método de Prueba</th>
                        <th class="p-2 border-r border-gray-300">Unidad</th>
                        <th class="p-2 border-r border-gray-300">Punto de Colocación</th>
                    </tr>
                    {html_rows}
                    <tr class="border-t-2 border-gray-400 bg-gray-50">
                        <td colspan="2" class="p-2 font-bold text-right border-r border-gray-300">Promedio / Final:</td>
                        <td class="p-2 font-mono font-bold text-center border-r border-gray-300 text-blue-700">{promedio_str}</td>
                        <td colspan="3"></td>
                    </tr>
                </table>
            </div>
            <div class="grid grid-cols-2 gap-6 h-64">
                <div class="border border-gray-300 flex flex-col items-center justify-center bg-gray-50 overflow-hidden relative">
                    <div class="absolute top-0 left-0 bg-gray-800 text-white font-bold px-2 py-1 uppercase text-xs w-full text-left z-10">Evidencia</div>
                    <div class="mt-8 flex-1 flex items-center justify-center p-2">
                        <span class='text-gray-400 flex flex-col items-center'><br><br>Sin evidencia fotográfica</span>
                    </div>
                </div>
                <div class="border border-gray-300 flex flex-col relative">
                    <div class="bg-gray-800 text-white font-bold px-2 py-1 uppercase text-xs w-full">Comentarios / Observaciones</div>
                    <div class="p-2 text-sm">{observaciones}</div>
                    <div class="absolute bottom-2 right-2 text-xl font-bold {res_color}">{resultado_str}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html
