#!/usr/bin/env python3
"""
Cross-VM IDS Provider-Consumer Synchronization Service

VM1 (this machine) → VM2 (tc-provider via NodePort)

Author: IDS Team  
Date: December 23, 2025
Version: 2.0 (Enhanced with comprehensive debugging)
"""

import requests
import json
import time
import logging
import os
import sys
from datetime import datetime
from requests.auth import HTTPBasicAuth
import urllib3
from typing import Dict, List, Set, Optional
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import traceback

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions. InsecureRequestWarning)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint"""
    
    def do_GET(self):
        if self.path == '/health':  
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            sync_service = getattr(self. server, 'sync_service', None)
            if sync_service:
                health_data = {
                    "status": "healthy" if sync_service.running else "stopped",
                    "uptime_seconds": (datetime.now() - sync_service.sync_stats["start_time"]).total_seconds(),
                    "total_synced":  sync_service.sync_stats["total_synced"],
                    "errors": sync_service.sync_stats["errors"],
                    "last_sync":  sync_service.sync_stats["last_sync"]. isoformat() if sync_service.sync_stats["last_sync"] else None,
                    "tracked_resources": len(sync_service.known_resources),
                    "provider_url": sync_service.provider_url,
                    "consumer_url": sync_service.consumer_url,
                    "provider_reachable": sync_service.last_provider_check,
                    "last_error": sync_service.last_error
                }
            else:
                health_data = {"status": "starting"}
            
            self.wfile.write(json. dumps(health_data, indent=2).encode())
        
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            sync_service = getattr(self. server, 'sync_service', None)
            if sync_service:
                metrics = f"""# HELP ids_sync_resources_synced_total Total number of resources synced
# TYPE ids_sync_resources_synced_total counter
ids_sync_resources_synced_total {sync_service.sync_stats["total_synced"]}

# HELP ids_sync_errors_total Total number of sync errors
# TYPE ids_sync_errors_total counter
ids_sync_errors_total {sync_service.sync_stats["errors"]}

# HELP ids_sync_resources_tracked Number of resources currently tracked
# TYPE ids_sync_resources_tracked gauge
ids_sync_resources_tracked {len(sync_service.known_resources)}

# HELP ids_sync_service_up Service status (1 = up, 0 = down)
# TYPE ids_sync_service_up gauge
ids_sync_service_up {1 if sync_service.running else 0}

