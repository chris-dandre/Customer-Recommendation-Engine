# Deployment Instructions for Recommendation API (v7.0) on Windows with Python 3.13.2 and VS Code Virtual Environment

This document provides step-by-step instructions for deploying the Recommendation API (`Agentic_workflow_v7.py`) using FastAPI and Docker on a Windows machine running Python 3.13.2. The deployment process includes setting up a new virtual environment (`.venv`) in Visual Studio Code (VS Code) for local testing in a new project folder, with steps to resolve dependency conflicts and run the application. The API generates product recommendations for a specified `UserId` using the Selection Approach, querying data from Astra DB, and includes LangGraph for structured workflows. It uses Gunicorn for better multiprocessing on Windows and provides an endpoint to return the top recommended URL.

**Date and Time of Instructions**: Wednesday, May 14, 2025, at 11:06 PM AEST.

## Prerequisites

Before starting, ensure you have the following installed on your Windows machine:

- **Docker Desktop**:
  - Download and install Docker Desktop for Windows from [Docker's official website](https://www.docker.com/products/docker-desktop/).
  - Ensure Docker Desktop is running and set to use Linux containers (default setting).
  - Enable WSL 2 (Windows Subsystem for Linux 2) if prompted during installation for better performance.
- **Python 3.13.2** (For local testing):
  - You have Python 3.13.2 installed, as specified.
  - Ensure Python and `pip` are added to your system PATH. Verify by running:
    - **Command Prompt**:
      ```cmd
      python --version
      ```
    - **PowerShell**:
      ```powershell
      python --version
      ```
    - Expected output: `Python 3.13.2`.
- **Visual Studio Code (VS Code)**:
  - Download and install VS Code from [code.visualstudio.com](https://code.visualstudio.com/).
  - Install the Python extension for VS Code (by Microsoft) to enable virtual environment support and debugging.
- **curl or Postman**:
  - `curl` is available in Windows 10/11 by default in Command Prompt or PowerShell.
  - Alternatively, download Postman from [postman.com](https://www.postman.com/downloads/) for a GUI to test the API.
- **jq (Optional)**:
  - Download `jq` from [github.com/jqlang/jq](https://github.com/jqlang/jq/releases) (e.g., `jq-win64.exe`) to parse JSON responses.
  - Place it in a directory in your PATH (e.g., `C:\Program Files\jq`) or in your project directory.
- **Astra DB Credentials**:
  - `ASTRA_DB_TOKEN`: Your Astra DB application token.
  - `ASTRA_DB_ENDPOINT`: Your Astra DB API endpoint (e.g., `https://your-astra-db-endpoint.apps.astra.datastax.com`).

## Directory Structure

Create a new project directory (e.g., `D:\Synapsewerx_Projects\Recommendations_API`) and ensure the following files are present:

- `Agentic_workflow_v7.py` (version with LangGraph)
- `requirements.txt`
- `Dockerfile`
- `.env`

After setting up the virtual environment, a `.venv` directory will also be created in this directory.

## Deployment Steps

### 1. Prepare the Application Files

#### 1.1. Save the Main Application File
- Save the application as `Agentic_workflow_v7.py` in your project directory (e.g., `D:\Synapsewerx_Projects\Recommendations_API\Agentic_workflow_v7.py`). This version includes LangGraph for structured workflows and an endpoint to return the top recommended URL.

#### 1.2. Create `requirements.txt`
Create a file named `requirements.txt` in the project directory with the following content:

```
fastapi==0.115.0
uvicorn==0.30.6
astrapy==1.4.2
python-dotenv==1.0.1
pydantic==2.9.2
numpy==2.1.0
langgraph==0.2.28
gunicorn==23.0.0
```

#### 1.3. Create `Dockerfile`
Create a file named `Dockerfile` in the project directory with the following content:

```
# Use an official Python runtime as a parent image
FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY Agentic_workflow_v7.py .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application with Gunicorn and Uvicorn workers
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "Agentic_workflow_v7:app", "--bind", "0.0.0.0:8000", "--log-level", "info", "--timeout", "30"]
```

#### 1.4. Create `.env` File
Create a file named `.env` in the project directory with your Astra DB credentials:

```
ASTRA_DB_TOKEN=your-astra-db-token
ASTRA_DB_ENDPOINT=https://your-astra-db-endpoint.apps.astra.datastax.com
USERINTERESTS_COLLECTION=userinterests
ADVERTISEMENTS_COLLECTION=advertisements
```

Replace `your-astra-db-token` and `https://your-astra-db-endpoint.apps.astra.datastax.com` with your actual Astra DB token and endpoint. Use a text editor like Notepad or VS Code to create this file, ensuring it’s saved as `.env` (not `.env.txt`).

### 2. Set Up the Virtual Environment in VS Code

Since you’ve created a new project folder and previously resolved dependency conflicts, your `.venv` environment should be set up with the updated `requirements.txt`. Let’s verify and proceed with running the application.

#### 2.1. Open the Project in VS Code
- Open VS Code.
- Go to **File > Open Folder** and select your project directory (e.g., `D:\Synapsewerx_Projects\Recommendations_API`).

#### 2.2. Verify the Virtual Environment
Ensure the `.venv` environment exists and is activated:

- Check for the `.venv` directory in `D:\Synapsewerx_Projects\Recommendations_API\.venv`.
- Open the VS Code terminal:
  - Go to **Terminal > New Terminal** in VS Code.
  - This opens a terminal (likely PowerShell or Command Prompt, depending on your VS Code settings).
- Activate the virtual environment:
  - **Command Prompt**:
    ```cmd
    .venv\Scripts\activate
    ```
  - **PowerShell**:
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```
- You should see `(.venv)` in the terminal prompt, indicating the virtual environment is active.

#### 2.3. Verify Dependencies
Ensure the dependencies are installed correctly with the updated `requirements.txt`:

- **Command Prompt**:
  ```cmd
  pip list
  ```
- **PowerShell**:
  ```powershell
  pip list
  ```

You should see `langgraph==0.2.28` and `gunicorn==23.0.0`. If you encounter any issues, reinstall the dependencies:

- **Command Prompt**:
  ```cmd
  pip install -r requirements.txt
  ```
- **PowerShell**:
  ```powershell
  pip install -r requirements.txt
  ```

#### 2.4. Select the Virtual Environment in VS Code
Ensure VS Code uses the `.venv` environment as the Python interpreter:

- Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) to open the Command Palette.
- Type `Python: Select Interpreter` and select it.
- Choose the interpreter from `.venv` (e.g., `Python 3.13.2 ('venv': venv)` or a similar path like `D:\Synapsewerx_Projects\Recommendations_API\.venv\Scripts\python.exe`).
- VS Code will update the interpreter, and you’ll see it in the bottom-left corner of the window (e.g., `Python 3.13.2 (.venv)`).

#### 2.5. Run the FastAPI Application from VS Code
Run the application using Uvicorn or Gunicorn with optimized settings from the VS Code terminal (with `.venv` activated):

- **Using Gunicorn (Recommended for Windows)**:
  - **Command Prompt**:
    ```cmd
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker Agentic_workflow_v7:app --bind 0.0.0.0:8000 --log-level info --timeout 30
    ```
  - **PowerShell**:
    ```powershell
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker Agentic_workflow_v7:app --bind 0.0.0.0:8000 --log-level info --timeout 30
    ```

- **Using Uvicorn (Single Worker for Debugging)**:
  - **Command Prompt**:
    ```cmd
    uvicorn Agentic_workflow_v7:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
    ```
  - **PowerShell**:
    ```powershell
    uvicorn Agentic_workflow_v7:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
    ```

Alternatively, you can run the app using VS Code’s **Run and Debug** feature:
- Create a `launch.json` file in VS Code:
  - Go to **Run > Add Configuration** and select `Python`.
  - Add a configuration to run the app:
    ```json
    {
      "version": "0.2.0",
      "configurations": [
        {
          "name": "Run FastAPI with Gunicorn",
          "type": "python",
          "request": "launch",
          "module": "gunicorn",
          "args": [
            "-w", "4",
            "-k", "uvicorn.workers.UvicornWorker",
            "Agentic_workflow_v7:app",
            "--bind", "0.0.0.0:8000",
            "--log-level", "info",
            "--timeout", "30"
          ],
          "justMyCode": true
        }
      ]
    }
    ```
  - Press `F5` or go to **Run > Start Debugging** to run the app.

#### 2.6. Test the API Locally
Test the API endpoints to retrieve recommendations and the top recommended URL:

- **Get Full Recommendations**:
  - **Command Prompt**:
    ```cmd
    curl http://localhost:8000/recommend/003dL000008HU8rQAG
    ```
  - **PowerShell**:
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/recommend/003dL000008HU8rQAG
    ```
  - **Expected Response** (abridged):
    ```json
    {
      "customer_id": "003dL000008HU8rQAG",
      "user_interests": {
        "InterestName": "Hobbies, Travel, Groceries, Cars, Beverages, Movies, Technology",
        "InterestDescription": "Cooking and baking, Beach vacations and relaxation, Ethnic foods and gourmet ingredients, SUVs and family vehicles, Smoothies and fresh juices, Animated films and family-friendly, Audio equipment and home theater"
      },
      "selection_approach": {
        "top_ad": {
          "url": "https://www.youtube.com/watch?v=satEdUz84r8&autoplay=1&mute=1",
          "product": "Bravia TV",
          "score": 0.7784507
        },
        "top_recommendations": [
          {"url": "https://www.youtube.com/watch?v=satEdUz84r8&autoplay=1&mute=1", "product": "Bravia TV", "score": 0.7784507},
          {"url": "https://www.youtube.com/watch?v=krQKnhMwxn4&autoplay=1&mute=1", "product": "Model 3", "score": 0.7726603},
          ...
        ]
      }
    }
    ```

- **Extract Top Recommended URL from Full Response**:
  - Using `jq` (if installed):
    ```powershell
    curl http://localhost:8000/recommend/003dL000008HU8rQAG | jq -r ".selection_approach.top_ad.url"
    ```
  - Using PowerShell:
    ```powershell
    (Invoke-RestMethod -Uri http://localhost:8000/recommend/003dL000008HU8rQAG).selection_approach.top_ad.url
    ```
  - **Expected Output**:
    ```
    https://www.youtube.com/watch?v=satEdUz84r8&autoplay=1&mute=1
    ```

- **Get Top Recommended URL Directly**:
  - Use the new `/recommend/{user_id}/top-url` endpoint:
    - **Command Prompt**:
      ```cmd
      curl http://localhost:8000/recommend/003dL000008HU8rQAG/top-url
      ```
    - **PowerShell**:
      ```powershell
      Invoke-RestMethod -Uri http://localhost:8000/recommend/003dL000008HU8rQAG/top-url
      ```
  - **Expected Output**:
    ```
    https://www.youtube.com/watch?v=satEdUz84r8&autoplay=1&mute=1
    ```

If the API works locally, proceed to Dockerization. If you encounter errors, check the logs in `workflow.log` (located in your project directory, e.g., `D:\Synapsewerx_Projects\Recommendations_API\workflow.log`). You can also use VS Code’s debugger to step through the code if issues arise.

### 3. Dockerize the Application

#### 3.1. Verify Docker Desktop Is Running
- Open Docker Desktop on your Windows machine.
- Ensure the Docker Engine is running (you’ll see a green light in the bottom-left corner of Docker Desktop).
- If using WSL 2, ensure it’s enabled in Docker Desktop settings under **Settings > Resources > WSL Integration**.

#### 3.2. Build the Docker Image
Build the Docker image using the `Dockerfile`:

- **Command Prompt**:
  ```cmd
  docker build -t recommendation-api:7.0 .
  ```
- **PowerShell**:
  ```powershell
  docker build -t recommendation-api:7.0 .
  ```

This command builds the Docker image named `recommendation-api:7.0` using Python 3.13.2 as the base image.

#### 3.3. Run the Docker Container
Run the container, mapping port 8000 and loading environment variables from the `.env` file:

- **Command Prompt**:
  ```cmd
  docker run --env-file .env -p 8000:8000 recommendation-api:7.0
  ```
- **PowerShell**:
  ```powershell
  docker run --env-file .env -p 8000:8000 recommendation-api:7.0
  ```

- The `--env-file .env` flag loads the environment variables from the `.env` file.
- The `-p 8000:8000` flag maps port 8000 on your Windows host to port 8000 in the container.

#### 3.4. Test the API in Docker
Test the API endpoints to ensure the container is running correctly:

- **Get Full Recommendations**:
  - **Command Prompt**:
    ```cmd
    curl http://localhost:8000/recommend/003dL000008HU8rQAG
    ```
  - **PowerShell**:
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/recommend/003dL000008HU8rQAG
    ```

- **Get Top Recommended URL**:
  - **Command Prompt**:
    ```cmd
    curl http://localhost:8000/recommend/003dL000008HU8rQAG/top-url
    ```
  - **PowerShell**:
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/recommend/003dL000008HU8rQAG/top-url
    ```

The responses should match the local test results. If you encounter issues, check the container logs:

- **Command Prompt**:
  ```cmd
  docker ps
  docker logs <container_id>
  ```
- **PowerShell**:
  ```powershell
  docker ps
  docker logs <container_id>
  ```

Find the `<container_id>` from the `docker ps` output (look under the `CONTAINER ID` column).

### 4. Production Deployment Considerations

#### 4.1. Persist Logs on Windows
To persist logs outside the container, mount a volume to a directory on your Windows host:

- **Command Prompt**:
  ```cmd
  docker run --env-file .env -p 8000:8000 -v D:\Synapsewerx_Projects\Recommendations_API\logs:/app/logs recommendation-api:7.0
  ```
- **PowerShell**:
  ```powershell
  docker run --env-file .env -p 8000:8000 -v D:\Synapsewerx_Projects\Recommendations_API\logs:/app/logs recommendation-api:7.0
  ```

This maps the `D:\Synapsewerx_Projects\Recommendations_API\logs` directory on your Windows host to `/app/logs` in the container, where `workflow.log` is written. Create the `logs` directory if it doesn’t exist:

- **Command Prompt**:
  ```cmd
  mkdir D:\Synapsewerx_Projects\Recommendations_API\logs
  ```
- **PowerShell**:
  ```powershell
  New-Item -ItemType Directory -Path D:\Synapsewerx_Projects\Recommendations_API\logs
  ```

#### 4.2. Health Check
To monitor the container’s health, add a health check endpoint and update the `Dockerfile`:

- Add a health check endpoint to the FastAPI app (already included in `Agentic_workflow_v7.py`):
  ```python
  @app.get("/health")
  async def health_check():
      return {"status": "healthy"}
  ```

- Update the `Dockerfile`:
  ```
  # Use an official Python runtime as a parent image
  FROM python:3.13.2-slim

  # Set working directory
  WORKDIR /app

  # Copy the requirements file into the container
  COPY requirements.txt .

  # Install dependencies
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy the application code into the container
  COPY Agentic_workflow_v7.py .

  # Expose the port FastAPI will run on
  EXPOSE 8000

  # Command to run the FastAPI application with Gunicorn and Uvicorn workers
  CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "Agentic_workflow_v7:app", "--bind", "0.0.0.0:8000", "--log-level", "info", "--timeout", "30"]

  # Health check to ensure the app is running
  HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1
  ```

Rebuild the Docker image after making these changes:

- **Command Prompt**:
  ```cmd
  docker build -t recommendation-api:7.0 .
  ```
- **PowerShell**:
  ```powershell
  docker build -t recommendation-api:7.0 .
  ```

#### 4.3. Environment Variables in Production
In a production environment, you may not want to use a `.env` file. Pass environment variables directly:

- **Command Prompt**:
  ```cmd
  docker run -e ASTRA_DB_TOKEN=your-astra-db-token -e ASTRA_DB_ENDPOINT=https://your-astra-db-endpoint.apps.astra.datastax.com -p 8000:8000 recommendation-api:7.0
  ```
- **PowerShell**:
  ```powershell
  docker run -e ASTRA_DB_TOKEN=your-astra-db-token -e ASTRA_DB_ENDPOINT=https://your-astra-db-endpoint.apps.astra.datastax.com -p 8000:8000 recommendation-api:7.0
  ```

Alternatively, use a secrets management system (e.g., Kubernetes Secrets, AWS Secrets Manager) to securely manage sensitive variables.

#### 4.4. Scaling with Gunicorn Workers
The `Dockerfile` for `Agentic_workflow_v7.py` uses `-w 4` for Gunicorn. Adjust this based on your server’s CPU cores (e.g., `2 * CPU cores + 1`). For example, on a 2-core server:

```dockerfile
CMD ["gunicorn", "-w", "5", "-k", "uvicorn.workers.UvicornWorker", "Agentic_workflow_v7:app", "--bind", "0.0.0.0:8000", "--log-level", "info", "--timeout", "30"]
```

Rebuild the image after adjusting:

- **Command Prompt**:
  ```cmd
  docker build -t recommendation-api:7.0 .
  ```
- **PowerShell**:
  ```powershell
  docker build -t recommendation-api:7.0 .
  ```

### 5. Troubleshooting

- **Docker Desktop Not Running**:
  - Ensure Docker Desktop is running (check for a green light in the bottom-left corner).
  - If Docker fails to start, restart Docker Desktop or check for errors in the Docker Desktop logs.

- **Container Fails to Start**:
  - Check the container logs:
    - **Command Prompt**:
      ```cmd
      docker logs <container_id>
      ```
    - **PowerShell**:
      ```powershell
      docker logs <container_id>
      ```
  - Ensure the `.env` file or environment variables are correctly set.

- **API Returns Errors**:
  - If the `/recommend/{user_id}` or `/recommend/{user_id}/top-url` endpoint returns a 404 or 500 error, check `workflow.log` in your mounted logs directory (e.g., `D:\Synapsewerx_Projects\Recommendations_API\logs\workflow.log`).
  - Use VS Code’s debugger to step through the code if issues arise during local testing.
  - Common issues:
    - `UserId` not found in `userinterests` collection.
    - Astra DB credentials incorrect or network issues.

- **ModuleNotFoundError**:
  - If you encounter `ModuleNotFoundError: No module named 'Agentic_workflow_v7'`:
    - Verify the file exists and is named exactly `Agentic_workflow_v7.py` in the project directory (`D:\Synapsewerx_Projects\Recommendations_API`).
    - Check for hidden extensions (e.g., `Agentic_workflow_v7.py.txt`) by enabling file extensions in File Explorer:
      - Open File Explorer, go to **View > Options > Change folder and search options**.
      - Uncheck **Hide extensions for known file types**, then click **Apply** and **OK**.
    - Test the module import directly:
      ```powershell
      python -c "import Agentic_workflow_v7"
      ```
    - If the import fails, ensure the file is in the correct directory and there are no syntax errors:
      ```powershell
      python Agentic_workflow_v7.py
      ```
    - Run Uvicorn with a single worker to isolate multiprocessing issues:
      ```powershell
      uvicorn Agentic_workflow_v7:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
      ```
    - Use Gunicorn for better multiprocessing on Windows (as shown above).

- **Performance Issues**:
  - Adjust the number of Gunicorn workers based on your system’s resources.
  - Consider implementing rate limiting or caching as suggested in the enhancements.

- **Windows Path Issues**:
  - If you encounter path-related errors (e.g., with volume mounts), ensure paths use backslashes (`\`) and are properly escaped in commands (e.g., `D:\path\to\dir`).

- **Python 3.13.2 Compatibility Issues**:
  - If any dependency fails to install or run in the `.venv` environment, check for a newer version on PyPI that supports Python 3.13.2.
  - For example, if `numpy` or another package causes issues, update to the latest version:
    - **Command Prompt**:
      ```cmd
      pip install numpy --upgrade
      ```
    - **PowerShell**:
      ```powershell
      pip install numpy --upgrade
      ```
  - Update `requirements.txt` with the new version and rebuild the Docker image.

- **Virtual Environment Issues**:
  - If VS Code doesn’t recognize the new `.venv` environment, reselect the interpreter:
    - Press `Ctrl+Shift+P`, type `Python: Select Interpreter`, and choose the `.venv` interpreter.
  - If the virtual environment fails to activate, ensure the activation script exists (e.g., `.venv\Scripts\activate` for Command Prompt or `.venv\Scripts\Activate.ps1` for PowerShell).

### 6. Enhancements (Optional)

For a production-ready API on Windows with Python 3.13.2 and VS Code, consider the following enhancements:

- **Authentication**: Secure the endpoint with an API key or JWT token.
  - Example with API key:
    ```python
    from fastapi.security import APIKeyHeader
    api_key_header = APIKeyHeader(name="X-API-Key")
    @app.get("/recommend/{user_id}", response_model=RecommendationResponse)
    async def get_recommendations(user_id: str, api_key: str = Depends(api_key_header)):
        if api_key != os.getenv("API_KEY"):
            raise HTTPException(status_code=401, detail="Invalid API Key")
        # Recommendation logic
    ```
  - Add `API_KEY=your-api-key` to the `.env` file.

- **Rate Limiting**: Use `slowapi` to limit requests per minute.
  ```cmd
  pip install slowapi
  ```
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from fastapi import Request

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(429, _rate_limit_exceeded_handler)

  @app.get("/recommend/{user_id}", response_model=RecommendationResponse)
  @limiter.limit("5/minute")
  async def get_recommendations(request: Request, user_id: str):
      # Recommendation logic
  ```

- **Monitoring**: Integrate with Prometheus for metrics or use a logging service like ELK stack to monitor `workflow.log`.

- **Documentation**: Access the API documentation at `http://localhost:8000/docs` to test interactively using a web browser on Windows. In VS Code, you can open this URL by right-clicking and selecting "Open in Browser."

For a full list of enhancements, refer to the original deployment discussion.

## Conclusion

You’ve now deployed the Recommendation API (v7.0 with LangGraph) on Windows using FastAPI, Docker, Python 3.13.2, and a fresh `.venv` environment in VS Code for the new project folder. The API is accessible at `http://localhost:8000/recommend/{user_id}` for full recommendations and `http://localhost:8000/recommend/{user_id}/top-url` for the top recommended URL. If you need to scale, secure, or monitor the API further, implement the optional enhancements above.

**Deployment Completed**: Wednesday, May 14, 2025, at 11:06 PM AEST.