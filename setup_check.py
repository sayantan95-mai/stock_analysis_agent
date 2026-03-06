"""
🔍 Setup Verification Script
─────────────────────────────
Run this FIRST after cloning the project to verify everything is ready.

Usage:
    uv run python setup_check.py
    # or
    python setup_check.py
"""

import sys
import os
import importlib
import shutil
from pathlib import Path


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

MIN_PYTHON = (3, 12)

REQUIRED_PACKAGES = {
    # package_import_name: (pip_name, min_version, purpose)
    "google.adk":             ("google-adk",             "0.5.0",  "Agent Framework"),
    "google.genai":           ("google-genai",           "1.0.0",  "Gemini LLM & Embeddings"),
    "yfinance":               ("yfinance",               "0.2.40", "Stock Market Data"),
    "tavily":                 ("tavily-python",          "0.5.0",  "Web Search (primary)"),
    "ddgs":                   ("ddgs",                   "6.0.0",  "Web Search (fallback)"),
    "pdfplumber":             ("pdfplumber",             "0.11.0", "PDF Table Extraction"),
    "fitz":                   ("PyMuPDF",                "1.24.0", "PDF Text Extraction"),
    "chromadb":               ("chromadb",               "0.5.0",  "Vector Store (RAG)"),
    "langchain_text_splitters": ("langchain-text-splitters", "0.2.0", "Smart Text Chunking"),
    "pandas":                 ("pandas",                 "2.2.0",  "Data Processing"),
    "streamlit":              ("streamlit",              "1.37.0", "UI Framework"),
    "pydantic":               ("pydantic",               "2.7.0",  "Data Validation"),
    "pydantic_settings":      ("pydantic-settings",      "2.3.0",  "Settings Management"),
    "dotenv":                 ("python-dotenv",          "1.0.0",  "Env File Loading"),
    "rich":                   ("rich",                   "13.7.0", "Terminal Output"),
}

OPTIONAL_PACKAGES = {
    "pytest":        ("pytest",        "8.2.0", "Testing"),
    "ruff":          ("ruff",          "0.5.0", "Linting"),
}

REQUIRED_ENV_VARS = {
    "GOOGLE_API_KEY": {
        "required": True,
        "description": "Gemini API key",
        "get_from": "https://ai.google.dev/",
    },
    "TAVILY_API_KEY": {
        "required": False,  # optional — DuckDuckGo fallback exists
        "description": "Tavily Search API key",
        "get_from": "https://tavily.com/",
    },
}

REQUIRED_DIRS = [
    "src/agents",
    "src/tools",
    "src/models",
    "src/rag",
    "src/config",
    "src/ui",
    "data/uploads",
    "data/cache/market_data",
    "data/cache/search_results",
    "data/cache/chroma_db",
    "tests",
]

REQUIRED_FILES = [
    "pyproject.toml",
    "requirements.txt",
    ".env.example",
    "src/config/settings.py",
    "src/models/schemas.py",
    "src/tools/stock_data.py",
    "src/tools/web_search.py",
    "src/tools/pdf_parser.py",
    "src/rag/vector_store.py",
    "src/rag/pipeline.py",
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


PASS = f"{Colors.GREEN}✔ PASS{Colors.RESET}"
FAIL = f"{Colors.RED}✘ FAIL{Colors.RESET}"
WARN = f"{Colors.YELLOW}⚠ WARN{Colors.RESET}"
INFO = f"{Colors.CYAN}ℹ INFO{Colors.RESET}"

total_checks = 0
passed_checks = 0
failed_checks = 0
warnings = 0


def check(condition: bool, message: str, is_warning: bool = False) -> bool:
    """Record and display a check result."""
    global total_checks, passed_checks, failed_checks, warnings
    total_checks += 1

    if condition:
        passed_checks += 1
        print(f"  {PASS}  {message}")
        return True
    elif is_warning:
        warnings += 1
        print(f"  {WARN}  {message}")
        return False
    else:
        failed_checks += 1
        print(f"  {FAIL}  {message}")
        return False


def section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}{Colors.RESET}")


def get_version(module) -> str:
    """Try to get version from a module."""
    for attr in ("__version__", "VERSION", "version"):
        v = getattr(module, attr, None)
        if v:
            return str(v)
    # Try importlib.metadata
    try:
        import importlib.metadata
        name = module.__name__.split(".")[0]
        return importlib.metadata.version(name)
    except Exception:
        return "unknown"


def compare_versions(current: str, minimum: str) -> bool:
    """Check if current version meets minimum requirement."""
    try:
        from packaging.version import Version
        return Version(current) >= Version(minimum)
    except ImportError:
        # Fallback: simple tuple comparison
        def parse(v):
            return tuple(int(x) for x in v.split(".")[:3] if x.isdigit())
        try:
            return parse(current) >= parse(minimum)
        except Exception:
            return True  # can't compare, assume ok


