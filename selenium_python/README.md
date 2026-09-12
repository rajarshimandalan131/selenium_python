# Selenium Network Capture & 10-Second Post-Submit Timeout

This project uses [Selenium WebDriver](https://www.selenium.dev/) with Chrome DevTools Protocol (CDP) performance logging to record network requests, API headers, and response bodies into `network_logs.json`.

After form submission, the script enforces an explicit **10-second timeout** to ensure all post-submit XHR network calls complete before capturing the final screenshot and closing the browser.

## Step-by-Step Flow

1. **Step 1 - Complete Initial Page Load**: Navigates to target page and waits for `document.readyState == 'complete'`.
2. **Step 2 - Enter Username**: Inputs username (`abcd`).
3. **Step 3 - Enter Password**: Inputs password (`1234`).
4. **Step 4 - Submit & 10-Second Post-Submit Timeout**: Clicks submit button and executes an explicit 10-second timeout before taking [step4_after_submit.png](step4_after_submit.png).
5. **Post-Processing JSON Extractor**: Scans `network_logs.json` for target endpoints and extracts request headers into `filtered_network_output/`.

## Output Files

- [main.py](main.py): Automation script with 10-second explicit post-submit timeout.
- [network_logs.json](network_logs.json): Exported raw network trace.
- [filtered_network_output/](filtered_network_output): Filtered output directory.
