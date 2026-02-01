from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os
from datetime import datetime

# ---------------- CONFIG ----------------
COMMAND_MODE = "show"     # "show" or "config"
MAX_THREADS = 5
DEVICE_FILE = "devices.txt"
COMMAND_FILE = "commands.txt"
# ---------------------------------------

# Create directories
os.makedirs("outputs/success", exist_ok=True)
os.makedirs("outputs/failed", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Logging
log_file = f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_devices():
    devices = []
    with open(DEVICE_FILE) as f:
        for line in f:
            if line.strip():
                hostname, ip, user, pwd = line.strip().split(",")
                devices.append({
                    "device_type": "cisco_ios",   # Cisco 2960
                    "host": ip,
                    "username": user,
                    "password": pwd,
                    "hostname": hostname,
                })
    return devices

def load_commands():
    with open(COMMAND_FILE) as f:
        return [cmd.strip() for cmd in f if cmd.strip()]

def run_device(device, commands):
    hostname = device["hostname"]
    output = ""

    try:
        logging.info(f"{hostname}: Connecting")
        conn = ConnectHandler(
            device_type=device["device_type"],
            host=device["host"],
            username=device["username"],
            password=device["password"],
            fast_cli=False
        )

        if COMMAND_MODE == "show":
            for cmd in commands:
                output += f"\n===== {cmd} =====\n"
                output += conn.send_command(cmd, expect_string=r"#")
        else:
            output = conn.send_config_set(commands)
            conn.save_config()

        conn.disconnect()

        with open(f"outputs/success/{hostname}.txt", "w") as f:
            f.write(output)

        logging.info(f"{hostname}: SUCCESS")
        return hostname, "SUCCESS"

    except Exception as e:
        logging.error(f"{hostname}: FAILED - {str(e)}")

        with open(f"outputs/failed/{hostname}.txt", "w") as f:
            f.write(str(e))

        return hostname, "FAILED"

def main():
    devices = load_devices()
    commands = load_commands()

    results = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(run_device, dev, commands) for dev in devices]

        for future in as_completed(futures):
            results.append(future.result())

    print("\n========= SUMMARY =========")
    for host, status in results:
        print(f"{host}: {status}")
    print(f"\nDetailed log: {log_file}")

if __name__ == "__main__":
    main()