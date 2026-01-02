"""Wizard deploy commands"""
import os
import sys
import time
from typing import Optional

from ..i18n import _


class WizardCommands:
    """Deploy wizard for GPU instances"""

    def __init__(self, api_client):
        self.api = api_client

    def get_vast_api_key(self) -> Optional[str]:
        """Get Vast API key from config or environment"""
        # Try environment variable first
        api_key = os.environ.get('VAST_API_KEY')
        if api_key:
            return api_key

        # Try to get from API
        try:
            result = self.api.call("GET", "/api/v1/settings", silent=True)
            if result:
                return result.get('vast_api_key')
        except:
            pass

        return None

    def deploy(
        self,
        gpu_name: str = None,
        speed: str = "fast",
        max_price: float = 2.0,
        region: str = "global"
    ):
        """
        Deploy a GPU instance using the wizard strategy.

        Strategy:
        1. Search for offers matching criteria
        2. Create batch of 5 machines in parallel
        3. Wait up to 90s for any to become ready
        4. If none ready, try another batch (up to 3 batches)
        5. First machine with SSH ready wins, others are destroyed
        """
        print("\n" + _("🚀 Wizard Deploy Starting") + "\n")
        print("=" * 60)
        print(_("   GPU:       {gpu}").format(gpu=gpu_name or _("Any")))
        print(_("   Speed:     {speed}").format(speed=speed))
        print(_("   Max Price: ${price}/hr").format(price=max_price))
        print(_("   Region:    {region}").format(region=region))
        print("=" * 60)

        # Import the wizard service
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        try:
            from src.services.deploy_wizard import (
                DeployWizardService,
                DeployConfig,
                BATCH_SIZE,
                MAX_BATCHES,
                BATCH_TIMEOUT
            )
        except ImportError as e:
            print(_("❌ Could not import wizard service: {error}").format(error=e))
            print(_("   Make sure you're running from the dumontcloud directory"))
            sys.exit(1)

        # Get API key
        api_key = self.get_vast_api_key()
        if not api_key:
            print(_("❌ No Vast.ai API key found"))
            print(_("   Set VAST_API_KEY environment variable or configure via settings"))
            sys.exit(1)

        print("\n" + _("📡 Step 1: Searching for offers..."))

        # Create wizard service
        wizard = DeployWizardService(api_key)

        # Create config
        config = DeployConfig(
            speed_tier=speed,
            gpu_name=gpu_name,
            region=region,
            max_price=max_price,
            disk_space=50,
            setup_codeserver=True,
        )

        # Get offers
        offers = wizard.get_offers(config)

        if not offers:
            print(_("❌ No offers found matching criteria"))
            print(_("💡 Try relaxing filters (higher price, different GPU, different region)"))
            sys.exit(1)

        print(_("   ✓ Found {count} offers").format(count=len(offers)))

        # Show top 5 offers
#         print("\n   Top offers:")
#         for i, offer in enumerate(offers[:5]):
#             print(f"   {i+1}. {offer.get('gpu_name')} - ${offer.get('dph_total', 0):.3f}/hr - {offer.get('inet_down', 0):.0f} Mbps")

        # Start deploy
        print("\n" + _("🔄 Step 2: Starting multi-start deployment..."))
        print(_("   Strategy: Create {batch_size} machines per batch, up to {max_batches} batches").format(batch_size=BATCH_SIZE, max_batches=MAX_BATCHES))
        print(_("   Timeout: {timeout}s per batch").format(timeout=BATCH_TIMEOUT))

        job = wizard.start_deploy(config)

        # Poll for completion
        start_time = time.time()
        last_status = None

        while True:
            job = wizard.get_job(job.id)

            if job.status != last_status:
                elapsed = int(time.time() - start_time)
                print("\n" + _("   [{elapsed}s] Status: {status}").format(elapsed=elapsed, status=job.status))
                print(f"   {job.message}")

                if job.status == 'creating':
                    print(_("   Batch {batch}/{max_batches} - Machines created: {count}").format(batch=job.batch, max_batches=MAX_BATCHES, count=len(job.machines_created)))
                elif job.status == 'waiting':
                    print(_("   Machines created: {machines}").format(machines=job.machines_created))

                last_status = job.status

            if job.status in ['completed', 'failed']:
                break

            time.sleep(2)

        # Handle result
        print("\n" + "=" * 60)

        if job.status == 'failed':
            print(_("❌ Deploy failed: {error}").format(error=job.error))
            print("\n" + _("   Machines tried: {count}").format(count=job.machines_tried))
            print(_("   Machines created: {count}").format(count=len(job.machines_created)))
            print(_("   Machines destroyed: {count}").format(count=len(job.machines_destroyed)))
            sys.exit(1)

        result = job.result
        print("\n" + _("✅ Deploy Complete!") + "\n")
        print(_("📋 Instance Details:"))
        print("-" * 40)
        print(_("   Instance ID: {id}").format(id=result['instance_id']))
        print(_("   GPU:         {gpu}").format(gpu=result.get('gpu_name', _('Unknown'))))
        print(_("   IP:          {ip}").format(ip=result['public_ip']))
        print(_("   SSH Port:    {port}").format(port=result['ssh_port']))
        print(_("   Price:       ${price:.3f}/hr").format(price=result.get('dph_total', 0)))
        print(_("   Speed:       {speed:.0f} Mbps").format(speed=result.get('inet_down', 0)))
        print(_("   Ready in:    {time:.1f}s").format(time=result.get('ready_time', 0)))
        print("-" * 40)
        print("\n" + _("🔗 SSH Command:"))
        print(f"   {result['ssh_command']}")

        if result.get('codeserver_port'):
            print("\n" + _("💻 Code Server:"))
            print(f"   http://{result['public_ip']}:{result['codeserver_port']}")

        # Save instance ID for later use
        print("\n" + _("💾 Instance ID saved: {id}").format(id=result['instance_id']))

        return result
