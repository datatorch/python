def normalize_api_url(url: str):
    url = url.strip()
    if url.endswith("/"):
        url = url[:-1]
    if not url.endswith("api"):
        url = f"{url}/api"
    return url