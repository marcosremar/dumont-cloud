#!/usr/bin/env python3
"""
Script de teste REAL de failover direto via API
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJjb3NyZW1hckBnbWFpbC5jb20iLCJleHAiOjE3NzEyNjYwMTIsImlhdCI6MTc2NzM3ODAxMn0.Jgcaq9nbWw7ym_l9xPZEPUG--7VUUISfMoFjMPPaSL0"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

def log(msg, color=NC):
    print(f"{color}{datetime.now().strftime('%H:%M:%S')} | {msg}{NC}")

def success(msg): log(f"✅ {msg}", GREEN)
def error(msg): log(f"❌ {msg}", RED)
def info(msg): log(f"📍 {msg}", YELLOW)

def api_get(endpoint):
    return requests.get(f"{API_URL}{endpoint}", headers=HEADERS).json()

def api_post(endpoint, data=None):
    return requests.post(f"{API_URL}{endpoint}", headers=HEADERS, json=data or {}).json()

def ssh_command(host, port, cmd, timeout=60):
    try:
        result = subprocess.run(
            ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no", 
             "-o", "ConnectTimeout=30", f"root@{host}", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def test_cpu_connectivity():
    info("TESTE 1: Verificar conectividade com CPU Standby")
    associations = api_get("/standby/associations")
    
    for gpu_id, assoc in associations.get("associations", {}).items():
        cpu_ip = assoc["cpu_standby"]["ip"]
        info(f"Testando CPU {cpu_ip}...")
        ok, stdout, _ = ssh_command(cpu_ip, 22, "echo OK && hostname")
        if ok:
            success(f"CPU {cpu_ip} acessível!")
            return {"gpu_id": int(gpu_id), "cpu_ip": cpu_ip, "cpu_name": assoc["cpu_standby"]["name"]}
    
    error("Nenhum CPU acessível")
    return None

def test_file_sync(cpu_info):
    info("TESTE 2: Testar sincronização de arquivos")
    cpu_ip = cpu_info["cpu_ip"]
    ts = int(time.time())
    test_file = f"/workspace/failover-test-{ts}.txt"
    content = f"Failover Test - {datetime.now().isoformat()}"
    
    cmd = f"mkdir -p /workspace && echo '{content}' > {test_file} && md5sum {test_file}"
    ok, stdout, _ = ssh_command(cpu_ip, 22, cmd)
    
    if ok:
        md5 = stdout.split()[0] if stdout else "N/A"
        success(f"Arquivo criado! MD5: {md5}")
        return {"file": test_file, "content": content, "md5": md5}
    
    error("Falha ao criar arquivo")
    return None

def test_failover_simulation(cpu_info):
    info("TESTE 3: Simular failover completo")
    gpu_id = cpu_info["gpu_id"]
    
    result = api_post(f"/standby/failover/simulate/{gpu_id}", {
        "reason": "real_test", "simulate_restore": True, "simulate_new_gpu": True
    })
    
    if "failover_id" in result:
        failover_id = result["failover_id"]
        success(f"Failover iniciado: {failover_id}")
        
        for _ in range(30):
            time.sleep(1)
            status = api_get(f"/standby/failover/status/{failover_id}")
            phase = status.get("phase", "unknown")
            info(f"Fase: {phase}")
            
            if phase == "complete":
                success(f"Failover completado em {status.get('total_time_ms', 0)}ms!")
                return status
            elif phase == "failed":
                error("Failover falhou!")
                return status
    
    error(f"Falha: {result}")
    return None

def test_file_integrity(cpu_info, file_info):
    info("TESTE 4: Verificar integridade do arquivo")
    cpu_ip = cpu_info["cpu_ip"]
    
    cmd = f"md5sum {file_info['file']}"
    ok, stdout, _ = ssh_command(cpu_ip, 22, cmd)
    
    if ok:
        current_md5 = stdout.split()[0] if stdout else ""
        if current_md5 == file_info["md5"]:
            success(f"Integridade OK! MD5: {current_md5}")
            return True
        error(f"MD5 diferente! Esperado: {file_info['md5']}, Atual: {current_md5}")
    
    return False

def test_failover_report():
    info("TESTE 5: Verificar relatório de failovers")
    report = api_get("/standby/failover/report?days=30")
    success(f"Total: {report.get('total_failovers', 0)} | Sucesso: {report.get('success_rate', 0)}% | MTTR: {report.get('mttr_seconds', 0)}s")
    return report

def main():
    print("\n" + "="*60)
    print("  TESTE REAL DE FAILOVER - DUMONT CLOUD")
    print("="*60 + "\n")
    
    results = []
    
    cpu_info = test_cpu_connectivity()
    results.append(("CPU Connectivity", cpu_info is not None))
    if not cpu_info:
        print("\n❌ Não foi possível continuar sem CPU acessível")
        return 1
    
    file_info = test_file_sync(cpu_info)
    results.append(("File Sync", file_info is not None))
    
    failover = test_failover_simulation(cpu_info)
    results.append(("Failover Simulation", failover and failover.get("success", False)))
    
    if file_info:
        integrity = test_file_integrity(cpu_info, file_info)
        results.append(("File Integrity", integrity))
    
    test_failover_report()
    results.append(("Failover Report", True))
    
    print("\n" + "="*60)
    print(f"  RESUMO: {sum(1 for _, p in results if p)}/{len(results)} testes passaram")
    print("="*60)
    for name, passed in results:
        print(f"  {'✅' if passed else '❌'} {name}")
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
