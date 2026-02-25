#!/usr/bin/env python3
"""
FileVantage Monitor - Single Execution
Ejecuta una sola vez, gestiona paginacion y almacena eventos en archivos log
También envía eventos por syslog
Autor: Matias Bendel
Sink: JSON & Syslog 
"""

import requests
import json
import logging
import logging.handlers
import os
import sys
import argparse
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

# ============================================
# CONFIGURACION
# ============================================

load_dotenv()

CLIENT_ID = os.getenv('CROWDSTRIKE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CROWDSTRIKE_CLIENT_SECRET')
CLOUD_REGION = os.getenv('CROWDSTRIKE_CLOUD_REGION', 'us-2')

# Validar region
if CLOUD_REGION not in ['us-1', 'us-2']:
    print(f"Region invalida: {CLOUD_REGION}. Usa 'us-1' o 'us-2'")
    sys.exit(1)

# Construir BASE_URL segun region
if CLOUD_REGION == 'us-1':
    BASE_URL = "https://api.crowdstrike.com"
else:
    BASE_URL = f"https://api.{CLOUD_REGION}.crowdstrike.com"

QUERY_ENDPOINT = f"{BASE_URL}/filevantage/queries/changes/v3"
DETAILS_ENDPOINT = f"{BASE_URL}/filevantage/entities/changes/v2"
AFTER_TOKEN_FILE = "after-token.txt"
EXECUTION_LOG_FILE = "filevantage.log"
STREAM_LOG_FILE = "filevantage-stream.json"

# Valores por defecto
DEFAULT_LIMIT = 500
MAX_LIMIT = 500
DEFAULT_MAX_BACKUPS = 20
DEFAULT_SYSLOG_HOST = None
DEFAULT_SYSLOG_PORT = 514
DEFAULT_SYSLOG_PROTOCOL = 'UDP'

# ============================================
# ARGUMENTOS DE LINEA DE COMANDOS
# ============================================

