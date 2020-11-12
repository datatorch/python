def normalize_api_url(url: str):
    url = url.strip().strip("/").strip("/api")
    if not url.endswith("/api"):
        url = f"{url}/api"
    return url
