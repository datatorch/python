def normalize_api_url(url: str):
    # rstrip() strips a character SET, not a suffix — it mangled hosts whose
    # names end in those letters (e.g. "https://my-lab.io" -> "https://my-lab.")
    url = url.strip().rstrip("/")
    if url.endswith("/graphql"):
        url = url.removesuffix("/graphql").rstrip("/")
    if not url.endswith("/api"):
        url = f"{url}/api"
    return url
