# core/constants.py
"""
Diccionarios y constantes normativas ESD (ANSI/ESD S20.20 / ANSI/ESD TR53 / IEC 61340-5-1)
Extraídos y enriquecidos del sistema base para validación de resistencia, voltaje y frecuencias.
"""

INFO_ELEMENTOS_ESD = {
    "Pulsera antiestática": {
        "limite": "RS < 3.5x10^7 ohms",
        "ref_num": 3.5e7,
        "tipo_material": "Banda elástica / Metal",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Calzado": {
        "limite": "RS < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Suela disipativa / Talón",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Piso ESD": {
        "limite": "RTG < 1.0x10^9 ohms / Walking Test < 100V",
        "ref_num": 1.0e9,
        "tipo_material": "Epóxico / Vinílico ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53 / ANSI/ESD 97.2",
        "frecuencia": "Semestralmente"
    },
    "Superficie de trabajo": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Tapete disipativo / Mesa",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Anualmente"
    },
    "Monitor Continuo": {
        "limite": "RTG < 2 ohms",
        "ref_num": 2.0,
        "tipo_material": "Equipo Electrónico",
        "magnitud": "Resistencia",
        "metodo": "Anexo A.1",
        "frecuencia": "Trimestralmente"
    },
    "Ionizador": {
        "limite": "Descarga: <10s, Bal: +-35V",
        "ref_num": 10.0,
        "tipo_material": "Ventilador / Barra",
        "magnitud": "Tiempo",
        "metodo": "ANSI/ESD SP3.3-2016",
        "frecuencia": "Trimestralmente"
    },
    "Bolsa disipativa": {
        "limite": "RS < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Plástico disipativo",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.11",
        "frecuencia": "Semestralmente"
    },
    "Cautín / Estación de soldar": {
        "limite": "RTG < 10 ohms",
        "ref_num": 10.0,
        "tipo_material": "Metal / Punta",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Caja Disipativa": {
        "limite": "RS < 1.0x10^11 ohms",
        "ref_num": 1.0e11,
        "tipo_material": "Plástico / Cartón",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.11",
        "frecuencia": "Anualmente"
    },
    "Caja conductiva": {
        "limite": "RS < 1.0x10^4 ohms",
        "ref_num": 1.0e4,
        "tipo_material": "Plástico conductivo",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.11",
        "frecuencia": "Anualmente"
    },
    "Charola conductiva": {
        "limite": "RS < 1.0x10^4 ohms",
        "ref_num": 1.0e4,
        "tipo_material": "Plástico conductivo",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.13/11.11",
        "frecuencia": "Anualmente"
    },
    "Charola Disipativa": {
        "limite": "RS < 1.0x10^11 ohms",
        "ref_num": 1.0e11,
        "tipo_material": "Plástico disipativo",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.13/11.11",
        "frecuencia": "Anualmente"
    },
    "Magazine": {
        "limite": "RS < 1.0x10^11 ohms",
        "ref_num": 1.0e11,
        "tipo_material": "Metal / Plástico",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM11.13/11.11",
        "frecuencia": "Anualmente"
    },
    "Bata": {
        "limite": "RPP < 1.0x10^11 ohms",
        "ref_num": 1.0e11,
        "tipo_material": "Tela ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Gorra": {
        "limite": "RPP < 1.0x10^11 ohms",
        "ref_num": 1.0e11,
        "tipo_material": "Tela ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Rack": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Metal",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM4.1",
        "frecuencia": "Anualmente"
    },
    "Carrito": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Metal",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD STM4.1",
        "frecuencia": "Anualmente"
    },
    "Silla ESD": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Tela / Vinil ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Guantes Nitrilo": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Nitrilo",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Guantes Tela": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Tela ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Tapete de piso": {
        "limite": "RTG < 1.0x10^9 ohms",
        "ref_num": 1.0e9,
        "tipo_material": "Caucho / Vinil ESD",
        "magnitud": "Resistencia",
        "metodo": "ANSI/ESD TR53",
        "frecuencia": "Semestralmente"
    },
    "Aislantes - EPA (General)": {
        "limite": ">30 cm de ESDS",
        "ref_num": 2000.0,
        "tipo_material": "Material Aislante",
        "magnitud": "Voltaje",
        "metodo": "Anexo A.2",
        "frecuencia": "Semestralmente"
    },
    "Aislantes - Conductores Aislados": {
        "limite": "< 35 Volts",
        "ref_num": 35.0,
        "tipo_material": "Conductor Aislado",
        "magnitud": "Voltaje",
        "metodo": "Anexo A.2",
        "frecuencia": "Semestralmente"
    },
    "Aislantes - Contacto directo": {
        "limite": "<= 125 Volts/in",
        "ref_num": 125.0,
        "tipo_material": "Material Aislante",
        "magnitud": "Voltaje",
        "metodo": "Anexo A.2",
        "frecuencia": "Semestralmente"
    },
    "Bolsas blindadas": {
        "limite": "Visual",
        "ref_num": 0.0,
        "tipo_material": "Plástico metalizado",
        "magnitud": "Otro",
        "metodo": "Inspección visual",
        "frecuencia": "Trimestralmente"
    }
}

MAPA_UNIDADES = {
    "Resistencia": "Ohms",
    "Voltaje": "Volts",
    "Tiempo": "Segundos",
    "Longitud": "cm",
    "Otro": "N/A"
}

def parsear_resistencia(valor_str):
    """Convierte texto libre a float soportando notación científica y comas."""
    if not valor_str or str(valor_str).strip() == "":
        return None
    try:
        val_limpio = str(valor_str).strip().replace(',', '.')
        return float(val_limpio)
    except ValueError:
        return "ERROR"
