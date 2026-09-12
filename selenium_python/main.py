import time
import json
import os
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class NetworkLogger:
    def __init__(self, driver):
        self.driver = driver
        self.requests = {}
        self.responses = {}
        self.captured_calls = []

    def process_logs(self):
        """Processes CDP performance logs to correlate requests and responses."""
        logs = self.driver.get_log('performance')
        for entry in logs:
            try:
                log_data = json.loads(entry['message'])['message']
                method = log_data.get('method', '')
                params = log_data.get('params', {})

                if method == 'Network.requestWillBeSent':
                    req_id = params.get('requestId')
                    request_info = params.get('request', {})
                    self.requests[req_id] = {
                        'requestId': req_id,
                        'url': request_info.get('url'),
                        'method': request_info.get('method'),
                        'headers': request_info.get('headers', {}),
                        'postData': request_info.get('postData'),
                        'timestamp': params.get('timestamp')
                    }

                elif method == 'Network.responseReceived':
                    req_id = params.get('requestId')
                    response_info = params.get('response', {})
                    self.responses[req_id] = {
                        'requestId': req_id,
                        'url': response_info.get('url'),
                        'status': response_info.get('status'),
                        'statusText': response_info.get('statusText'),
                        'mimeType': response_info.get('mimeType'),
                        'headers': response_info.get('headers', {}),
                        'timestamp': params.get('timestamp')
                    }

                    # Fetch response body via CDP
                    body_content = None
                    try:
                        body_res = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                        body_content = body_res.get('body')
                        if body_res.get('base64Encoded') and body_content:
                            body_content = f"[Base64 Encoded Data ({len(body_content)} bytes)]"
                    except Exception:
                        body_content = "[Response body not available or expired]"

                    # Combine request + response info
                    req = self.requests.get(req_id, {})
                    self.captured_calls.append({
                        'requestId': req_id,
                        'url': response_info.get('url'),
                        'method': req.get('method', 'GET'),
                        'status': response_info.get('status'),
                        'statusText': response_info.get('statusText'),
                        'mimeType': response_info.get('mimeType'),
                        'requestHeaders': req.get('headers'),
                        'postData': req.get('postData'),
                        'responseHeaders': response_info.get('headers'),
                        'responseBody': body_content
                    })

            except Exception:
                continue

    def save_to_json(self, filepath="network_logs.json"):
        """Saves captured network details to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.captured_calls, f, indent=2, ensure_ascii=False)
        print(f"\nSaved full network details ({len(self.captured_calls)} calls) to '{filepath}'.")

def filter_json_log(filepath="network_logs.json", target_endpoint="/new/enrollmentStatus", output_dir="filtered_network_output"):
    """
    Scans network_logs.json for target_endpoint and extracts the 2nd request header.
    Writes the extracted header detail to the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n==================================================")
    print(f" SCANNING '{filepath}' FOR ENDPOINT: '{target_endpoint}' ")
    print(f"==================================================")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            logs = json.load(f)

        matched_calls = [call for call in logs if target_endpoint in call.get("url", "")]

        output_summary = []

        if not matched_calls:
            print(f"No network entries found matching endpoint: '{target_endpoint}'")
        else:
            print(f"Found {len(matched_calls)} matching entry/entries. Extracting 2nd request header...")
            for idx, call in enumerate(matched_calls, 1):
                headers = call.get("requestHeaders", {})
                second_header = None
                
                # Extract 2nd request header (0-indexed position 1)
                if isinstance(headers, dict) and len(headers) >= 2:
                    header_items = list(headers.items())
                    key, val = header_items[1]
                    second_header = {key: val}
                elif isinstance(headers, list) and len(headers) >= 2:
                    second_header = headers[1]
                else:
                    second_header = headers

                print(f"  [{idx}] URL: {call.get('url')}")
                print(f"      2nd Request Header: {second_header}")

                result_entry = {
                    "url": call.get("url"),
                    "method": call.get("method"),
                    "second_request_header": second_header,
                    "all_request_headers": headers
                }
                output_summary.append(result_entry)

                header_file = os.path.join(output_dir, f"second_request_header_{idx}.txt")
                with open(header_file, "w", encoding="utf-8") as hf:
                    hf.write(json.dumps(second_header, indent=2))
                print(f"      Saved 2nd header to '{header_file}'")

        summary_filepath = os.path.join(output_dir, "filtered_second_headers.json")
        with open(summary_filepath, "w", encoding="utf-8") as sum_f:
            json.dump(output_summary, sum_f, indent=2, ensure_ascii=False)
        print(f"Exported extraction results to '{summary_filepath}'.")

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
    except Exception as e:
        print(f"Error reading/exporting log files: {e}")

def automate_login(username="abcd", password="1234", headless=True):
    print(f"Initializing Chrome Browser with CDP Network Logging (Headless={headless})...")
    
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"WebDriverManager fallback: {e}")
        driver = webdriver.Chrome(options=chrome_options)

    # Enable CDP Network Domain
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    net_logger = NetworkLogger(driver)

    try:
        # STEP 1: Navigate to page & wait for complete load
        url = "https://"
        print(f"\n[STEP 1] Navigating to {url} & waiting for complete page load...")
        driver.get(url)

        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        username_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
        password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submit")))

        screenshot1 = "step1_page_loaded.png"
        driver.save_screenshot(screenshot1)
        print(f"  Page loaded! Saved '{screenshot1}'")

        # STEP 2: Enter Username
        print(f"\n[STEP 2] Entering Username: '{username}'...")
        username_field.clear()
        for char in username:
            username_field.send_keys(char)
            time.sleep(0.05)
            
        screenshot2 = "step2_username_entered.png"
        driver.save_screenshot(screenshot2)
        print(f"  Saved '{screenshot2}'")

        # STEP 3: Enter Password
        print(f"\n[STEP 3] Entering Password: '{'•' * len(password)}'...")
        password_field.clear()
        for char in password:
            password_field.send_keys(char)
            time.sleep(0.05)
            
        screenshot3 = "step3_password_entered.png"
        driver.save_screenshot(screenshot3)
        print(f"  Saved '{screenshot3}'")

        # STEP 4: Click Submit & Post-submit explicit 10 seconds timeout
        print("\n[STEP 4] Clicking 'Log In' button & initiating 10-second explicit post-submit timeout...")
        submit_button.click()

        # Explicit wait for page load completion and 10 seconds timeout
        post_submit_wait = WebDriverWait(driver, 10)
        post_submit_wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        print("  Waiting explicit 10 seconds post-submit...")
        time.sleep(10)  # Explicit 10 seconds post-submit timeout

        screenshot4 = "step4_after_submit.png"
        driver.save_screenshot(screenshot4)
        print(f"  Completed 10-second explicit post-submit timeout! Saved '{screenshot4}'")

        # Process Network Logs captured during execution
        print("\nProcessing captured network calls...")
        net_logger.process_logs()
        net_logger.save_to_json("network_logs.json")

    except Exception as e:
        print(f"\nAn error occurred during execution: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        print("Browser session closed successfully.")
        
    # Post-processing: Filter network_logs.json for /new/enrollmentStatus and capture 2nd request header
    filter_json_log(filepath="network_logs.json", target_endpoint="/new/enrollmentStatus", output_dir="filtered_network_output")

if __name__ == "__main__":
    automate_login(username="abcd", password="1234", headless=True)
