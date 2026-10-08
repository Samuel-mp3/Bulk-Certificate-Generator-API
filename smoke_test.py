import json
import time
import httpx

def main():
    print("--- 1. Health Check ---")
    h_res = httpx.get("http://127.0.0.1:8000/health")
    print("GET /health:", h_res.status_code, h_res.json())

    print("\n--- 2. Submit Job (with 1 valid, 2 invalid recipients) ---")
    payload = {
        "title": "FastAPI Expert Certificate",
        "issuer_name": "Antigravity Academy",
        "issue_date": "2026-10-08",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "   ", "email": "blank@example.com"},
            {"name": "Bob Jones", "email": "invalid-email"}
        ]
    }
    res = httpx.post("http://127.0.0.1:8000/jobs", json=payload)
    print("POST /jobs Code:", res.status_code)
    job_data = res.json()
    print("POST /jobs Response Body:")
    print(json.dumps(job_data, indent=2))

    job_id = job_data["id"]

    # Poll status after background execution
    time.sleep(1)
    print(f"\n--- 3. Poll Job Status (GET /jobs/{job_id}) ---")
    status_res = httpx.get(f"http://127.0.0.1:8000/jobs/{job_id}")
    print("GET /jobs status code:", status_res.status_code)
    print(json.dumps(status_res.json(), indent=2))

    print(f"\n--- 4. List Certificates (GET /jobs/{job_id}/certificates) ---")
    certs_res = httpx.get(f"http://127.0.0.1:8000/jobs/{job_id}/certificates")
    certs_data = certs_res.json()
    print(json.dumps(certs_data, indent=2))

    # Single download
    success_cert = [c for c in certs_data["certificates"] if c["status"] == "SUCCESS"][0]
    dl_url = success_cert["download_url"]
    print(f"\n--- 5. Download Single Certificate ({dl_url}) ---")
    dl_res = httpx.get(f"http://127.0.0.1:8000{dl_url}")
    print("Single PDF Download Status:", dl_res.status_code)
    print("Media Type:", dl_res.headers.get("content-type"))
    print("PDF Header:", dl_res.content[:4])

    # ZIP download
    print(f"\n--- 6. Download Job ZIP Archive (GET /jobs/{job_id}/download) ---")
    zip_res = httpx.get(f"http://127.0.0.1:8000/jobs/{job_id}/download")
    print("ZIP Download Status:", zip_res.status_code)
    print("Media Type:", zip_res.headers.get("content-type"))
    print("ZIP Size (bytes):", len(zip_res.content))

if __name__ == "__main__":
    main()
