"""
Azure Functions backend for RAG Chat Application
Uses Azure OpenAI "On Your Data" feature with AI Search integration
"""
import azure.functions as func
import json
import logging
import os
from typing import AsyncGenerator
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "redlist-index")

# Global client instance (initialized lazily)
_client = None
_credential = None
_token_provider = None

def get_openai_client():
    """Get or create Azure OpenAI client with lazy initialization"""
    global _client, _credential, _token_provider
    
    if _client is None:
        _credential = DefaultAzureCredential()
        _token_provider = get_bearer_token_provider(
            _credential, "https://cognitiveservices.azure.com/.default"
        )
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=_token_provider,
            api_version="2024-02-15-preview"
        )
    
    return _client


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    logger.info("Health check requested")
    
    health_status = {
        "status": "healthy",
        "service": "rag-chat-backend",
        "version": "1.0.0"
    }
    
    return func.HttpResponse(
        json.dumps(health_status, ensure_ascii=False),
        mimetype="application/json",
        status_code=200
    )


@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Chat endpoint with Azure OpenAI On Your Data
    Supports streaming responses
    """
    try:
        # Parse request body
        req_body = req.get_json()
        user_message = req_body.get("message", "")
        
        if not user_message:
            logger.warning("Empty message received")
            return func.HttpResponse(
                json.dumps({"error": "Message is required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )
        
        logger.info(f"Chat request received: {user_message[:100]}...")
        
        # Validate configuration
        if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX]):
            error_msg = "Azure configuration incomplete. Check environment variables."
            logger.error(error_msg)
            return func.HttpResponse(
                json.dumps({"error": error_msg}, ensure_ascii=False),
                mimetype="application/json",
                status_code=500
            )
        
        # Configure Azure OpenAI with On Your Data
        messages = [
            {"role": "system", "content": "あなたは環境省のレッドリスト（絶滅危惧種）に関する専門家アシスタントです。ユーザーの質問に対して、提供されたデータに基づいて正確かつ丁寧に回答してください。"},
            {"role": "user", "content": user_message}
        ]
        
        # Azure OpenAI On Your Data configuration
        extra_body = {
            "data_sources": [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": AZURE_SEARCH_ENDPOINT,
                        "index_name": AZURE_SEARCH_INDEX,
                        "authentication": {
                            "type": "system_assigned_managed_identity"
                        },
                        "query_type": "semantic",
                        "semantic_configuration": "semantic-config",
                        "top_n_documents": 5,
                        "in_scope": True,
                        "strictness": 3
                    }
                }
            ]
        }
        
        logger.info(f"Calling Azure OpenAI with On Your Data. Index: {AZURE_SEARCH_INDEX}")
        
        # Get Azure OpenAI client (lazy initialization)
        client = get_openai_client()
        
        # Call Azure OpenAI with streaming
        try:
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                extra_body=extra_body,
                stream=True,
                temperature=0.7,
                max_tokens=800
            )
            
            # Stream response as Server-Sent Events (SSE)
            def generate():
                try:
                    for chunk in response:
                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                # SSE format: data: {json}\n\n
                                data = json.dumps({
                                    "content": delta.content
                                }, ensure_ascii=False)
                                yield f"data: {data}\n\n"
                    
                    # Send completion signal
                    yield "data: [DONE]\n\n"
                    logger.info("Streaming response completed successfully")
                    
                except Exception as stream_error:
                    error_msg = f"Streaming error: {str(stream_error)}"
                    logger.error(error_msg, exc_info=True)
                    error_data = json.dumps({
                        "error": error_msg
                    }, ensure_ascii=False)
                    yield f"data: {error_data}\n\n"
            
            return func.HttpResponse(
                generate(),
                mimetype="text/event-stream",
                status_code=200,
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
            
        except Exception as openai_error:
            error_msg = f"Azure OpenAI API error: {str(openai_error)}"
            logger.error(error_msg, exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    "error": "AI応答の生成中にエラーが発生しました",
                    "details": error_msg
                }, ensure_ascii=False),
                mimetype="application/json",
                status_code=500
            )
    
    except ValueError as ve:
        error_msg = f"Invalid request format: {str(ve)}"
        logger.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON format"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=400
        )
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "details": error_msg
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=500
        )
