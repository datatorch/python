def normalize_api_url(url: str):
    print(url)
    url = url.strip().rstrip("/").rstrip("/graphql").rstrip("/api")
    print(url)
    if not url.endswith("/api"):
        url = f"{url}/api"
    return url
