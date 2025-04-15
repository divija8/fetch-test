#!/usr/bin/env python3
import argparse
import asyncio
import logging
from urllib.parse import urlparse
import aiohttp
import yaml
import time
from collections import defaultdict

# Configure logging to include timestamps and log-levels.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_domain(url):
    """
    Extracts the hostname (domain) from a given URL, ignoring any port numbers.
    
    Parameters:
        url (str): The full URL to be processed.
    
    Returns:
        str or None: The extracted hostname or None if an error occurs.
    """
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception as e:
        logging.error(f"Error parsing URL {url}: {e}")
        return None

async def check_endpoint(session, endpoint):
    """
    Asynchronously performs an HTTP request based on the provided endpoint configuration.
    
    An endpoint is considered "UP" if:
      - The HTTP status code is between 200 and 299.
      - The response is received within 500 milliseconds.
    
    Parameters:
        session (aiohttp.ClientSession): The aiohttp session used for the request.
        endpoint (dict): The endpoint configuration with keys 'url', 'method', 'headers', and 'body'.
    
    Returns:
        tuple: A tuple in the form (domain, success) where:
            - domain (str): The hostname extracted from the endpoint's URL.
            - success (bool): True if the endpoint meets the "UP" conditions, otherwise False.
    """
    # Extract the domain from the URL.
    domain = extract_domain(endpoint['url'])
    if not domain:
        return domain, False

    # Get HTTP method, headers, and optional payload.
    method = endpoint.get('method', 'GET').upper()
    headers = endpoint.get('headers', {})
    payload = endpoint.get('body', None)

    try:
        start = time.monotonic()
        # Send the HTTP request with a timeout of 0.5 seconds.
        async with session.request(method, endpoint['url'], headers=headers, json=payload, timeout=0.5) as response:
            elapsed = time.monotonic() - start
            # Check if both the status code and response time meet the criteria.
            if 200 <= response.status < 300 and elapsed <= 0.5:
                return domain, True
            else:
                return domain, False
    except Exception as e:
        logging.warning(f"Request failed for {endpoint['url']}: {e}")
        return domain, False

async def health_check_cycle(endpoints, domain_stats, session):
    """
    Performs a single cycle of health checks on all endpoints concurrently.
    
    For each endpoint, it calls the check_endpoint function and updates the cumulative 
    statistics for each domain. It then logs the availability for each domain.
    
    Parameters:
        endpoints (list): A list of endpoint configuration dictionaries.
        domain_stats (dict): Cumulative statistics per domain that stores 'total' checks and 'successes'.
        session (aiohttp.ClientSession): The session used for performing HTTP requests.
    """
    # Create tasks to perform health checks concurrently.
    tasks = [check_endpoint(session, endpoint) for endpoint in endpoints]
    results = await asyncio.gather(*tasks)

    # Update statistics for each domain.
    for domain, success in results:
        if domain is None:
            continue
        if domain not in domain_stats:
            domain_stats[domain] = {"total": 0, "successes": 0}
        domain_stats[domain]["total"] += 1
        if success:
            domain_stats[domain]["successes"] += 1

    # Log cumulative availability for each domain (dropping decimals).
    for domain, stats in domain_stats.items():
        total_checks = stats["total"]
        successful_checks = stats["successes"]
        availability = int((successful_checks / total_checks) * 100) if total_checks > 0 else 0
        logging.info(f"Domain: {domain} - Availability: {availability}% (Checks: {total_checks}, Successes: {successful_checks})")

async def main_async(endpoints):
    """
    The main asynchronous loop that continuously runs health check cycles.
    
    It initializes cumulative domain statistics, sets up an aiohttp session with a connection 
    limit, and ensures that each cycle of health checks occurs exactly every 15 seconds.
    
    Parameters:
        endpoints (list): A list of endpoint configurations read from the YAML file.
    """
    # Initialize cumulative statistics for endpoints using defaultdict.
    domain_stats = defaultdict(lambda: {"total": 0, "successes": 0})
    logging.info("Starting asynchronous health checks. Press Ctrl+C to exit.")

    # Limit concurrent connections to avoid resource exhaustion.
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            cycle_start = time.monotonic()
            await health_check_cycle(endpoints, domain_stats, session)
            cycle_duration = time.monotonic() - cycle_start
            logging.info(f"Cycle completed in {cycle_duration:.2f} seconds.")
            # Adjust sleep time to ensure each cycle is 15 seconds long.
            sleep_time = max(0, 15 - cycle_duration)
            await asyncio.sleep(sleep_time)

def load_config(file_path):
    """
    Loads and parses the YAML configuration file containing endpoint definitions.
    
    Parameters:
        file_path (str): The path to the YAML configuration file.
    
    Returns:
        list: The parsed YAML content (expected to be a list of endpoint definitions).
    """
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    """
    Main function that parses the command-line argument for the YAML configuration file,
    loads the configuration, and starts the asynchronous health check loop.
    """
    parser = argparse.ArgumentParser(description="Async SRE Health Check Tool")
    parser.add_argument('config_file', help="Path to YAML configuration file")
    args = parser.parse_args()

    # Load endpoint configurations from the YAML file.
    endpoints = load_config(args.config_file)
    if not isinstance(endpoints, list):
        logging.error("The YAML configuration must be a list of endpoint definitions.")
        return

    try:
        asyncio.run(main_async(endpoints))
    except KeyboardInterrupt:
        logging.info("Shutting down asynchronous health check tool.")

# Entry point: if the correct number of command-line arguments is not provided,
# an error message is displayed with usage instructions.
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python monitor.py <config_file_path>")
        sys.exit(1)
    
    main()