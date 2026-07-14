# core/reports.py
from datetime import datetime

def generar_html_reporte_linea(linea, df_linea, auditor, comentarios, db_id):
    """
    Genera la plantilla HTML interactiva para el reporte de validación de línea (ESD)
    que el usuario puede descargar e imprimir en PDF.
    """
    año_actual = datetime.today().strftime("%y")
    fecha_hoy = datetime.today().strftime("%d-%b-%Y")
    fecha_pie = datetime.today().strftime("%Y/%m/%d")
    
    # Construir las filas de la tabla
    filas_html = ""
    for i, row in enumerate(df_linea.to_dict('records'), 1):
        categoria = str(row.get('Categoría', 'N/D'))
        id_elem = str(row.get('ID / Nombre', 'N/D'))
        clasif = str(row.get('Clasificación', 'N/D'))
        ultima_val = str(row.get('Última Medición', 'N/D'))
        vencimiento = str(row.get('Próximo Vencimiento', 'N/D'))
        estatus_raw = str(row.get('Estatus', '')).upper()
        
        # Limpiar el emoji si existe
        estatus_limpio = estatus_raw.replace('🟢', '').replace('🔴', '').replace('🟡', '').strip()
        color_txt = "text-green-600" if "VIGENTE" in estatus_limpio or "PASA" in estatus_limpio else ("text-red-600" if "VENCIDO" in estatus_limpio or "FALLA" in estatus_limpio else "text-yellow-600")
        
        filas_html += f"""
        <tr class="text-center border-b border-gray-300 print:border-black">
            <td class="border-r border-gray-300 p-2 print:border-black">{i}</td>
            <td class="border-r border-gray-300 p-2 font-bold text-left print:border-black">{id_elem}</td>
            <td class="border-r border-gray-300 p-2 text-left print:border-black">{categoria} - {clasif}</td>
            <td class="border-r border-gray-300 p-2 font-mono text-gray-700 print:border-black">{ultima_val}</td>
            <td class="border-r border-gray-300 p-2 font-mono print:border-black">{vencimiento}</td>
            <td class="p-2 font-bold {color_txt}">{estatus_limpio}</td>
        </tr>
        """
        
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BCS-LV-{db_id:03d}-{año_actual}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>@media print {{ body {{ -webkit-print-color-adjust: exact; }} }}</style>
</head>
<body class="bg-gray-100 p-4 md:p-8 font-sans text-sm print:bg-white print:p-0">
    <div class="max-w-5xl mx-auto mb-6 bg-white p-4 rounded-lg shadow flex justify-end print:hidden">
        <button onclick="window.print()" class="bg-blue-600 text-white px-6 py-2 rounded font-bold shadow-sm">🖨️ Imprimir / Guardar PDF</button>
    </div>
    <div class="max-w-5xl mx-auto bg-white shadow-xl print:shadow-none print:w-full print:border print:border-black">
        <div class="border-b-2 border-gray-800 p-6 flex items-start justify-between print:border-black">
            <div class="w-1/3">
                <img src="https://github.com/aldoaoa/Visualizador-BCS-IDS/blob/main/BCS%20LOGO.png?raw=true" alt="BCS Logo" class="h-16 object-contain" />
            </div>
            <div class="w-1/3 text-center">
                <h1 class="text-lg font-bold text-gray-800">REPORTE DE VALIDACIÓN DE LÍNEA (ESD)</h1>
                <p class="text-xs text-gray-600">Cumplimiento Integral ANSI/ESD S20.20</p>
            </div>
            <div class="w-1/3 text-right text-sm">
                <div class="font-bold text-red-700 text-lg mb-2">Folio: BCS-LV-{db_id:03d}-{año_actual}</div>
                <div class="flex justify-end gap-2 mb-1">
                    <span class="font-bold">Fecha de Emisión:</span><span>{fecha_hoy}</span>
                </div>
            </div>
        </div>

        <div class="p-6 space-y-6">
            <div class="bg-gray-100 p-4 border border-gray-300 rounded print:border-black print:bg-transparent">
                <div class="grid grid-cols-2 gap-4">
                    <div><span class="font-bold text-[#003366]">Línea Evaluada:</span> <span class="text-lg font-bold">{linea}</span></div>
                    <div><span class="font-bold text-[#003366]">Auditor Responsable:</span> {auditor}</div>
                </div>
            </div>

            <div>
                <div class="bg-[#003366] text-white font-bold px-2 py-1 uppercase text-xs print:bg-black">Desglose de Activos Operativos en Línea</div>
                <table class="w-full text-sm border-collapse border border-gray-300 print:border-black">
                    <tr class="bg-gray-200 border-b border-gray-300 print:bg-transparent print:border-black">
                        <th class="p-2 border-r border-gray-300 print:border-black w-10">No.</th>
                        <th class="p-2 border-r border-gray-300 print:border-black text-left">ID Elemento</th>
                        <th class="p-2 border-r border-gray-300 print:border-black text-left">Tipo de Equipo</th>
                        <th class="p-2 border-r border-gray-300 print:border-black">Última Validación</th>
                        <th class="p-2 border-r border-gray-300 print:border-black">Próx. Vencimiento</th>
                        <th class="p-2">Estatus Actual</th>
                    </tr>
                    {filas_html}
                </table>
            </div>

            <div class="mt-4 border border-gray-300 p-3 bg-gray-50 print:border-black print:bg-transparent">
                <div class="font-bold text-[#003366] text-xs uppercase mb-1 print:text-black">Comentarios / Observaciones de la Línea:</div>
                <div class="text-sm">{comentarios}</div>
            </div>

            <div class="mt-16 mb-8 pt-8 [page-break-inside:avoid]">
                <div class="w-1/2 mx-auto text-center border-t-2 border-gray-800 pt-2 print:border-black">
                    <div class="font-bold uppercase text-sm mb-1">CERTIFICADO POR:</div>
                    <div class="text-center font-bold text-gray-700 print:text-black">{auditor}</div>
                    <div class="text-xs text-gray-500">Coordinador ESD</div>
                </div>
            </div>
            
            <div class="border-t-[3px] border-b-[3px] border-black mt-16 py-1 text-[11px] font-sans [page-break-inside:avoid]">
                <div class="flex justify-between items-end">
                    <div class="text-left leading-tight">
                        <div>B_010_4_013_QRO_SP Rev. A</div>
                        <div>Registro de eventos ESD.</div>
                    </div>
                    <div class="text-center leading-tight">
                        <div>Fecha: {fecha_pie}</div>
                    </div>
                    <div class="text-right leading-tight">
                        <div>Ref.B_010_3_002_QRO_SP</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html, año_actual
