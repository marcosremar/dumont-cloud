"""
SkyPilot Provider for job orchestration
Handles launching and monitoring fine-tuning jobs via SkyPilot CLI

Uses vendor/skypilot fork via PYTHONPATH instead of system-installed SkyPilot.
"""
import subprocess
import json
import logging
import os
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Vendor SkyPilot directory
VENDOR_DIR = Path(__file__).parent.parent.parent.parent / "vendor" / "skypilot"
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates"


def get_skypilot_env() -> Dict[str, str]:
    """
    Get environment variables for running SkyPilot from vendor directory.
    Adds vendor/skypilot to PYTHONPATH.
    """
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    vendor_path = str(VENDOR_DIR)
    
    if current_pythonpath:
        env["PYTHONPATH"] = f"{vendor_path}:{current_pythonpath}"
    else:
        env["PYTHONPATH"] = vendor_path
    
    return env


def _run_sky_command(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Run a SkyPilot CLI command using the vendor fork.
    
    Args:
        args: Command arguments (without 'sky' prefix)
        timeout: Command timeout in seconds
        
    Returns:
        subprocess.CompletedProcess
    """
    cmd = ["python3", "-m", "sky.cli"] + args
    env = get_skypilot_env()
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env
    )


class SkyPilotProvider:
    """
    Provider for SkyPilot job orchestration.
    Uses SkyPilot CLI from vendor/skypilot fork to launch and monitor jobs.
    """

    def __init__(self):
        """Initialize SkyPilot provider"""
        self.template_path = TEMPLATE_PATH
        self._verify_skypilot()

    def _verify_skypilot(self) -> bool:
        """Verify SkyPilot vendor fork is available"""
        try:
            # Check if vendor directory exists
            if not VENDOR_DIR.exists():
                logger.error(f"SkyPilot vendor directory not found: {VENDOR_DIR}")
                return False
            
            # Try to import sky to verify it works
            result = _run_sky_command(["--version"], timeout=10)
            
            if result.returncode == 0:
                logger.info(f"SkyPilot vendor fork available: {result.stdout.strip()}")
                return True
            
            # Some versions may not have --version, try --help
            result = _run_sky_command(["--help"], timeout=10)
            if result.returncode == 0:
                logger.info("SkyPilot vendor fork available (verified via --help)")
                return True
                
            logger.warning(f"SkyPilot CLI returned non-zero exit code: {result.stderr}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.warning("SkyPilot CLI timed out during verification (may still work)")
            return True  # Assume it works, timeout might be due to API server startup
        except Exception as e:
            logger.error(f"Error verifying SkyPilot: {e}")
            return False

    def launch_finetune_job(
        self,
        job_name: str,
        yaml_path: str,
    ) -> Dict[str, Any]:
        """
        Launch a fine-tuning job via SkyPilot.

        Args:
            job_name: Unique name for the job
            yaml_path: Path to the SkyPilot task YAML file

        Returns:
            {"success": True, "job_id": int, "job_name": str} or
            {"success": False, "error": str}
        """
        logger.info(f"Launching fine-tuning job: {job_name}")

        if not os.path.exists(yaml_path):
            return {"success": False, "error": f"YAML file not found: {yaml_path}"}

        try:
            args = [
                "jobs", "launch",
                yaml_path,
                "--name", job_name,
                "--detach-run",
                "-y"
            ]

            logger.debug(f"Running SkyPilot command: sky {' '.join(args)}")

            result = _run_sky_command(args, timeout=180)

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Failed to launch job: {error_msg}")
                return {"success": False, "error": error_msg}

            # Parse job ID from output
            job_id = self._parse_job_id(result.stdout + result.stderr)

            logger.info(f"Job {job_name} launched successfully with ID: {job_id}")
            return {
                "success": True,
                "job_id": job_id,
                "job_name": job_name,
                "output": result.stdout,
            }

        except subprocess.TimeoutExpired:
            logger.error("Job launch timed out after 180 seconds")
            return {"success": False, "error": "Job launch timed out"}
        except Exception as e:
            logger.error(f"Failed to launch job: {e}")
            return {"success": False, "error": str(e)}

    def get_job_status(self, job_id: Optional[int] = None, job_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of a SkyPilot job.

        Args:
            job_id: Job ID to check
            job_name: Job name to check (alternative to job_id)

        Returns:
            Dict with job status information
        """
        try:
            result = _run_sky_command(["jobs", "queue", "--json"], timeout=30)

            if result.returncode != 0:
                return {"error": result.stderr or "Failed to get job queue"}

            try:
                jobs = json.loads(result.stdout) if result.stdout.strip() else []
            except json.JSONDecodeError:
                return {"error": "Failed to parse job queue output"}

            # Find the job
            for job in jobs:
                if job_id and job.get("id") == job_id:
                    return self._format_job_status(job)
                if job_name and job.get("name") == job_name:
                    return self._format_job_status(job)

            return {"status": "NOT_FOUND"}

        except subprocess.TimeoutExpired:
            return {"error": "Timed out getting job status"}
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {"error": str(e)}

    def get_job_logs(self, job_name: str, tail: int = 100) -> str:
        """
        Get logs from a SkyPilot job.

        Args:
            job_name: Name of the job
            tail: Number of lines to return from the end

        Returns:
            Log output as string
        """
        try:
            result = _run_sky_command(["jobs", "logs", job_name, "--no-follow"], timeout=60)

            if result.returncode != 0:
                return f"Error getting logs: {result.stderr}"

            # Return last N lines
            lines = result.stdout.strip().split('\n')
            return '\n'.join(lines[-tail:])

        except subprocess.TimeoutExpired:
            return "Error: Timed out getting logs"
        except Exception as e:
            return f"Error: {str(e)}"

    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel a SkyPilot job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if successful
        """
        try:
            result = _run_sky_command(["jobs", "cancel", str(job_id), "-y"], timeout=60)

            if result.returncode == 0:
                logger.info(f"Job {job_id} cancelled successfully")
                return True
            else:
                logger.error(f"Failed to cancel job {job_id}: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        List all SkyPilot jobs.

        Returns:
            List of job dictionaries
        """
        try:
            result = _run_sky_command(["jobs", "queue", "--json"], timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to list jobs: {result.stderr}")
                return []

            try:
                jobs = json.loads(result.stdout) if result.stdout.strip() else []
                return [self._format_job_status(job) for job in jobs]
            except json.JSONDecodeError:
                logger.error("Failed to parse job queue output")
                return []

        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []

    def check_cloud(self, cloud: str = "vast") -> Dict[str, Any]:
        """
        Check if a cloud provider is configured and enabled.
        
        Args:
            cloud: Cloud provider name (vast, gcp, aws, etc.)
            
        Returns:
            Dict with check results
        """
        try:
            result = _run_sky_command(["check", cloud], timeout=30)
            
            return {
                "cloud": cloud,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "enabled": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"cloud": cloud, "error": "Timed out", "enabled": False}
        except Exception as e:
            return {"cloud": cloud, "error": str(e), "enabled": False}

    def _format_job_status(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Format job status from SkyPilot output"""
        return {
            "job_id": job.get("id"),
            "name": job.get("name"),
            "status": job.get("status", "UNKNOWN"),
            "start_time": job.get("start_time"),
            "end_time": job.get("end_time"),
            "resources": job.get("resources"),
            "cluster": job.get("cluster"),
        }

    def _parse_job_id(self, output: str) -> Optional[int]:
        """
        Parse job ID from SkyPilot launch output.

        SkyPilot outputs various formats, try multiple patterns.
        """
        patterns = [
            r'Job ID:\s*(\d+)',
            r'Submitted job (\d+)',
            r'job_id=(\d+)',
            r'\[(\d+)\]',  # [123] format
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(match.group(1))

        logger.warning(f"Could not parse job ID from output: {output[:200]}")
        return None

    @staticmethod
    def map_gpu_type(gpu_type: str) -> str:
        """
        Map GPU type names to SkyPilot accelerator format.

        Args:
            gpu_type: User-friendly GPU name

        Returns:
            SkyPilot accelerator string
        """
        gpu_mapping = {
            "A100": "A100",
            "A100-40GB": "A100",
            "A100-80GB": "A100-80GB",
            "H100": "H100",
            "H100-80GB": "H100",
            "RTX4090": "RTX4090",
            "RTX3090": "RTX3090",
            "L4": "L4",
            "T4": "T4",
            "V100": "V100",
        }
        return gpu_mapping.get(gpu_type, gpu_type)


# Singleton instance
_skypilot_provider: Optional[SkyPilotProvider] = None


def get_skypilot_provider() -> SkyPilotProvider:
    """Get or create SkyPilot provider singleton"""
    global _skypilot_provider
    if _skypilot_provider is None:
        _skypilot_provider = SkyPilotProvider()
    return _skypilot_provider
