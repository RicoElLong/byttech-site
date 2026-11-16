"""Render the site's templates into a static GitHub Pages artifact."""

from html import escape
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
DOCUMENTS = ("index", "privacy", "consent", "legal", "work-order")
ROUTES = {"/": "./", "/request-form.js": "./request-form.js"}
ROUTES.update({f"/{name}": f"./{name}.html" for name in DOCUMENTS})
OWNER_FIELDS = ("NAME", "INN", "ADDRESS", "PHONE", "EMAIL")
# Public contact number already published on the Bot Tech website.
PUBLIC_PHONE = "+79053031551"


def phone_only_page(source: str) -> str:
    source, sections = re.subn(
        r'<!-- QUIZ -->\s*<section class="quiz-section">.*?</section>\s*',
        "",
        source,
        flags=re.DOTALL,
    )
    if sections != 1:
        raise ValueError("Could not remove the request form from the phone-only site.")
    source = re.sub(r'<p class="footer-legal">.*?</p>\s*', "", source, flags=re.DOTALL)
    source = re.sub(
        r'^[ \t]*(?:<a href="(?:mailto:[^"]*|/legal|/privacy|/consent)">[^<]*</a>'
        r'|<script src="/request-form\.js" defer></script>)\n',
        "",
        source,
        flags=re.MULTILINE,
    )
    return (
        source.replace('href="#quiz"', 'href="tel:{{OWNER_PHONE_E164}}"')
        .replace('href="/#quiz">Оставить заявку на сайте', 'href="tel:{{OWNER_PHONE_E164}}">Позвонить мастеру')
        .replace("Звоните по телефону или оставьте заявку на сайте.", "Позвоните мастеру.")
    )


def build(destination: Path) -> None:
    values = {f"OWNER_{field}": os.getenv(f"OWNER_{field}", "").strip()
              for field in OWNER_FIELDS}
    endpoint = os.getenv("REQUEST_API_URL", "").strip()
    if not endpoint:
        values = {"OWNER_PHONE": values["OWNER_PHONE"] or PUBLIC_PHONE}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ValueError("Missing repository variables: " + ", ".join(missing))

    phone = values["OWNER_PHONE"]
    if not re.fullmatch(r"\+7[0-9]{10}", phone):
        raise ValueError("OWNER_PHONE must use the +7XXXXXXXXXX format.")
    if endpoint and not re.fullmatch(r"[0-9]{12}", values["OWNER_INN"]):
        raise ValueError("OWNER_INN must contain 12 digits.")
    if endpoint and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["OWNER_EMAIL"]):
        raise ValueError("OWNER_EMAIL must be an email address.")
    api = urlsplit(endpoint)
    if endpoint and (api.scheme != "https" or not api.hostname or api.username is not None
            or api.path != "/api/requests" or api.query or api.fragment
            or any(char.isspace() for char in endpoint)):
        raise ValueError("REQUEST_API_URL must be an HTTPS URL ending in /api/requests.")
    values["OWNER_PHONE_E164"] = phone

    def relative_link(match: re.Match) -> str:
        attribute, path, fragment = match.groups()
        if path not in ROUTES:
            raise ValueError(f"Unmapped site route: {path}")
        return f'{attribute}="{ROUTES[path]}{fragment or ""}"'

    output = {}
    for name in DOCUMENTS if endpoint else ("index",):
        filename = f"{name}.html"
        source = (WEB_ROOT / filename).read_text(encoding="utf-8")
        if not endpoint:
            source = phone_only_page(source)
        source = re.sub(r'\b(href|src)="(/(?!/)[^"#]*)(#[^"]*)?"', relative_link, source)
        output[filename] = re.sub(
            r"\{\{((?:OWNER|CONTACT)_[A-Z_0-9]+)\}\}",
            lambda match: escape(values[match[1]], quote=True),
            source,
        )

    if endpoint:
        script = (WEB_ROOT / "request-form.js").read_text(encoding="utf-8")
        same_origin = "fetch('/api/requests',"
        if script.count(same_origin) != 1:
            raise ValueError("The expected request URL in web/request-form.js has changed.")
        output["request-form.js"] = script.replace(same_origin, f"fetch({json.dumps(endpoint)},")

    destination.mkdir()
    for filename, content in output.items():
        (destination / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    try:
        build(Path("_site"))
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