# ──────────────────────────────────────────────
# Check Functions
# ──────────────────────────────────────────────

def check_python_version():
    """Verify Python version meets minimum requirement."""
    section("1. Python Version")

    major, minor, micro = sys.version_info[:3]
    version_str = f"{major}.{minor}.{micro}"
    required_str = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"

    check(
        (major, minor) >= MIN_PYTHON,
        f"Python {version_str} (required: >= {required_str})"
    )

    # Check if running in virtual env
    in_venv = (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )
    check(in_venv, "Running inside a virtual environment", is_warning=not in_venv)
    if not in_venv:
        print(f"       {Colors.DIM}Tip: Run 'uv sync' to create .venv automatically{Colors.RESET}")

    # Check interpreter path
    print(f"  {INFO}  Interpreter: {sys.executable}")


def check_package_manager():
    """Check if uv or pip is available."""
    section("2. Package Manager")

    uv_path = shutil.which("uv")
    check(uv_path is not None, f"uv found: {uv_path or 'not found'}", is_warning=True)
    if not uv_path:
        print(f"       {Colors.DIM}Install: curl -LsSf https://astral.sh/uv/install.sh | sh{Colors.RESET}")

    pip_path = shutil.which("pip") or shutil.which("pip3")
    check(pip_path is not None, f"pip found: {pip_path or 'not found'}")


def check_required_packages():
    """Verify all required packages are installed and meet version requirements."""
    section("3. Required Packages")

    for import_name, (pip_name, min_ver, purpose) in REQUIRED_PACKAGES.items():
        try:
            # Handle nested imports like google.adk
            mod = importlib.import_module(import_name)
            version = get_version(mod)
            version_ok = compare_versions(version, min_ver) if version != "unknown" else True
            status = f"v{version}" if version != "unknown" else "installed"
            check(
                version_ok,
                f"{pip_name} {status} (>= {min_ver}) — {purpose}"
            )
            if not version_ok:
                print(f"       {Colors.DIM}Upgrade: uv pip install '{pip_name}>={min_ver}'{Colors.RESET}")
        except ImportError:
            check(False, f"{pip_name} NOT INSTALLED — {purpose}")
            print(f"       {Colors.DIM}Install: uv pip install '{pip_name}>={min_ver}'{Colors.RESET}")


def check_optional_packages():
    """Check optional development packages."""
    section("4. Optional Dev Packages")

    for import_name, (pip_name, min_ver, purpose) in OPTIONAL_PACKAGES.items():
        try:
            mod = importlib.import_module(import_name)
            version = get_version(mod)
            check(True, f"{pip_name} v{version} — {purpose}")
        except ImportError:
            check(
                False,
                f"{pip_name} not installed — {purpose} (optional)",
                is_warning=True,
            )


def check_environment_variables():
    """Verify API keys and environment configuration."""
    section("5. Environment Variables")

    # Check .env file exists
    env_file = Path(".env")
    env_example = Path(".env.example")

    has_env = env_file.exists()
    check(has_env, ".env file exists")
    if not has_env and env_example.exists():
        print(f"       {Colors.DIM}Run: cp .env.example .env{Colors.RESET}")

    # Load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Check each env var
    for var_name, config in REQUIRED_ENV_VARS.items():
        value = os.environ.get(var_name, "")
        is_set = bool(value) and value not in (
            f"your_{var_name.lower()}_here",
            "your_gemini_api_key_here",
            "your_tavily_api_key_here",
        )

        if config["required"]:
            check(is_set, f"{var_name} — {config['description']}")
        else:
            check(is_set, f"{var_name} — {config['description']} (optional)", is_warning=not is_set)

        if not is_set:
            print(f"       {Colors.DIM}Get yours: {config['get_from']}{Colors.RESET}")

        # Mask the key for display
        if is_set:
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "****"
            print(f"       {Colors.DIM}Value: {masked}{Colors.RESET}")


def check_project_structure():
    """Verify all required directories and files exist."""
    section("6. Project Structure")

    # Directories
    print(f"  {Colors.DIM}Directories:{Colors.RESET}")
    for dir_path in REQUIRED_DIRS:
        exists = Path(dir_path).is_dir()
        check(exists, f"  {dir_path}/")
        if not exists:
            print(f"       {Colors.DIM}Create: mkdir -p {dir_path}{Colors.RESET}")

    # Files
    print(f"\n  {Colors.DIM}Files:{Colors.RESET}")
    for file_path in REQUIRED_FILES:
        exists = Path(file_path).is_file()
        check(exists, f"  {file_path}")


