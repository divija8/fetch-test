# SRE Health Check Tool

This tool monitors the availability of a list of HTTP endpoints defined in a YAML configuration file.
It performs periodic health checks every 15 seconds and logs the cumulative availability percentage per domain.
The tool has been enhanced to ensure that each endpoint is marked “UP” only if it returns a 200–299 HTTP status code and responds within 500 milliseconds.
Additionally, availability is aggregated by domain (ignoring port numbers) and reported as an integer percentage (with decimals dropped).

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Identified Issues and Improvements](#identified-issues-and-improvements)


## Installation

### Prerequisites
• Python 3.6 or later
• pip (Python package manager)

### Clone the Repository

Clone the repository and navigate into the project directory:

```bash
git clone https://your-public-repo-url.git
cd your-repo-folder
```

### Install Dependencies

The tool requires pyyaml and requests packages. You can install them via pip.

If you have a requirements.txt file, run:

```bash
pip install -r requirements.txt
```

Alternatively, install the dependencies individually:

```bash
pip install pyyaml requests
```

Example requirements.txt content:

```txt
pyyaml
requests
```

## Usage

### Step 1: Prepare the YAML Configuration File

Create a configuration file (e.g., config.yaml) that lists your endpoints. For example:

```yaml
- name: "Google Home"
  url: "https://www.google.com"
  method: "GET"

- name: "Example Domain"
  url: "https://example.com"
  method: "GET"

- name: "Local API Health"
  url: "http://localhost:8080/api/health"
  method: "GET"
  headers:
    Authorization: "Bearer your_token_here"
```

### Step 2: Run the Monitoring Tool

Execute the tool by providing the path to your YAML configuration file:

```bash
python main.py config.yaml
```

The tool will start health check cycles every 15 seconds, displaying the cumulative availability percentage for each domain.
To stop the tool, press Ctrl+C.

## Configuration

The YAML configuration file must be a list of endpoint definitions, each including:
- name: A descriptive label for the endpoint.
- url: The HTTP or HTTPS URL of the endpoint.
-  method: (Optional) The HTTP method; defaults to GET if omitted.
-  headers: (Optional) A dictionary of HTTP headers.
-  body: (Optional) A JSON-encoded string for endpoints that require a request body (e.g., for POST).

## Identified Issues and Improvements

### 1. Response Time Validation
- Issue:
The original code did not verify that an endpoint responded within 500 milliseconds.
- Improvement:
Updated logic measures the response time and marks an endpoint as “UP” only if it responds within 500ms in addition to having a valid HTTP status.

### 2. Domain Extraction – Ignoring Port Numbers
- Issue:
The domain was extracted using simple string splits, potentially including the port number (e.g., example.com:8080), which could lead to separate entries for the same domain.
- Improvement:
The code now extracts the hostname using proper URL parsing, ensuring that only the base domain is used for cumulative statistics.

### 3. Cycle Timing Accuracy
- Issue:
The original code unconditionally slept for 15 seconds without accounting for the time taken by health checks, which could make cycles longer than intended.
- Improvement:
The sleep time is dynamically adjusted based on the elapsed time in each cycle to ensure that a new cycle starts every 15 seconds.

### 4. Availability Reporting – Dropping Decimal Values
-  Issue:
Availability percentages were rounded, which might include unwanted decimal values.
-  Improvement:
The calculation now drops the decimal portion and reports the availability as a whole number (e.g., 85%).

### 5. Robust Error Handling and Logging
-  Issue:
The original implementation had limited error handling and logging, making it harder to diagnose issues.
-  Improvement:
Enhanced logging and error handling have been added for URL parsing failures and HTTP request errors, improving the tool’s reliability and debuggability.