# HELP ids_sync_provider_reachable Provider reachability (1 = reachable, 0 = unreachable)
# TYPE ids_sync_provider_reachable gauge
ids_sync_provider_reachable {1 if sync_service.last_provider_check else 0}
"""
            else:
                metrics = "ids_sync_service_up 0\n"
            
            self.wfile.write(metrics. encode())
        
        elif self.path == '/resources':
            # New endpoint to list tracked resources
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            sync_service = getattr(self.server, 'sync_service', None)
            if sync_service:
                resources_data = {
                    "tracked_count": len(sync_service.known_resources),
                    "resources": list(sync_service.known_resources)
                }
            else: 
                resources_data = {"tracked_count": 0, "resources":  []}
            
            self. wfile.write(json.dumps(resources_data, indent=2).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP access logs

class CrossVMIDSSyncService:
    def __init__(self):
        # Setup logging first
        self.setup_logging()
        
        # External access configuration
        self.provider_url = os.getenv('PROVIDER_URL', 'https://10.10.2.20:30578') #contacts another node where the tc-provider is running
        # when running cross VM as a python application use the loadbalancer external IP of tc-consumer, when running as a pod within the cluster use the service name "tc-consumer"
        self.consumer_url = os.getenv('CONSUMER_URL', 'https://10.0.2.15:8444')
        self.username = os.getenv('IDS_USERNAME', 'admin')
        self.password = os.getenv('IDS_PASSWORD', 'password')
        
        # State tracking
        self.known_resources: Set[str] = set()
        self.last_provider_check = False
        self.last_error = None
        self.sync_stats = {
            "total_synced": 0,
            "last_sync": None,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Configuration
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_backoff = int(os.getenv('RETRY_BACKOFF_SECONDS', '2'))
        self.health_port = int(os.getenv('HEALTH_PORT', '8080'))
        self.connection_timeout = int(os.getenv('CONNECTION_TIMEOUT', '30'))
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Start health check server
        self.start_health_server()
    
    def configure_provider_url(self) -> str:
        """
        Configure provider URL for cross-VM NodePort access
        Priority: 
        1. PROVIDER_URL (explicit override)
        2. PROVIDER_NODE_IP + PROVIDER_NODE_PORT
        3. Fallback with warning
        """
        
        # Explicit URL override (highest priority)
        if os.getenv('PROVIDER_URL'):
            url = os.getenv('PROVIDER_URL')
            self.logger.info(f"📍 Using explicit PROVIDER_URL: {url}")
            return url
        
        # NodePort configuration (recommended for cross-VM)
        node_ip = os.getenv('PROVIDER_NODE_IP')
        node_port = os.getenv('PROVIDER_NODE_PORT', '30578')
        
        if node_ip:
            url = f"https://{node_ip}:{node_port}"
            self.logger.info(f"📍 NodePort mode:  {url}")
            return url
        
        # Fallback (requires manual configuration)
        self.logger.error("❌ PROVIDER_NODE_IP not set!")
        self.logger.error("⚙️  Please set environment variables:")
        self.logger.error("    export PROVIDER_NODE_IP=<VM2_IP>")
        self.logger.error("    export PROVIDER_NODE_PORT=30578")
        self.logger. error("    OR")
        self.logger.error("    export PROVIDER_URL=https://<VM2_IP>:30578")
        
        # Use a placeholder that will fail with clear error
        url = "https://PROVIDER_NOT_CONFIGURED: 30578"
        self.logger.warning(f"⚠️  Using placeholder: {url}")
        return url
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Create logs directory
        log_dir = os.getenv('LOG_DIR', './logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging. basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/ids-sync. log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('ids-sync')
        self.logger.info(f"🚀 Cross-VM IDS Sync Service starting...")
    
    def start_health_server(self):
        """Start HTTP health check server in background thread"""
        def run_server():
            try:
                server = HTTPServer(('0.0.0.0', self.health_port), HealthCheckHandler)
                server.sync_service = self
                self.logger.info(f"🏥 Health check server started on port {self.health_port}")
                self.logger.info(f"   Endpoints: /health, /metrics, /resources")
                server.serve_forever()
            except Exception as e:
                self. logger.error(f"Health server error: {e}")
        
        health_thread = threading.Thread(target=run_server, daemon=True)
        health_thread.start()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def make_request_with_retry(self, method:  str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and exponential backoff"""
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.connection_timeout
        
        last_exception = None
        
        for attempt in range(self. max_retries):
            try:
                self.logger.debug(f"🔄 Attempt {attempt + 1}/{self.max_retries}:  {method} {url}")
                
                if method. upper() == 'GET':
                    response = requests.get(url, **kwargs)
                elif method.upper() == 'POST':
                    response = requests. post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Consider 2xx and 3xx as success
                if response.status_code < 400:
                    self.last_error = None
                    return response
                else:
                    self.logger.warning(f"⚠️  HTTP {response.status_code} (attempt {attempt + 1}/{self.max_retries})")
                    last_exception = f"HTTP {response.status_code}"
                    
            except requests.exceptions.ConnectionError as e:
                self. logger.warning(f"⚠️  Connection failed (attempt {attempt + 1}/{self.max_retries}): {str(e)[:100]}")
                last_exception = f"Connection error: {str(e)[:50]}"
            except requests.exceptions.Timeout as e:
                self.logger. warning(f"⚠️  Request timeout (attempt {attempt + 1}/{self.max_retries})")
                last_exception = "Timeout"
            except requests.exceptions.RequestException as e:
                self. logger.warning(f"⚠️  Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)[:100]}")
                last_exception = f"Request error: {str(e)[:50]}"
            
            # Retry with exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = self.retry_backoff * (2 ** attempt)
                self.logger.debug(f"⏳ Waiting {wait_time}s before retry...")
                time. sleep(wait_time)
        
        self.logger.error(f"❌ All {self.max_retries} attempts failed for {url}")
        self.last_error = last_exception
        return None
    
    def check_provider_connectivity(self) -> bool:
        """Test connectivity to provider"""
        self.logger.info("🔍 Testing provider connectivity...")
        
        try:
            response = self.make_request_with_retry(
                'GET',
                f"{self.provider_url}/api/selfDescription/",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={"Accept": "application/json"},
                verify=False
            )
            
            if response and response.status_code == 200:
                self.logger.info(f"✅ Provider is reachable at {self.provider_url}")
                self.last_provider_check = True
                return True
            else: 
                self.logger.error(f"❌ Provider not reachable at {self.provider_url}")
                self.last_provider_check = False
                return False
                
        except Exception as e:
            self.logger.error(f"💥 Provider connectivity check failed: {e}")
            self.last_provider_check = False
            return False
    
    def get_provider_catalog(self) -> Optional[Dict]:
        """Get the complete Provider catalog to discover resources"""
        try:
            self.logger.debug("🔍 Fetching Provider catalog...")
            
            response = self.make_request_with_retry(
                'GET',
                f"{self.provider_url}/api/selfDescription/",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={"Accept":  "application/json"},
                verify=False
            )
            
            if response and response.status_code == 200:
                catalog_data = response.json()
                self.logger.debug("✅ Provider catalog retrieved successfully")
                
                # Debug: Log catalog structure (only in DEBUG mode)
                if self. logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"📋 Catalog structure:  {json.dumps(catalog_data, indent=2)[:500]}...")
                
                self.last_provider_check = True
                return catalog_data
            else: 
                status = response.status_code if response else "No response"
                self.logger. error(f"❌ Failed to get Provider catalog: {status}")
                self.last_provider_check = False
                return None
                
        except Exception as e:
            self.logger.error(f"💥 Error fetching Provider catalog: {e}")
            self.logger.error(traceback.format_exc())
            self.last_provider_check = False
            return None
    
    def extract_resource_identifiers(self, catalog_data: Dict) -> List[str]:
        """Extract all TextResource identifiers from catalog"""
        resource_ids = []
        
        try:
            catalogs = catalog_data.get('ids:resourceCatalog', [])
            self.logger.info(f"🔍 Found {len(catalogs)} catalog(s) in provider")
            
            if not catalogs:
                self. logger.warning("⚠️  No resource catalogs found in provider response")
                self.logger.debug(f"Available top-level keys: {list(catalog_data. keys())}")
                return []
            
            for catalog_idx, catalog in enumerate(catalogs):
                offered_resources = catalog.get('ids:offeredResource', [])
                self.logger.info(f"🔍 Catalog {catalog_idx} has {len(offered_resources)} offered resource(s)")
                
                if not offered_resources:
                    self.logger.warning(f"⚠️  Catalog {catalog_idx} has no offered resources")
                    self.logger.debug(f"Catalog keys: {list(catalog.keys())}")
                    continue
                
                for resource_idx, resource in enumerate(offered_resources):
                    resource_id = resource.get('@id')
                    resource_type = resource.get('@type')
                    resource_title = 'Unknown'
                    
                    try:
                        title_list = resource.get('ids:title', [])
                        if title_list and len(title_list) > 0:
                            resource_title = title_list[0]. get('@value', 'Unknown')
                    except: 
                        pass
                    
                    self.logger.debug(f"   📄 Resource {resource_idx + 1}: {resource_id}")
                    self.logger.debug(f"      Type: {resource_type}, Title: {resource_title}")
                    
                    # Only sync TextResources
                    if resource_id and resource_type == 'ids:TextResource':
                        resource_ids.append(resource_id)
                        self.logger.info(f"   ✅ Will track: {resource_id. split('/')[-1]} ({resource_title})")
                    elif resource_id: 
                        self.logger.debug(f"   ⏭️  Skipping: {resource_id. split('/')[-1]} (type: {resource_type})")
                    else:
                        self.logger.warning(f"   ⚠️  Resource {resource_idx + 1} has no @id")
            
            self.logger.info(f"📋 Total:  {len(resource_ids)} TextResource(s) found in catalog")
            
            # Debug: Log the resource IDs
            if resource_ids and self.logger.isEnabledFor(logging.DEBUG):
                for rid in resource_ids:
                    self.logger.debug(f"   - {rid}")
            
            return resource_ids
            
        except Exception as e:
            self. logger.error(f"💥 Error extracting resource IDs: {e}")
            self.logger.error(traceback. format_exc())
            return []
    
    def get_resource_details(self, resource_id: str) -> Optional[Dict]:
        """Get complete resource details from Provider"""
        try:
            resource_name = resource_id.split('/')[-1]
            self.logger.debug(f"📄 Fetching details for resource: {resource_name}")
            
            response = self.make_request_with_retry(
                'GET',
                f"{self.provider_url}/api/offeredResource/",
                auth=HTTPBasicAuth(self.username, self. password),
                headers={
                    "Accept": "application/json",
                    "resource":  resource_id
                },
                verify=False
            )
            
            if response and response.status_code == 200:
                resource_data = response.json()
                self.logger.debug(f"✅ Resource details retrieved:  {resource_name}")
                return resource_data
            else: 
                status = response.status_code if response else "No response"
                self.logger.error(f"❌ Failed to get resource {resource_name}: {status}")
                if response:
                    self.logger.debug(f"Response body: {response.text[: 200]}")
                return None
                
        except Exception as e:
            self.logger.error(f"💥 Error fetching resource {resource_id. split('/')[-1]}: {e}")
            self.logger.error(traceback. format_exc())
            return None
    
    def get_consumer_catalog_header(self) -> Optional[str]:
        """Get the catalog ID needed for Consumer POST requests"""
        try:
            self.logger.debug("🔍 Getting Consumer catalog header...")
            
            response = self.make_request_with_retry(
                'GET',
                f"{self.consumer_url}/api/selfDescription/",
                auth=HTTPBasicAuth(self.username, self. password),
                headers={"Accept": "application/json"},
                verify=False
            )
            
            if response and response.status_code == 200:
                consumer_data = response.json()
                catalogs = consumer_data.get('ids:resourceCatalog', [])
                
                if catalogs:
                    catalog_id = catalogs[0]. get('@id')
                    if catalog_id:
                        clean_catalog_id = catalog_id.strip().strip("'\"")
                        self. logger.debug(f"✅ Consumer catalog ID: {clean_catalog_id}")
                        return clean_catalog_id
                    else:
                        self. logger.error("❌ Catalog ID is empty")
                        return None
                else:
                    self.logger.warning("⚠️  No catalog found in Consumer")
                    return None
            else:
                status = response.status_code if response else "No response"
                self.logger.error(f"❌ Failed to get Consumer catalog: {status}")
                return None
                
        except Exception as e:
            self.logger. error(f"💥 Error getting Consumer catalog: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def post_resource_to_consumer(self, resource_data: Dict, catalog_header: str) -> bool:
        """Post resource to Consumer with enhanced error handling"""
        try: 
            resource_id = resource_data.get('@id', 'unknown')
            resource_name = resource_id.split('/')[-1]
            self.logger.info(f"🚀 Posting resource to Consumer: {resource_name}")
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'catalog': catalog_header
            }
            
            response = self.make_request_with_retry(
                'POST',
                f"{self.consumer_url}/api/offeredResource/",
                auth=HTTPBasicAuth(self.username, self.password),
                headers=headers,
                data=json.dumps(resource_data, separators=(',', ':')),
                verify=False,
                timeout=60
            )
            
            if response and response.status_code == 200:
                self.logger.info(f"✅ Successfully synced resource: {resource_name}")
                self.sync_stats["total_synced"] += 1
                return True
            else:
                status = response.status_code if response else "No response"
                response_text = response.text if response else "No response"
                self.logger.error(f"❌ Failed to post resource {resource_name}: {status}")
                self.logger.error(f"Response:  {response_text[: 200]}")
                self.sync_stats["errors"] += 1
                return False
                
        except Exception as e: 
            self.logger.error(f"💥 Exception posting resource to Consumer: {e}")
            self.logger.error(traceback. format_exc())
            self.sync_stats["errors"] += 1
            return False
    
    def sync_new_resources(self) -> None:
        """Main synchronization logic"""
        try:
            self.logger.info("🔄 Starting synchronization cycle...")
            
            # Step 1: Get Provider catalog
            catalog_data = self.get_provider_catalog()
            if not catalog_data:
                self.logger.error("❌ Cannot proceed without Provider catalog")
                return
            
            # Step 2: Extract resource identifiers
            current_resources = set(self.extract_resource_identifiers(catalog_data))
            
            # Enhanced debugging
            self.logger.info(f"🔍 Current resources in catalog: {len(current_resources)}")
            self.logger.info(f"🔍 Known resources tracked: {len(self.known_resources)}")
            
            if current_resources and self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Current resources in catalog:")
                for res_id in current_resources:
                    self.logger.debug(f"   📄 {res_id}")
            
            if self.known_resources and self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Already tracked resources:")
                for res_id in self.known_resources:
                    self.logger.debug(f"   ✓ {res_id}")
            
            # Step 3: Find new resources
            new_resources = current_resources - self.known_resources
            
            self.logger.info(f"🔍 New resources to sync: {len(new_resources)}")
            
            if new_resources:
                self.logger.info(f"🆕 Found {len(new_resources)} new resource(s) to sync")
                
                for res_id in new_resources: 
                    self.logger.info(f"   🆕 {res_id. split('/')[-1]}")
                
                # Step 4: Get Consumer catalog header
                catalog_header = self. get_consumer_catalog_header()
                if not catalog_header: 
                    self.logger.error("❌ Cannot sync without Consumer catalog header")
                    return
                
                # Step 5: Sync each new resource
                success_count = 0
                for resource_id in new_resources:
                    resource_name = resource_id.split('/')[-1]
                    
                    # Get full resource details from Provider
                    resource_data = self.get_resource_details(resource_id)
                    if resource_data:
                        # Post to Consumer
                        success = self.post_resource_to_consumer(resource_data, catalog_header)
                        if success:
                            self.known_resources.add(resource_id)
                            success_count += 1
                        
                        # Small delay between requests
                        time.sleep(1)
                    else:
                        self.logger.error(f"❌ Failed to get details for {resource_name}")
                
                self.logger.info(f"📊 Sync batch complete: {success_count}/{len(new_resources)} successful")
            else:
                self.logger.info("✅ No new resources found")
            
            # Update stats
            self.sync_stats["last_sync"] = datetime.now()
            self.known_resources.update(current_resources)
            
            total_attempts = self.sync_stats["total_synced"] + self.sync_stats["errors"]
            success_rate = (self.sync_stats["total_synced"] / max(total_attempts, 1)) * 100
            self.logger.info(f"📊 Sync complete.  Resources:  {len(self.known_resources)}, Success Rate: {success_rate:.1f}%")
            
        except Exception as e:
            self. logger.error(f"💥 Error during synchronization: {e}")
            self.logger.error(traceback.format_exc())
            self.sync_stats["errors"] += 1
    
    def run(self) -> None:
        """Main service loop"""
        self.logger. info("🚀 Cross-VM IDS Provider-Consumer Sync Service starting...")
        self.logger.info(f"📍 VM1 (this machine) → VM2 (tc-provider)")
        self.logger.info(f"📡 Provider URL: {self.provider_url}")
        self.logger.info(f"📥 Consumer URL: {self.consumer_url}")
        self.logger.info(f"⏱️  Poll Interval: {self.poll_interval} seconds")
        self.logger.info(f"🔄 Max Retries: {self.max_retries}")
        self.logger.info(f"🏥 Health Check Port: {self.health_port}")
        self.logger.info(f"📝 Log Level: {logging.getLevelName(self.logger.level)}")
        
        # Initial connectivity check
        if not self.check_provider_connectivity():
            self.logger.error("❌ Cannot reach provider at startup")
            self.logger.error("📋 Troubleshooting checklist:")
            self.logger. error("   1. Is VM2 deployed and running?")
            self.logger.error("   2. Is tc-provider service accessible?")
            self.logger. error("   3. Check:  kubectl get svc tc-provider (on VM2)")
            self.logger.error("   4. Is firewall allowing port 30578?")
            self.logger. error("   5. Can you ping VM2 from VM1?")
            self.logger.error("   6. Test: curl -k https://<VM2-IP>:30578/api/selfDescription/")
            self.logger.warning("⚠️  Continuing anyway, will retry on each cycle...")
        
        try:
            # Initial sync
            self.sync_new_resources()
            
            # Main loop
            while self.running:
                try:
                    self.logger.debug(f"⏳ Waiting {self.poll_interval} seconds until next sync...")
                    time.sleep(self.poll_interval)
                    
                    if self.running:
                        self. sync_new_resources()
                    
                except KeyboardInterrupt: 
                    break
                except Exception as e: 
                    self.logger.error(f"💥 Error in main loop: {e}")
                    self.logger.error(traceback.format_exc())
                    time.sleep(5)
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.logger.info("🛑 IDS Sync Service stopped")
            uptime = datetime.now() - self.sync_stats["start_time"]
            total_attempts = self.sync_stats["total_synced"] + self.sync_stats["errors"]
            success_rate = (self.sync_stats["total_synced"] / max(total_attempts, 1)) * 100
            
            self.logger.info(f"📊 Final Stats:")
            self.logger.info(f"   ⏰ Uptime: {uptime}")
            self.logger.info(f"   📈 Success Rate: {success_rate:.1f}%")
            self.logger.info(f"   ✅ Total Synced: {self.sync_stats['total_synced']}")
            self.logger.info(f"   ❌ Errors: {self.sync_stats['errors']}")
            self.logger.info(f"   📋 Resources Tracked: {len(self. known_resources)}")

def main():
    """Entry point for cross-VM sync service"""
    print("=" * 70)
    print("  IDS Provider-Consumer Synchronization Service (Cross-VM)")
    print("  Version 2.0 - Enhanced Debug Edition")
    print("=" * 70)
    print()
    
    service = CrossVMIDSSyncService()
    try:
        service.run()
    except Exception as e:
        service.logger.error(f"💥 Service error: {e}")
        service.logger.error(traceback. format_exc())
        sys.exit(1)

if __name__ == "__main__": 
    main()