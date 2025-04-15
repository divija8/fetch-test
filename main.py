import argparse
import asyncio
import logging
from urllib.parse import urlparse
import aiohttp
import yaml
import requests
import time
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_domain(url):
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception as e:
        logging.error(f"Error parsing URL {url}: {e}")
        return None

async def check_endpoint(session, endpoint):
    domain = extract_domain(endpoint['url'])
    if not domain:
        return domain, False

    method = endpoint.get('method', 'GET').upper()
    headers = endpoint.get('headers', {})
    payload = endpoint.get('body', None)

    try:
        start = time.monotonic()
        async with session.request(method, endpoint['url'], headers=headers, json=payload, timeout=0.5) as response:
            elapsed = time.monotonic() - start
            if 200 <= response.status < 300 and elapsed <= 0.5:
                return domain, True
            else:
                return domain, False
    except Exception as e:
        logging.warning(f"Request failed for {endpoint['url']}: {e}")
        return domain, False


async def health_check_cycle(endpoints, domain_stats, session):
    tasks = [check_endpoint(session, endpoint) for endpoint in endpoints]
    results = await asyncio.gather(*tasks)

    for domain, success in results:
        if domain is None:
            continue
        if domain not in domain_stats:
            domain_stats[domain] = {"total": 0, "successes": 0}
        domain_stats[domain]["total"] += 1
        if success:
            domain_stats[domain]["successes"] += 1

    for domain, stats in domain_stats.items():
        total_checks = stats["total"]
        successful_checks = stats["successes"]
        availability = int((successful_checks / total_checks) * 100) if total_checks > 0 else 0
        logging.info(f"Domain: {domain} - Availability: {availability}% (Checks: {total_checks}, Successes: {successful_checks})")


async def main_async(endpoints):
    domain_stats = defaultdict(lambda: {"total": 0, "successes": 0})
    logging.info("Starting asynchronous health checks. Press Ctrl+C to exit.")

    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            cycle_start = time.monotonic()
            await health_check_cycle(endpoints, domain_stats, session)
            cycle_duration = time.monotonic() - cycle_start
            logging.info(f"Cycle completed in {cycle_duration:.2f} seconds.")
            sleep_time = max(0, 15 - cycle_duration)
            await asyncio.sleep(sleep_time)


def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    parser = argparse.ArgumentParser(description="Async SRE Health Check Tool")
    parser.add_argument('config_file', help="Path to YAML configuration file")
    args = parser.parse_args()

    endpoints = load_config(args.config_file)
    if not isinstance(endpoints, list):
        logging.error("The YAML configuration must be a list of endpoint definitions.")
        return

    try:
        asyncio.run(main_async(endpoints))
    except KeyboardInterrupt:
        logging.info("Shutting down asynchronous health check tool.")

# Entry point of the program
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python monitor.py <config_file_path>")
        sys.exit(1)
    
    main()