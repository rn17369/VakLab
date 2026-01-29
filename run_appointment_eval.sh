#!/bin/bash
# Run appointment evaluation with Google AI API (not Vertex AI)

# Unset Vertex AI variables to force use of GOOGLE_API_KEY
unset GOOGLE_GENAI_USE_VERTEXAI
unset GOOGLE_APPLICATION_CREDENTIALS
unset GOOGLE_CLOUD_PROJECT
unset GOOGLE_CLOUD_LOCATION

# Export Google API key from .env
export GOOGLE_API_KEY=$(grep "^GOOGLE_API_KEY=" .env | cut -d '=' -f2)
export GOOGLE_GENAI_USE_VERTEXAI=0

echo "Running appointment evaluation with Google AI API..."
echo "GOOGLE_GENAI_USE_VERTEXAI: $GOOGLE_GENAI_USE_VERTEXAI"
echo "GOOGLE_API_KEY set: ${GOOGLE_API_KEY:0:10}..."

python eval/eval_runner.py --run --campaign appointment
