#!/bin/bash
export DATABASE_URL="sqlite:///./test.db"

for i in {1..5}; do
    echo "--- Restart Cycle $i ---"
    
    # Start uvicorn
    .venv/bin/uvicorn app.main:app --port 8000 > server_$i.log 2>&1 &
    UVICORN_PID=$!
    
    echo "Waiting for server to start..."
    while ! nc -z localhost 8000; do
        sleep 0.5
    done
    echo "Server is listening!"
    
    # Test endpoints
    echo "Curling /docs..."
    DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
    if [ "$DOCS_STATUS" != "200" ]; then
        echo "FAILED: /docs returned $DOCS_STATUS"
        kill -9 $UVICORN_PID
        exit 1
    fi
    echo "PASS: /docs"
    
    echo "Curling /openapi.json..."
    OPENAPI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/openapi.json)
    if [ "$OPENAPI_STATUS" != "200" ]; then
        echo "FAILED: /openapi.json returned $OPENAPI_STATUS"
        kill -9 $UVICORN_PID
        exit 1
    fi
    echo "PASS: /openapi.json"
    
    echo "Curling /api/sessions/test-session/runtime-status..."
    RUNTIME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sessions/test-session/runtime-status)
    if [ "$RUNTIME_STATUS" != "401" ]; then
        echo "FAILED: runtime-status returned $RUNTIME_STATUS"
        kill -9 $UVICORN_PID
        exit 1
    fi
    echo "PASS: runtime-status"
    
    echo "Terminating server..."
    kill $UVICORN_PID
    sleep 2
    
done

echo "ALL 5 RESTART CYCLES PASSED SUCCESSFULLY."
