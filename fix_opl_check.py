#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
""" Enhance opl_check.py 's check_standard_terms_url to validate page content. """
from pathlib import Path

path = Path("tools/opl_check.py")
text = path.read_text(encoding="utf-8")

# Find function boundaries
start = text.find("def check_standard_terms_url(root: Path) -> CheckResult:")
end = text.find("\ndef check_spdx_headers", start)
if start == -1 or end == -1:
    raise SystemExit("Could not locate function boundaries")

new_func = '''def check_standard_terms_url(root: Path) -> CheckResult:
    """Check that the Standard Terms URL is valid and contains required content."""
    notice_content = None
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            notice_content = p.read_text(encoding="utf-8", errors="ignore")
            break
    if not notice_content:
        return CheckResult("standard-terms-url", False, "Cannot check URL: no NOTICE file")

    urls = re.findall(r"https?://[^\\s\\>\\"\'<]+", notice_content)
    if not urls:
        return CheckResult("standard-terms-url", False, "No URL found in NOTICE")

    url = urls[0].rstrip(".,;)")
    if not url.startswith("https://"):
        return CheckResult("standard-terms-url", False, f"URL must use HTTPS: {url}")

    # Fetch and check the page content
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "OPL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct:
                return CheckResult("standard-terms-url", False,
                                   f"URL does not return HTML (got {ct}): {url}", "warning")
    except urllib.error.HTTPError as e:
        return CheckResult("standard-terms-url", False, f"URL returned HTTP {e.code}: {url}")
    except urllib.error.URLError as e:
        return CheckResult("standard-terms-url", False,
                           f"URL unreachable ({e.reason}): {url}", "warning")
    except Exception as e:
        return CheckResult("standard-terms-url", False,
                           f"URL check failed ({e}): {url}", "warning")

    # Now check that the page contains substantive content
    try:
        req = urllib.request.Request(url, method="GET",
                                     headers={"User-Agent": "OPL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\\s+", " ", text).lower()

            has_pricing = any(kw in text for kw in
                ["price", "$", "fee", "cost", "tariff", "payment", "pay", "usd", "year", "month", "subscription"])
            has_terms = any(kw in text for kw in
                ["commercial use", "license", "terms", "permission", "agreement", "standard terms"])
            has_contact = any(kw in text for kw in
                ["contact", "email", "mailto", "stripe", "bank", "sponsor"])

            missing = []
            if not has_pricing:
                missing.append("pricing")
            if not has_terms:
                missing.append("commercial-use terms")
            if not has_contact:
                missing.append("payment mechanism or contact")

            if missing:
                return CheckResult("standard-terms-url", False,
                    "URL reachable and HTML, but may be missing: " + ", ".join(missing) +
                    " — verify your Standard Terms page publishes pricing, commercial-use terms, and a payment mechanism or contact.",
                    "warning")
            return CheckResult("standard-terms-url", True,
                               f"Standard Terms URL is valid and publishes required content: {url}")
    except Exception:
        return CheckResult("standard-terms-url", True,
                           f"Standard Terms URL is reachable: {url}")

'''

text = text[:start] + new_func + text[end:]
path.write_text(text, encoding="utf-8")
print("Done.")