def parse_arguments():
    """Parsea argumentos de linea de comandos"""
    parser = argparse.ArgumentParser(
        description='FileVantage Monitor - Monitorea cambios de archivos en CrowdStrike',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python3 filevantage.py                                          # Usa valores por defecto
  python3 filevantage.py --limit 500                              # Usa limite de 500 IDs
  python3 filevantage.py --max-backups 10                         # Mantiene 10 backups
  python3 filevantage.py --syslog-host 192.168.1.100              # Envía a syslog
  python3 filevantage.py --syslog-host 192.168.1.100 --syslog-port 514 --syslog-protocol UDP
  python3 filevantage.py -l 500 -b 30 --syslog-host 192.168.1.100 --syslog-protocol TCP
  python3 filevantage.py --help                                   # Muestra esta ayuda
        """
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=DEFAULT_LIMIT,
        help=f'Maximo numero de IDs por query (default: {DEFAULT_LIMIT}, maximo: {MAX_LIMIT})'
    )
    
    parser.add_argument(
        '--max-backups', '-b',
        type=int,
        default=DEFAULT_MAX_BACKUPS,
        help=f'Numero maximo de backups de logs a mantener (default: {DEFAULT_MAX_BACKUPS})'
    )
    
    parser.add_argument(
        '--syslog-host', '-sh',
        type=str,
        default=DEFAULT_SYSLOG_HOST,
        help='Direccion IP del servidor syslog (opcional)'
    )
    
    parser.add_argument(
        '--syslog-port', '-sp',
        type=int,
        default=DEFAULT_SYSLOG_PORT,
        help=f'Puerto del servidor syslog (default: {DEFAULT_SYSLOG_PORT})'
    )
    
    parser.add_argument(
        '--syslog-protocol', '-sprot',
        type=str,
        choices=['UDP', 'TCP'],
        default=DEFAULT_SYSLOG_PROTOCOL,
        help=f'Protocolo para syslog (default: {DEFAULT_SYSLOG_PROTOCOL})'
    )
    
    return parser.parse_args()

def validate_limit(limit: int) -> int:
    """Valida el limite de IDs"""
    if limit < 1:
        print(f"Error: El limite debe ser mayor a 0")
        sys.exit(1)
    
    if limit > MAX_LIMIT:
        print(f"Error: El limite no puede ser mayor a {MAX_LIMIT}")
        print(f"Se usara el limite maximo: {MAX_LIMIT}")
        return MAX_LIMIT
    
    return limit

def validate_max_backups(max_backups: int) -> int:
    """Valida el numero maximo de backups"""
    if max_backups < 1:
        print(f"Error: El numero de backups debe ser mayor a 0")
        sys.exit(1)
    
    if max_backups > 100:
        print(f"Error: El numero de backups no puede ser mayor a 100")
        print(f"Se usara el maximo: 100")
        return 100
    
    return max_backups

def validate_syslog_port(port: int) -> int:
    """Valida el puerto de syslog"""
    if port < 1 or port > 65535:
        print(f"Error: El puerto debe estar entre 1 y 65535")
        sys.exit(1)
    
    return port

# ============================================
# ROTACION DE LOGS
# ============================================

def rotate_stream_log(stream_log_file: str, max_backups: int) -> None:
    """
    Rota el archivo de stream log
    
    Flujo:
    - filevantage-stream.json → filevantage-stream.001.json
    - filevantage-stream.001.json → filevantage-stream.002.json
    - ...
    - filevantage-stream.020.json → se elimina (si max_backups=20)
    
    Args:
        stream_log_file: Ruta del archivo de stream log
        max_backups: Numero maximo de backups a mantener
    """
    if not os.path.exists(stream_log_file):
        # No hay archivo a rotar
        return
    
    console_logger.info(f"Rotando archivo de stream log...")
    execution_logger.info(f"Rotating stream log file...")
    
    try:
        # Obtener extension del archivo
        base_name, ext = os.path.splitext(stream_log_file)
        
        # Paso 1: Eliminar el archivo mas antiguo si existe
        oldest_backup = f"{base_name}.{max_backups:03d}{ext}"
        if os.path.exists(oldest_backup):
            os.remove(oldest_backup)
            console_logger.info(f"  Eliminado: {oldest_backup}")
            execution_logger.info(f"  Deleted: {oldest_backup}")
        
        # Paso 2: Renombrar archivos de backup en orden inverso
        for i in range(max_backups - 1, 0, -1):
            old_name = f"{base_name}.{i:03d}{ext}"
            new_name = f"{base_name}.{i + 1:03d}{ext}"
            
            if os.path.exists(old_name):
                os.rename(old_name, new_name)
                console_logger.debug(f"  Renombrado: {old_name} → {new_name}")
                execution_logger.debug(f"  Renamed: {old_name} → {new_name}")
        
        # Paso 3: Renombrar el archivo principal a .001
        first_backup = f"{base_name}.001{ext}"
        os.rename(stream_log_file, first_backup)
        console_logger.info(f"  Renombrado: {stream_log_file} → {first_backup}")
        execution_logger.info(f"  Renamed: {stream_log_file} → {first_backup}")
        
        console_logger.info(f"Rotacion completada")
        execution_logger.info(f"Rotation completed")
        
    except Exception as e:
        console_logger.error(f"Error al rotar archivo de stream log: {e}")
        execution_logger.error(f"Error rotating stream log file: {e}")

# ============================================
# LOGGING - ARCHIVO DE EJECUCION
# ============================================

def setup_execution_logger():
    """Configura logger para ejecucion del script"""
    logger = logging.getLogger('filevantage_execution')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    log_dir = os.path.dirname(EXECUTION_LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    file_handler = logging.FileHandler(EXECUTION_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def setup_console_logger():
    """Configura logger para consola"""
    logger = logging.getLogger('filevantage_console')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def setup_stream_log_logger():
    """Configura logger para respuestas de la segunda query"""
    logger = logging.getLogger('filevantage_stream')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    log_dir = os.path.dirname(STREAM_LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    file_handler = logging.FileHandler(STREAM_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def setup_syslog_logger(syslog_host: str, syslog_port: int, syslog_protocol: str):
    """
    Configura logger para enviar a syslog remoto
    
    Args:
        syslog_host: Dirección IP del servidor syslog
        syslog_port: Puerto del servidor syslog
        syslog_protocol: Protocolo (UDP o TCP)
    """
    logger = logging.getLogger('filevantage_syslog')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    try:
        # Determinar tipo de socket según protocolo
        if syslog_protocol.upper() == 'TCP':
            handler = logging.handlers.SysLogHandler(
                address=(syslog_host, syslog_port),
                facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
                socktype=__import__('socket').SOCK_STREAM
            )
            console_logger.info(f"Syslog configurado: TCP://{syslog_host}:{syslog_port}")
            execution_logger.info(f"Syslog configured: TCP://{syslog_host}:{syslog_port}")
        else:  # UDP
            handler = logging.handlers.SysLogHandler(
                address=(syslog_host, syslog_port),
                facility=logging.handlers.SysLogHandler.LOG_LOCAL0
            )
            console_logger.info(f"Syslog configurado: UDP://{syslog_host}:{syslog_port}")
            execution_logger.info(f"Syslog configured: UDP://{syslog_host}:{syslog_port}")
        
        # Formato para syslog
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    except Exception as e:
        console_logger.error(f"Error al configurar syslog: {e}")
        execution_logger.error(f"Error configuring syslog: {e}")
        return None

# Inicializar loggers
execution_logger = setup_execution_logger()
console_logger = setup_console_logger()
stream_logger = setup_stream_log_logger()
syslog_logger = None  # Se inicializa en la clase si es necesario

# ============================================
# CLASE PRINCIPAL
# ============================================

class FileVantageMonitor:
    def __init__(self, client_id: str, client_secret: str, cloud_region: str, limit: int, 
                 max_backups: int, syslog_host: Optional[str] = None, syslog_port: int = 514,
                 syslog_protocol: str = 'UDP'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cloud_region = cloud_region
        self.limit = limit
        self.max_backups = max_backups
        self.syslog_host = syslog_host
        self.syslog_port = syslog_port
        self.syslog_protocol = syslog_protocol
        self.token = None
        self.token_expiry = 0
        self.syslog_logger = None
        
    def get_auth_token(self) -> str:
        """Obtiene token de autenticacion"""
        try:
            auth_url = f"{BASE_URL}/oauth2/token"
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                auth_url,
                data=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data['access_token']
            
            console_logger.info(f"Token de autenticacion obtenido (Region: {self.cloud_region})")
            execution_logger.info(f"Authentication successful - Region: {self.cloud_region}")
            return self.token
            
        except requests.exceptions.RequestException as e:
            console_logger.error(f"Error al obtener token: {e}")
            execution_logger.error(f"Authentication failed: {e}")
            raise
    
    def get_headers(self) -> Dict:
        """Retorna headers con autenticacion"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def check_after_token_file(self) -> Optional[str]:
        """Verifica si existe el archivo after-token.txt"""
        if os.path.exists(AFTER_TOKEN_FILE):
            try:
                with open(AFTER_TOKEN_FILE, 'r') as f:
                    token = f.read().strip()
                    if token:
                        console_logger.info(f"Token 'after' encontrado: {token[:30]}...")
                        execution_logger.info(f"After token loaded: {token[:30]}...")
                        return token
            except Exception as e:
                console_logger.error(f"Error al leer {AFTER_TOKEN_FILE}: {e}")
                execution_logger.error(f"Error reading after-token file: {e}")
                return None
        else:
            console_logger.warning(f"Archivo '{AFTER_TOKEN_FILE}' no encontrado")
            response = input("Deseas comenzar desde el inicio? (s/n): ").strip().lower()
            
            if response == 's':
                console_logger.info("Iniciando desde el principio")
                execution_logger.info("Starting extraction from beginning")
                try:
                    with open(AFTER_TOKEN_FILE, 'w') as f:
                        f.write("")
                    return None
                except Exception as e:
                    console_logger.error(f"Error al crear {AFTER_TOKEN_FILE}: {e}")
                    execution_logger.error(f"Error creating after-token file: {e}")
                    sys.exit(1)
            else:
                console_logger.info("Operacion cancelada")
                execution_logger.info("Operation cancelled by user")
                sys.exit(0)
    
    def save_after_token(self, token: str) -> None:
        """Guarda el token 'after' en archivo"""
        try:
            with open(AFTER_TOKEN_FILE, 'w') as f:
                f.write(token)
            console_logger.info(f"Token 'after' guardado: {token[:30]}...")
            execution_logger.info(f"After token saved: {token[:30]}...")
        except Exception as e:
            console_logger.error(f"Error al guardar token: {e}")
            execution_logger.error(f"Error saving after token: {e}")
    
    def query_changes_single(self, after_token: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
        """Realiza una UNICA consulta a la primera API"""
        try:
            console_logger.info(f"Consultando cambios (limite: {self.limit})...")
            execution_logger.info(f"Querying changes (limit: {self.limit})")
            
            params = {
                'limit': self.limit,
                'sort': 'action_timestamp|asc'
            }
            
            if after_token:
                params['after'] = after_token
                console_logger.info(f"  Usando after token: {after_token[:30]}...")
                execution_logger.info(f"  Using after token: {after_token[:30]}...")
            else:
                console_logger.info(f"  Primera consulta (sin after token)")
                execution_logger.info(f"  First query (no after token)")
            
            response = requests.get(
                QUERY_ENDPOINT,
                headers=self.get_headers(),
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            change_ids = data.get('resources', [])
            errors = data.get('errors', [])
            
            next_after_token = data.get('meta', {}).get('pagination', {}).get('after')
            
            pagination_info = data.get('meta', {}).get('pagination', {})
            total_results = pagination_info.get('total', 'N/A')
            
            if errors:
                console_logger.warning(f"Errores en respuesta: {errors}")
                execution_logger.warning(f"API errors: {errors}")
            
            console_logger.info(f"  Obtenidos {len(change_ids)} IDs")
            console_logger.info(f"  Total de resultados disponibles: {total_results}")
            execution_logger.info(f"Retrieved {len(change_ids)} IDs")
            execution_logger.info(f"Total results available: {total_results}")
            
            return change_ids, next_after_token
            
        except requests.exceptions.RequestException as e:
            console_logger.error(f"Error al consultar cambios: {e}")
            execution_logger.error(f"Query changes failed: {e}")
            return [], None
    
    def get_change_details_batch(self, change_ids: List[str]) -> List[Dict]:
        """Obtiene detalles de multiples cambios en una sola llamada"""
        if not change_ids:
            return []
        
        try:
            params = []
            for change_id in change_ids:
                params.append(('ids', change_id))
            
            console_logger.info(f"  Obteniendo detalles de {len(change_ids)} cambios...")
            execution_logger.info(f"  Fetching details for {len(change_ids)} changes")
            
            response = requests.get(
                DETAILS_ENDPOINT,
                headers=self.get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            changes = data.get('resources', [])
            errors = data.get('errors', [])
            
            if errors:
                console_logger.warning(f"  Errores en respuesta: {errors}")
                execution_logger.warning(f"  API errors: {errors}")
            
            console_logger.info(f"  Obtenidos detalles de {len(changes)} cambios")
            execution_logger.info(f"  Retrieved details for {len(changes)} changes")
            
            return changes
            
        except requests.exceptions.RequestException as e:
            console_logger.error(f"  Error al obtener detalles: {e}")
            execution_logger.error(f"  Failed to get details: {e}")
            return []
    
    def log_change_to_stream(self, change_detail: Dict) -> None:
        """Registra detalles del cambio en archivo stream (JSON)"""
        try:
            json_message = json.dumps(change_detail, ensure_ascii=False)
            stream_logger.info(json_message)
            
        except Exception as e:
            console_logger.error(f"Error al registrar en stream: {e}")
            execution_logger.error(f"Failed to log change to stream: {e}")
    
    def log_change_to_syslog(self, change_detail: Dict) -> None:
        """Registra detalles del cambio en syslog remoto"""
        if not self.syslog_logger:
            return
        
        try:
            json_message = json.dumps(change_detail, ensure_ascii=False)
            self.syslog_logger.info(json_message)
            
        except Exception as e:
            console_logger.error(f"Error al registrar en syslog: {e}")
            execution_logger.error(f"Failed to log change to syslog: {e}")
    
    def run(self) -> None:
        """Ejecuta el proceso completo"""
        console_logger.info("=" * 70)
        console_logger.info("FileVantage Monitor (Single Execution)")
        console_logger.info(f"Region: {self.cloud_region}")
        console_logger.info(f"Base URL: {BASE_URL}")
        console_logger.info(f"Limite de IDs por query: {self.limit}")
        console_logger.info(f"Maximo de backups: {self.max_backups}")
        if self.syslog_host:
            console_logger.info(f"Syslog: {self.syslog_protocol}://{self.syslog_host}:{self.syslog_port}")
        console_logger.info("=" * 70)
        
        execution_logger.info("=" * 70)
        execution_logger.info("FileVantage Monitor Started")
        execution_logger.info(f"Region: {self.cloud_region}")
        execution_logger.info(f"Base URL: {BASE_URL}")
        execution_logger.info(f"ID limit per query: {self.limit}")
        execution_logger.info(f"Max backups: {self.max_backups}")
        if self.syslog_host:
            execution_logger.info(f"Syslog: {self.syslog_protocol}://{self.syslog_host}:{self.syslog_port}")
        execution_logger.info("=" * 70)
        
        try:
            if not CLIENT_ID or not CLIENT_SECRET:
                console_logger.error("Falta configurar credenciales en .env")
                execution_logger.error("Missing credentials in .env")
                sys.exit(1)
            
            # Configurar syslog si se proporciona host
            if self.syslog_host:
                self.syslog_logger = setup_syslog_logger(
                    self.syslog_host,
                    self.syslog_port,
                    self.syslog_protocol
                )
                if not self.syslog_logger:
                    console_logger.warning("No se pudo configurar syslog, continuando sin él")
                    execution_logger.warning("Failed to configure syslog, continuing without it")
            
            # PASO 0: Rotar archivo de stream log antes de comenzar
            console_logger.info("Verificando rotacion de logs...")
            execution_logger.info("Checking log rotation...")
            rotate_stream_log(STREAM_LOG_FILE, self.max_backups)
            
            self.get_auth_token()
            
            after_token = self.check_after_token_file()
            
            total_processed = 0
            total_errors = 0
            iteration = 0
            current_after = after_token
            
            while True:
                iteration += 1
                console_logger.info(f"\n--- Iteracion {iteration} ---")
                execution_logger.info(f"\n--- Iteration {iteration} ---")
                
                # PASO 1: Consultar primera API
                console_logger.info("PASO 1: Consultando IDs desde primera API...")
                execution_logger.info("STEP 1: Querying IDs from first API...")
                
                change_ids, next_after_token = self.query_changes_single(current_after)
                
                if not change_ids:
                    console_logger.info("No hay nuevos cambios")
                    execution_logger.info("No new changes detected")
                    break
                
                console_logger.info(f"Obtenidos {len(change_ids)} IDs")
                execution_logger.info(f"Retrieved {len(change_ids)} IDs")
                
                # PASO 2: Consultar segunda API con esos IDs
                console_logger.info("PASO 2: Consultando detalles desde segunda API...")
                execution_logger.info("STEP 2: Querying details from second API...")
                
                changes = self.get_change_details_batch(change_ids)
                
                if not changes:
                    console_logger.error("No se pudieron obtener detalles de los cambios")
                    execution_logger.error("Failed to retrieve change details")
                    break
                
                # PASO 3: Registrar detalles en stream Y syslog
                console_logger.info("PASO 3: Registrando detalles en stream y syslog...")
                execution_logger.info("STEP 3: Logging details to stream and syslog...")
                
                processed_count = 0
                error_count = 0
                
                for idx, change_detail in enumerate(changes, 1):
                    try:
                        # Registrar en archivo JSON
                        self.log_change_to_stream(change_detail)
                        
                        # Registrar en syslog (si está configurado)
                        if self.syslog_logger:
                            self.log_change_to_syslog(change_detail)
                        
                        processed_count += 1
                    except Exception as e:
                        console_logger.error(f"Error procesando cambio {idx}: {e}")
                        error_count += 1
                
                total_processed += processed_count
                total_errors += error_count
                
                console_logger.info(f"Registrados {processed_count} cambios en esta iteracion")
                execution_logger.info(f"Logged {processed_count} changes in this iteration")
                
                # PASO 4: Verificar si hay mas IDs
                if len(change_ids) < self.limit:
                    console_logger.info(f"Paginacion completada. Se obtuvieron {len(change_ids)} IDs (menos de {self.limit})")
                    execution_logger.info(f"Pagination completed. Retrieved {len(change_ids)} IDs (less than {self.limit})")
                    break
                
                if len(change_ids) == self.limit:
                    if next_after_token:
                        console_logger.info(f"Hay mas IDs disponibles. Guardando token y continuando...")
                        execution_logger.info(f"More IDs available. Saving token and continuing...")
                        self.save_after_token(next_after_token)
                        current_after = next_after_token
                    else:
                        console_logger.info(f"Se obtuvieron {len(change_ids)} IDs pero no hay token 'after'")
                        execution_logger.info(f"Retrieved {len(change_ids)} IDs but no 'after' token")
                        break
            
            console_logger.info("\n" + "=" * 70)
            console_logger.info(f"Total procesados: {total_processed}")
            console_logger.info(f"Total errores: {total_errors}")
            console_logger.info(f"Execution Log: {os.path.abspath(EXECUTION_LOG_FILE)}")
            console_logger.info(f"Stream Log: {os.path.abspath(STREAM_LOG_FILE)}")
            if self.syslog_host:
                console_logger.info(f"Syslog: {self.syslog_protocol}://{self.syslog_host}:{self.syslog_port}")
            console_logger.info("=" * 70)
            
            execution_logger.info("=" * 70)
            execution_logger.info(f"Execution completed: {total_processed} processed, {total_errors} errors")
            execution_logger.info("=" * 70)
            
        except Exception as e:
            console_logger.error(f"Error fatal: {e}")
            execution_logger.error(f"Fatal error: {e}")
            sys.exit(1)

# ============================================
# EJECUCION
# ============================================

if __name__ == "__main__":
    # Parsear argumentos
    args = parse_arguments()
    
    # Validar parametros
    limit = validate_limit(args.limit)
    max_backups = validate_max_backups(args.max_backups)
    syslog_port = validate_syslog_port(args.syslog_port)
    
    # Crear y ejecutar monitor
    monitor = FileVantageMonitor(
        CLIENT_ID,
        CLIENT_SECRET,
        CLOUD_REGION,
        limit,
        max_backups,
        args.syslog_host,
        syslog_port,
        args.syslog_protocol
    )
    monitor.run()
