import os
import subprocess
import threading
import logging
import base64
import json
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Configure logging
log_dir = "reencrypt_all_logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"reencrypt_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


def run_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
        return output.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {cmd}\n{e.output.decode('utf-8')}")
        return None


def fetch_public_key():
    logging.info("Fetching current public key from the SealedSecrets controller...")
    cert = run_command("kubeseal --fetch-cert")
    if cert:
        cert_hash = hashlib.sha256(cert.encode()).hexdigest()
        logging.info(f"Public key hash: {cert_hash[:16]}...")  
        # Use os.path.join and tempfile directory
        temp_dir = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP') or '.', 'sealedsecrets')
        os.makedirs(temp_dir, exist_ok=True)
        cert_path = os.path.join(temp_dir, "sealedsecrets-public-cert.pem")
        with open(cert_path, "w") as f:
            f.write(cert)
        return cert_path
    return None


def list_sealed_secrets():
    logging.info("Listing all SealedSecrets in the cluster...")
    output = run_command("kubectl get sealedsecrets --all-namespaces -o json")
    if output:
        data = json.loads(output)
        return data.get("items", [])
    return []


def reseal_secret(secret, cert_path):
    namespace = secret["metadata"]["namespace"]
    name = secret["metadata"]["name"]

    logging.info(f"Processing {namespace}/{name}...")

    # Use the same temp directory as fetch_public_key
    temp_dir = os.path.dirname(cert_path)
    
    # Export the existing SealedSecret
    secret_file = os.path.join(temp_dir, f"{namespace}-{name}-sealed.yaml")
    with open(secret_file, "w") as f:
        yaml_data = run_command(f"kubectl get sealedsecret {name} -n {namespace} -o yaml")
        if yaml_data:
            f.write(yaml_data)
        else:
            logging.error(f"Failed to fetch YAML for {namespace}/{name}")
            return

    # Reseal using the new cert
    new_sealed_file = os.path.join(temp_dir, f"{namespace}-{name}-resealed.yaml")
    cmd = f"kubeseal --re-encrypt --cert {cert_path} < {secret_file} > {new_sealed_file}"
    result = run_command(cmd)
    if result is None:
        logging.error(f"Failed to reseal {namespace}/{name}")
        return

    # Apply the new sealed secret
    apply_result = run_command(f"kubectl apply -f {new_sealed_file}")
    if apply_result:
        logging.info(f"Successfully resealed and updated {namespace}/{name}")
    else:
        logging.error(f"Failed to apply updated SealedSecret for {namespace}/{name}")


def main():
    cert_path = fetch_public_key()
    if not cert_path:
        logging.error("Public key not found. Exiting.")
        return

    secrets = list_sealed_secrets()
    if not secrets:
        logging.info("No SealedSecrets found.")
        return

    logging.info(f"Found {len(secrets)} SealedSecrets. Starting reseal process...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        for secret in secrets:
            executor.submit(reseal_secret, secret, cert_path)

    logging.info("Reseal process completed.")


main()
