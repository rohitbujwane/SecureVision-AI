"""
Generate a synthetic security log dataset for development and testing.
All records are synthetic and do not represent real attack observations.

Schema is inspired by CIC-IDS2017 network flow data.
"""

import csv
import random
import datetime
import os
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "sample_logs.csv"

HEADERS = [
    "timestamp", "source_ip", "dest_ip", "protocol",
    "flow_duration", "total_fwd_packets", "total_bwd_packets",
    "total_length_of_fwd_packets", "total_length_of_bwd_packets",
    "fwd_packet_length_mean", "bwd_packet_length_mean",
    "flow_bytes_per_s", "flow_packets_per_s",
    "fwd_iat_mean", "bwd_iat_mean", "flow_iat_mean",
    "active_mean", "idle_mean",
    "syn_flag_count", "ack_flag_count", "psh_flag_count",
    "rst_flag_count", "fin_flag_count",
    "label"
]

PROTOCOLS = ["TCP", "UDP", "TCP", "TCP", "TCP"]  # weighted toward TCP
INTERNAL_IPS = [f"192.168.1.{i}" for i in range(10, 50)]
EXTERNAL_IPS = [f"10.0.{random.randint(0,10)}.{random.randint(1,254)}" for _ in range(20)]


def gen_normal():
    """Generate a normal (benign) network flow record."""
    return {
        "flow_duration": random.uniform(100, 500000),
        "total_fwd_packets": random.randint(1, 50),
        "total_bwd_packets": random.randint(1, 40),
        "total_length_of_fwd_packets": random.uniform(40, 15000),
        "total_length_of_bwd_packets": random.uniform(40, 12000),
        "fwd_packet_length_mean": random.uniform(40, 800),
        "bwd_packet_length_mean": random.uniform(40, 600),
        "flow_bytes_per_s": random.uniform(100, 100000),
        "flow_packets_per_s": random.uniform(1, 500),
        "fwd_iat_mean": random.uniform(10, 50000),
        "bwd_iat_mean": random.uniform(10, 50000),
        "flow_iat_mean": random.uniform(10, 30000),
        "active_mean": random.uniform(0, 5000),
        "idle_mean": random.uniform(0, 100000),
        "syn_flag_count": random.choice([0, 1, 1, 1]),
        "ack_flag_count": random.randint(0, 5),
        "psh_flag_count": random.randint(0, 3),
        "rst_flag_count": 0,
        "fin_flag_count": random.choice([0, 1]),
        "label": "BENIGN",
    }


def gen_portscan():
    """Generate a port scan anomaly."""
    return {
        "flow_duration": random.uniform(0, 100),  # Very short
        "total_fwd_packets": random.randint(1, 3),
        "total_bwd_packets": random.randint(0, 1),
        "total_length_of_fwd_packets": random.uniform(40, 80),
        "total_length_of_bwd_packets": random.uniform(0, 40),
        "fwd_packet_length_mean": random.uniform(40, 60),
        "bwd_packet_length_mean": random.uniform(0, 40),
        "flow_bytes_per_s": random.uniform(500000, 5000000),  # High rate
        "flow_packets_per_s": random.uniform(5000, 50000),  # Very high
        "fwd_iat_mean": random.uniform(0, 10),  # Very rapid
        "bwd_iat_mean": random.uniform(0, 5),
        "flow_iat_mean": random.uniform(0, 5),
        "active_mean": random.uniform(0, 10),
        "idle_mean": random.uniform(0, 50),
        "syn_flag_count": random.randint(1, 10),  # Many SYN flags
        "ack_flag_count": random.randint(0, 1),
        "psh_flag_count": 0,
        "rst_flag_count": random.randint(0, 5),  # RST responses
        "fin_flag_count": 0,
        "label": "PortScan",
    }


def gen_ddos():
    """Generate a DDoS-like anomaly."""
    return {
        "flow_duration": random.uniform(100, 5000),
        "total_fwd_packets": random.randint(100, 10000),  # Huge packet count
        "total_bwd_packets": random.randint(0, 10),
        "total_length_of_fwd_packets": random.uniform(50000, 5000000),
        "total_length_of_bwd_packets": random.uniform(0, 500),
        "fwd_packet_length_mean": random.uniform(40, 200),
        "bwd_packet_length_mean": random.uniform(0, 40),
        "flow_bytes_per_s": random.uniform(1000000, 50000000),  # Extreme
        "flow_packets_per_s": random.uniform(10000, 500000),
        "fwd_iat_mean": random.uniform(0, 1),
        "bwd_iat_mean": random.uniform(0, 1),
        "flow_iat_mean": random.uniform(0, 1),
        "active_mean": random.uniform(100, 5000),
        "idle_mean": random.uniform(0, 10),
        "syn_flag_count": random.randint(5, 50),
        "ack_flag_count": random.randint(0, 2),
        "psh_flag_count": random.randint(0, 1),
        "rst_flag_count": random.randint(0, 3),
        "fin_flag_count": 0,
        "label": "DDoS",
    }


