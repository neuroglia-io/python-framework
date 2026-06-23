import uvicorn

from neuroglia.hosting.web import WebApplicationBuilder

# Create the application builder
builder = WebApplicationBuilder()

# Build the FastAPI application
app = builder.build()


# Add a simple endpoint
@app.get("/")
async def hello():
    return {"message": "Hello from Neuroglia!"}


# Run the application (if executed directly)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
