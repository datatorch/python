def normalize_api_url(url: str):
    url = url.strip().rstrip("/").rstrip("/graphql").rstrip("/api")
    if not url.endswith("/api"):
        url = f"{url}/api"
    return url
