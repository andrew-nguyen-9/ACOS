# acos-backend.spec — PyInstaller build spec for the ACOS backend sidecar binary.
# Run via: pyinstaller acos-backend.spec --noconfirm --distpath dist/backend
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
root = str(Path(".").resolve())

# Collect all chromadb submodules — its __init__ uses pkgutil.iter_modules at
# runtime to discover embedding functions, which fails unless every submodule is
# explicitly bundled.
chromadb_hidden = collect_submodules("chromadb")
chromadb_datas = collect_data_files("chromadb")

a = Analysis(
    ["backend/server_entry.py"],
    pathex=[root],
    binaries=[],
    datas=[
        # Project prompts
        ("backend/prompts", "backend/prompts"),
        # ChromaDB data files (SQL migration scripts etc.)
        *chromadb_datas,
    ],
    hiddenimports=[
        # All of chromadb (including dynamic embedding function discovery)
        *chromadb_hidden,

        # uvicorn internals
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",

        # SQLAlchemy dialects
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.base",
        "sqlalchemy.dialects.sqlite.pysqlite",

        # alembic
        "alembic",
        "alembic.config",
        "alembic.runtime",
        "alembic.runtime.migration",
        "alembic.runtime.environment",
        "alembic.operations",
        "alembic.operations.ops",
        "alembic.script",
        "alembic.script.revision",
        "alembic.ddl",
        "alembic.ddl.impl",

        # other application deps
        "pypdf",
        "docx",                # python-docx import name
        "docx.api",
        "rank_bm25",
        "yaml",                # pyyaml
        "pydantic",
        "pydantic_settings",
        "multipart",           # python-multipart
        "httpx",
        "numpy",               # required by chromadb
        "onnxruntime",         # required by chromadb DefaultEmbeddingFunction (ONNXMiniLM_L6_V2)
        "tokenizers",          # required by chromadb DefaultEmbeddingFunction
        "tqdm",                # required by chromadb DefaultEmbeddingFunction

        # async / concurrency
        "anyio",
        "anyio.from_thread",
        "starlette.middleware.cors",
        "starlette.routing",
        "starlette.applications",
        "starlette.responses",
        "fastapi",
        "fastapi.middleware.cors",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        # numpy is required by chromadb — do NOT exclude it
        "pandas",
        "PIL",
        "notebook",
        "IPython",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="acos-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
