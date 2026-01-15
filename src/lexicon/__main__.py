"""
Module entry point, supports running with python -m lexicon
This will start the FastAPI application by default.
For training, use: poetry run lexicon or python -m lexicon.train
"""

from .app import app
import uvicorn
import os

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9000"))
    
    uvicorn.run(
        "lexicon.app:app",
        host=host,
        port=port,
        reload=True
    )