def gen_bruteforce():
    """Generate a brute-force login-like anomaly."""
    return {
        "flow_duration": random.uniform(1000, 30000),
        "total_fwd_packets": random.randint(5, 30),
        "total_bwd_packets": random.randint(5, 25),
        "total_length_of_fwd_packets": random.uniform(200, 5000),
        "total_length_of_bwd_packets": random.uniform(200, 3000),
        "fwd_packet_length_mean": random.uniform(50, 200),
        "bwd_packet_length_mean": random.uniform(50, 150),
        "flow_bytes_per_s": random.uniform(10000, 200000),
        "flow_packets_per_s": random.uniform(100, 2000),
        "fwd_iat_mean": random.uniform(50, 500),  # Regular intervals
        "bwd_iat_mean": random.uniform(50, 500),
        "flow_iat_mean": random.uniform(50, 300),
        "active_mean": random.uniform(500, 10000),
        "idle_mean": random.uniform(500, 5000),
        "syn_flag_count": random.randint(2, 15),
        "ack_flag_count": random.randint(2, 15),
        "psh_flag_count": random.randint(2, 10),
        "rst_flag_count": random.randint(0, 5),
        "fin_flag_count": random.randint(1, 5),
        "label": "BruteForce",
    }


def gen_exfiltration():
    """Generate a data exfiltration-like anomaly."""
    return {
        "flow_duration": random.uniform(100000, 3000000),  # Long duration
        "total_fwd_packets": random.randint(50, 500),
        "total_bwd_packets": random.randint(2, 20),
        "total_length_of_fwd_packets": random.uniform(100000, 10000000),  # Lots of data out
        "total_length_of_bwd_packets": random.uniform(40, 2000),
        "fwd_packet_length_mean": random.uniform(1000, 5000),  # Large packets
        "bwd_packet_length_mean": random.uniform(40, 100),
        "flow_bytes_per_s": random.uniform(50000, 500000),
        "flow_packets_per_s": random.uniform(10, 200),
        "fwd_iat_mean": random.uniform(100, 5000),
        "bwd_iat_mean": random.uniform(1000, 50000),
        "flow_iat_mean": random.uniform(100, 3000),
        "active_mean": random.uniform(5000, 100000),
        "idle_mean": random.uniform(50000, 500000),  # Long idle
        "syn_flag_count": 1,
        "ack_flag_count": random.randint(1, 5),
        "psh_flag_count": random.randint(5, 30),
        "rst_flag_count": 0,
        "fin_flag_count": 1,
        "label": "Exfiltration",
    }


def generate_dataset(n_normal=700, n_portscan=60, n_ddos=40,
                     n_bruteforce=50, n_exfiltration=30):
    """Generate the complete synthetic dataset."""
    rows = []
    base_time = datetime.datetime(2024, 6, 15, 8, 0, 0)

    generators = (
        [(gen_normal, "BENIGN")] * n_normal +
        [(gen_portscan, "PortScan")] * n_portscan +
        [(gen_ddos, "DDoS")] * n_ddos +
        [(gen_bruteforce, "BruteForce")] * n_bruteforce +
        [(gen_exfiltration, "Exfiltration")] * n_exfiltration
    )
    random.shuffle(generators)

    for i, (gen_fn, _) in enumerate(generators):
        record = gen_fn()
        ts = base_time + datetime.timedelta(seconds=i * random.uniform(0.5, 5))
        record["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")
        record["source_ip"] = random.choice(INTERNAL_IPS + EXTERNAL_IPS)
        record["dest_ip"] = random.choice(INTERNAL_IPS + EXTERNAL_IPS)
        record["protocol"] = random.choice(PROTOCOLS)

        # Round numeric values
        for key in record:
            if isinstance(record[key], float):
                record[key] = round(record[key], 4)

        rows.append(record)

    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic security log dataset.")
    parser.add_argument("--samples", type=int, default=880, help="Total number of samples to generate")
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Output CSV path")
    args = parser.parse_args()

    total = args.samples
    # Distribution ratios: ~85% normal, 6% portscan, 4% ddos, 3% bruteforce, 2% exfiltration
    n_portscan = int(total * 0.06)
    n_ddos = int(total * 0.04)
    n_bruteforce = int(total * 0.03)
    n_exfiltration = int(total * 0.02)
    n_normal = total - (n_portscan + n_ddos + n_bruteforce + n_exfiltration)

    rows = generate_dataset(
        n_normal=n_normal,
        n_portscan=n_portscan,
        n_ddos=n_ddos,
        n_bruteforce=n_bruteforce,
        n_exfiltration=n_exfiltration
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic records -> {out_path}")

    # Print distribution
    from collections import Counter
    labels = Counter(r["label"] for r in rows)
    print("Label distribution:")
    for label, count in sorted(labels.items()):
        print(f"  {label}: {count} ({count/len(rows)*100:.1f}%)")


if __name__ == "__main__":
    main()
