"""
Service para operacoes com Restic (backup/restore)
"""
import subprocess
import json
import os
from typing import List, Dict, Any, Optional
from collections import defaultdict


class ResticService:
    """Service para gerenciar backups/restores com Restic"""

    def __init__(
        self,
        repo: str,
        password: str,
        access_key: str,
        secret_key: str,
        connections: int = 32,
    ):
        self.repo = repo
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        self.connections = connections

    def _get_env(self) -> Dict[str, str]:
        """Retorna variaveis de ambiente para o restic"""
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = self.access_key
        env["AWS_SECRET_ACCESS_KEY"] = self.secret_key
        env["RESTIC_PASSWORD"] = self.password
        env["RESTIC_REPOSITORY"] = self.repo
        return env

    def list_snapshots(self, deduplicate: bool = True) -> Dict[str, Any]:
        """Lista snapshots do repositorio"""
        try:
            result = subprocess.run(
                ["restic", "snapshots", "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": result.stderr, "snapshots": [], "deduplicated": []}

            snapshots = json.loads(result.stdout) if result.stdout else []
            formatted = []

            for s in snapshots:
                formatted.append({
                    "id": s.get("id", ""),
                    "short_id": s.get("id", "")[:8],
                    "time": s.get("time", "")[:19].replace("T", " "),
                    "hostname": s.get("hostname", ""),
                    "tags": s.get("tags", []),
                    "paths": s.get("paths", []),
                    "tree": s.get("tree", ""),
                    "parent": s.get("parent", ""),
                })

            # Ordenar por data (mais recente primeiro)
            formatted.sort(key=lambda x: x["time"], reverse=True)

            if not deduplicate:
                return {"snapshots": formatted, "deduplicated": formatted}

            # Deduplicar por tree hash - manter apenas o mais recente de cada
            tree_groups = defaultdict(list)
            for s in formatted:
                tree_groups[s["tree"]].append(s)

            deduplicated = []
            for tree_hash, group in tree_groups.items():
                most_recent = group[0]
                most_recent["version_count"] = len(group) - 1
                deduplicated.append(most_recent)

            deduplicated.sort(key=lambda x: x["time"], reverse=True)

            return {"snapshots": formatted, "deduplicated": deduplicated}

        except Exception as e:
            return {"error": str(e), "snapshots": [], "deduplicated": []}

    def get_snapshot_folders(self, snapshot_id: str) -> List[Dict[str, Any]]:
        """Lista pastas principais de um snapshot"""
        try:
            result = subprocess.run(
                ["restic", "ls", snapshot_id, "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=60,
            )

            if result.returncode != 0:
                return []

            folders = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if item.get("type") == "dir":
                        path = item.get("path", "")
                        # Apenas pastas do primeiro nivel
                        parts = path.strip("/").split("/")
                        if len(parts) <= 2:
                            folders.append({
                                "name": parts[-1] if parts else "",
                                "path": path,
                                "size": item.get("size", 0),
                            })
                except json.JSONDecodeError:
                    continue

            return folders

        except Exception as e:
            return []

    def restore(
        self,
        snapshot_id: str,
        target_path: str,
        ssh_host: str,
        ssh_port: int,
    ) -> Dict[str, Any]:
        """Executa restore em uma maquina remota via SSH"""
        cmd = f"""
export AWS_ACCESS_KEY_ID="{self.access_key}"
export AWS_SECRET_ACCESS_KEY="{self.secret_key}"
export RESTIC_REPOSITORY="{self.repo}"
export RESTIC_PASSWORD="{self.password}"
mkdir -p {target_path}
restic restore {snapshot_id} --target {target_path} -o s3.connections={self.connections} 2>&1
echo "RESTORE_COMPLETED"
du -sh {target_path}/* 2>/dev/null | head -5
"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=30",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos max
            )

            success = "RESTORE_COMPLETED" in result.stdout

            return {
                "success": success,
                "output": result.stdout,
                "error": result.stderr if not success else None,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Restore timeout (5 minutos)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_snapshot_tree(self, snapshot_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Lista arvore de arquivos de um snapshot"""
        try:
            result = subprocess.run(
                ["restic", "ls", snapshot_id, "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=120,
            )

            if result.returncode != 0:
                return []

            # Build tree structure
            all_items = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    path = item.get("path", "")
                    parts = path.strip("/").split("/")
                    depth = len(parts)

                    # Limitar profundidade
                    if depth > max_depth + 1:  # +1 porque o primeiro nivel e o root
                        continue

                    all_items.append({
                        "name": parts[-1] if parts else "",
                        "path": path,
                        "type": item.get("type", "file"),
                        "size": item.get("size", 0),
                        "mtime": item.get("mtime", "")[:19].replace("T", " ") if item.get("mtime") else "",
                        "depth": depth,
                        "parts": parts,
                    })
                except json.JSONDecodeError:
                    continue

            # Build hierarchical tree
            def build_tree(items, parent_path="", current_depth=1):
                tree = []
                # Group items by their immediate parent
                children = {}
                for item in items:
                    if item["depth"] == current_depth:
                        item_path = item["path"]
                        if parent_path == "" or item_path.startswith(parent_path + "/"):
                            children[item_path] = {
                                "name": item["name"],
                                "path": item["path"],
                                "type": item["type"],
                                "size": item["size"],
                                "mtime": item["mtime"],
                                "children": []
                            }

                # For each direct child, find its children recursively
                for path, node in children.items():
                    if node["type"] == "dir":
                        node["children"] = build_tree(items, path, current_depth + 1)
                    tree.append(node)

                # Sort: folders first, then by name
                tree.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"].lower()))
                return tree

            return build_tree(all_items)

        except Exception as e:
            print(f"Error getting snapshot tree: {e}")
            return []

    def install_on_remote(self, ssh_host: str, ssh_port: int, timeout: int = 30) -> bool:
        """Instala restic moderno em uma maquina remota"""
        cmd = """
wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2 &&
bunzip2 -f /tmp/restic.bz2 &&
chmod +x /tmp/restic &&
mv /tmp/restic /usr/local/bin/restic &&
/usr/local/bin/restic version
"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return "restic" in result.stdout.lower()
        except Exception:
            return False
