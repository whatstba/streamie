"""
Debug script for running the FastAPI server with debugpy
This allows attaching a debugger from VS Code or other IDEs
"""

import debugpy
import uvicorn

# Configure debugpy
debugpy.listen(5678)  # Port for debugger to attach
print("⏳ Waiting for debugger to attach on port 5678...")
print("   In VS Code: Run 'Python: Attach' configuration")

# Optional: Wait for debugger to attach before continuing
# debugpy.wait_for_client()

if __name__ == "__main__":
    # Run the server
    print("🚀 Starting FastAPI server with debugging enabled...")
    uvicorn.run(
        "main:app",  # Use module string format for reload
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
