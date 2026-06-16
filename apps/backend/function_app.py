"""
Azure Functions backend for a beginner-friendly closed-network RAG chat application.
The Function app stays thin and delegates retrieval + grounded generation to Azure OpenAI
On Your Data backed by Azure AI Search.
"""
import azure.functions as func
import json
import logging
import os
from openai import AzureOpenAI
from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "redlist-index")
AZURE_SEARCH_SEMANTIC_CONFIGURATION = os.environ.get(
    "AZURE_SEARCH_SEMANTIC_CONFIGURATION", "semantic-config"
)
SYSTEM_PROMPT = (
    "あなたは環境省のレッドリスト（絶滅危惧種）に関する専門家アシスタントです。"
    "提供された検索結果に基づいて、正確かつ丁寧に回答してください。"
    "検索結果にない情報は推測せず、その旨を明示してください。"
)

# Global client instances (initialized lazily)
_openai_client = None
_credential = None
_token_provider = None


def is_development_environment():
    """Azure Functions uses Development when running locally."""
    return os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") == "Development"


def get_credential():
    """Use developer credentials locally and managed identity in Azure."""
    global _credential

    if _credential is None:
        if is_development_environment():
            _credential = DefaultAzureCredential()
        else:
            client_id = os.environ.get("AZURE_CLIENT_ID")
            _credential = (
                ManagedIdentityCredential(client_id=client_id)
                if client_id
                else ManagedIdentityCredential()
            )

    return _credential

def get_openai_client():
    """Get or create Azure OpenAI client with lazy initialization"""
    global _openai_client, _token_provider

    if _openai_client is None:
        _token_provider = get_bearer_token_provider(
            get_credential(), "https://cognitiveservices.azure.com/.default"
        )
        _openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=_token_provider,
            api_version=AZURE_OPENAI_API_VERSION
        )

    return _openai_client


def build_search_authentication():
    """Local development uses the signed-in developer token. Azure uses managed identity."""
    if is_development_environment():
        search_token = get_credential().get_token("https://search.azure.com/.default")
        return {
            "type": "access_token",
            "access_token": search_token.token,
        }

    return {"type": "system_assigned_managed_identity"}


def build_data_sources():
    """Configure Azure AI Search as the grounding source for Azure OpenAI On Your Data."""
    return [
        {
            "type": "azure_search",
            "parameters": {
                "endpoint": AZURE_SEARCH_ENDPOINT,
                "index_name": AZURE_SEARCH_INDEX,
                "authentication": build_search_authentication(),
                "query_type": "semantic",
                "semantic_configuration": AZURE_SEARCH_SEMANTIC_CONFIGURATION,
                "top_n_documents": 5,
                "strictness": 3,
                "in_scope": True,
                "include_contexts": ["citations"],
                "role_information": SYSTEM_PROMPT,
                "fields_mapping": {
                    "content_fields": ["content"],
                    "title_field": "title",
                    "url_field": "url",
                },
            },
        }
    ]


def extract_citations(response):
    """Normalize citations from the Azure OpenAI response shape."""
    payload = response.model_dump()
    choices = payload.get("choices") or []
    if not choices:
        return []

    message = choices[0].get("message") or {}
    message_context = message.get("context") or {}
    message_model_extra = message.get("model_extra") or {}
    payload_model_extra = payload.get("model_extra") or {}

    citations = (
        message_context.get("citations")
        or message_model_extra.get("citations")
        or (message_model_extra.get("context") or {}).get("citations")
        or payload_model_extra.get("citations")
        or []
    )

    normalized = []
    for citation in citations:
        normalized.append(
            {
                "title": citation.get("title", ""),
                "url": citation.get("url", ""),
                "filepath": citation.get("filepath", ""),
                "content": citation.get("content", ""),
                "chunk_id": citation.get("chunk_id", ""),
            }
        )

    return normalized


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
    Chat endpoint using Azure OpenAI On Your Data.
    Retrieval still happens against Azure AI Search, but the Function app no longer
    performs search directly. This keeps the app beginner-friendly while preserving
    the closed-network RAG architecture.
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
        if not all(
            [
                AZURE_OPENAI_ENDPOINT,
                AZURE_OPENAI_DEPLOYMENT,
                AZURE_SEARCH_ENDPOINT,
                AZURE_SEARCH_INDEX,
            ]
        ):
            error_msg = "Azure configuration incomplete. Check environment variables."
            logger.error(error_msg)
            return func.HttpResponse(
                json.dumps({"error": error_msg}, ensure_ascii=False),
                mimetype="application/json",
                status_code=500
            )

        logger.info(
            "Calling Azure OpenAI On Your Data. Index: %s, semantic config: %s",
            AZURE_SEARCH_INDEX,
            AZURE_SEARCH_SEMANTIC_CONFIGURATION,
        )
        openai_client = get_openai_client()

        try:
            response = openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                stream=False,
                temperature=0.2,
                max_tokens=800,
                extra_body={
                    "data_sources": build_data_sources(),
                },
            )

            content = ""
            if response.choices:
                choice = response.choices[0]
                if choice.message.content:
                    content = choice.message.content
            citations = extract_citations(response)

            logger.info("Response generated successfully")

            return func.HttpResponse(
                json.dumps({
                    "content": content,
                    "citations": citations,
                    "sources": citations,
                }, ensure_ascii=False),
                mimetype="application/json",
                status_code=200,
                headers={
                    "Cache-Control": "no-cache"
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