def check_api_connectivity():
    """Test actual API connections (only if keys are set)."""
    section("7. API Connectivity")

    # --- Gemini API ---
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key and "your_" not in api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            # Test LLM
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Reply with exactly: OK",
            )
            check(
                response and response.text,
                f"Gemini LLM (gemini-2.0-flash) — responded: {response.text.strip()[:20]}"
            )

            # Test Embedding
            emb_response = client.models.embed_content(
                model="text-embedding-004",
                content="test",
            )
            emb_dim = len(emb_response.embeddings[0].values)
            check(
                emb_dim > 0,
                f"Gemini Embeddings (text-embedding-004) — dimension: {emb_dim}"
            )

        except Exception as e:
            check(False, f"Gemini API connection failed: {e}")
    else:
        print(f"  {INFO}  Gemini API — skipped (GOOGLE_API_KEY not set)")

    # --- Tavily API ---
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if tavily_key and "your_" not in tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            result = client.search("test query", max_results=1)
            has_results = len(result.get("results", [])) > 0
            check(has_results, "Tavily Search API — connected")
        except Exception as e:
            check(False, f"Tavily API connection failed: {e}")
    else:
        print(f"  {INFO}  Tavily API — skipped (TAVILY_API_KEY not set)")

    # --- DuckDuckGo (no key needed) ---
    try:
        try:
            from ddgs import DDGS  # new package name
        except ImportError:
            from duckduckgo_search import DDGS  # legacy fallback

        with DDGS() as ddgs:
            results = list(ddgs.text("test", max_results=1))
            check(len(results) > 0, "DuckDuckGo Search — connected (free fallback)")
    except Exception as e:
        check(False, f"DuckDuckGo Search — failed: {e}", is_warning=True)

    # --- yfinance ---
    try:
        import yfinance as yf
        stock = yf.Ticker("RELIANCE.NS")
        price = stock.info.get("currentPrice") or stock.info.get("regularMarketPrice")
        check(
            price is not None and price > 0,
            f"yfinance (NSE) — RELIANCE.NS current price: ₹{price}"
        )
    except Exception as e:
        check(False, f"yfinance connection failed: {e}")

    # --- ChromaDB (local) ---
    try:
        import chromadb
        test_path = "data/cache/chroma_db"
        client = chromadb.PersistentClient(path=test_path)
        col = client.get_or_create_collection("setup-test")
        client.delete_collection("setup-test")
        check(True, f"ChromaDB — local storage OK ({test_path})")
    except Exception as e:
        check(False, f"ChromaDB failed: {e}")


def check_disk_space():
    """Check available disk space for cache and vector store."""
    section("8. System Resources")

    # Disk space
    try:
        usage = shutil.disk_usage(".")
        free_gb = usage.free / (1024 ** 3)
        check(
            free_gb > 1.0,
            f"Disk space: {free_gb:.1f} GB free (need > 1 GB for cache + ChromaDB)"
        )
    except Exception:
        print(f"  {INFO}  Could not check disk space")

    # Check write permissions
    test_file = Path("data/cache/.write_test")
    try:
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        test_file.unlink()
        check(True, "Write permissions OK (data/cache/)")
    except Exception as e:
        check(False, f"Cannot write to data/cache/: {e}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print(f"\n{Colors.BOLD}{'═' * 50}")
    print(f"  📊 Stock Analysis Agent — Setup Checker")
    print(f"{'═' * 50}{Colors.RESET}")

    check_python_version()
    check_package_manager()
    check_required_packages()
    check_optional_packages()
    check_environment_variables()
    check_project_structure()
    check_api_connectivity()
    check_disk_space()

    # ── Summary ──
    print(f"\n{Colors.BOLD}{'═' * 50}")
    print(f"  📋 SUMMARY")
    print(f"{'═' * 50}{Colors.RESET}")
    print(f"  Total checks:  {total_checks}")
    print(f"  {Colors.GREEN}Passed:  {passed_checks}{Colors.RESET}")
    if warnings:
        print(f"  {Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")
    if failed_checks:
        print(f"  {Colors.RED}Failed:  {failed_checks}{Colors.RESET}")

    if failed_checks == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🚀 ALL CLEAR — Ready to start building!{Colors.RESET}")
        print(f"  {Colors.DIM}Next step: Start coding the Research Agent (Phase 1){Colors.RESET}\n")
        sys.exit(0)
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}❌ {failed_checks} issue(s) need fixing before you start.{Colors.RESET}")
        print(f"  {Colors.DIM}Fix the FAIL items above and re-run: python setup_check.py{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
