#-----------------------------------#
#                                   #
# by Matias Bendel from Crowdstrike #
#                                   #
#-----------------------------------#

import time
import json
from falconpy import QuickScanPro

# Configura tus credenciales
CLIENT_ID = ""
CLIENT_SECRET = ""

# Inicializa el cliente de QuickScanPro
falcon = QuickScanPro(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Ruta del archivo a analizar
archivo = "/Users/mbendel/Desktop/MD5_Utility.exe"
print("Archivo a analizar:", archivo)

# Paso 1: Subir el archivo
print("Subiendo archivo para analizar...")
with open(archivo, "rb") as f:
    upload_response = falcon.upload_file(file=f.read())
    if upload_response["status_code"] != 200:
        print("Error al subir el archivo: ", upload_response)
        exit(1)
print("Subida de archivo exitosa")

# Obtener el SHA256 del archivo subido
sha256 = upload_response["body"]["resources"][0]
sha256_json = json.loads(json.dumps(sha256))
sha256_str = sha256_json['sha256']

# Paso 2: Iniciar el análisis
scan_response = falcon.launch_scan(sha256=sha256_str)
if scan_response["status_code"] != 200:
    print("Error al iniciar el análisis: ", scan_response)
    exit(1)

# Obtener el ID del análisis
scan_id = scan_response["body"]["resources"][0]
scan_id_json = json.loads(json.dumps(scan_id))
scan_id_str = scan_id_json['id']

# Paso 3: Esperar y obtener los resultados
print("Esperando resultados del análisis...")
time.sleep(5) # Espera inicial

# Intentar obtener los resultados varias veces
i=0
for _ in range(3):
    result_response = falcon.get_scan_result(ids=scan_id_str)
    if result_response["status_code"] == 200:
        result = result_response["body"]["resources"][0]
        result_json = json.loads(json.dumps(result))
        result_str = result_json['result']['verdict']
        if not result_str:
            result_str = "unknown"
        print("Veredicto: ", result_str)
        break
    else:
        if i == 0:
            print("Análisis en progreso, esperando...")
        else:
            print(f"Análisis en progreso, esperando... {i*3} segundos")    
        i=i+1
        time.sleep(3)
else:
    print("No se pudo obtener el resultado del análisis después de varios intentos.")
