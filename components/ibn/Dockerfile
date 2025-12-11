# --- BUILDER STAGE: Obfuscate the Code ---
FROM python:3.12-slim as builder
WORKDIR /builder

# 1. Copy requirements.txt FIRST
COPY requirements.txt .
COPY . .
# 2. Install dependencies including Pyarmor (using requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt pyarmor

# 3. Copy source code (assuming source is in a 'src' folder)
# This command is often better than 'COPY . /builder' if you have local files you don't need
COPY src /builder/src

# Conditionally run Pyarmor obfuscation
RUN if [ -f /builder/src/app.py ]; then \
        echo "Found app.py - Obfuscating code..."; \
        pyarmor gen --output dist /builder/src/app.py; \
    else \
        echo "No app.py found - Using pre-obfuscated code from dist"; \
        # Copying pre-obfuscated files from a different source (like the root directory)
        # This assumes your pre-obfuscated code is in /builder/dist/
        mkdir -p dist && cp -r /builder/src/dist/* dist/; \
    fi


# --- FINAL STAGE: Runtime Environment ---
FROM python:3.12-slim

WORKDIR /app

# 1. Copy requirements and install runtime dependencies
COPY --from=builder /builder/requirements.txt /app/
# Crucial change: Only install the runtime component
RUN pip install --no-cache-dir -r requirements.txt pyarmor

# 2. Copy the obfuscated application code and runtime files
# This copies app.py and pyarmor_runtime_xxxx from /builder/dist/ to /app/
COPY --from=builder /builder/dist/. /app/

# 3. Copy supporting directories
COPY --from=builder /builder/Intent/ /app/Intent/
COPY --from=builder /builder/NSD/ /app/NSD/
COPY --from=builder /builder/Temp/ /app/Temp/
COPY --from=builder /builder/UseCase/ /app/UseCase/

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]