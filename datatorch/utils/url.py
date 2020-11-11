def normalize_api_url(url: str):
    return url.strip().strip("/").strip("/api")
