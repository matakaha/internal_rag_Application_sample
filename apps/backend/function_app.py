"""
Azure Functions backend for RAG Chat Application
Standard RAG pattern: Function App directly accesses both Azure AI Search and Azure OpenAI
"""
import azure.functions as func
import json
import logging
import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "redlist-index")

# Global client instances (initialized lazily)
_openai_client = None
_search_client = None
_credential = None
_token_provider = None

def get_openai_client():
    """Get or create Azure OpenAI client with lazy initialization"""
    global _openai_client, _credential, _token_provider
    
    if _openai_client is None:
        _credential = DefaultAzureCredential()
        _token_provider = get_bearer_token_provider(
            _credential, "https://cognitiveservices.azure.com/.default"
        )
        _openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=_token_provider,
            api_version="2024-02-15-preview"
        )
    
    return _openai_client

def get_search_client():
    """Get or create Azure AI Search client with lazy initialization"""
    global _search_client, _credential
    
    if _search_client is None:
        if _credential is None:
            _credential = DefaultAzureCredential()
        
        _search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX,
            credential=_credential
        )
    
    return _search_client


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
    Chat endpoint with standard RAG pattern
    1. Search Azure AI Search for relevant documents
    2. Send results as context to Azure OpenAI
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
        
        # Step 1: Search Azure AI Search
        logger.info(f"Searching Azure AI Search. Index: {AZURE_SEARCH_INDEX}")
        search_client = get_search_client()
        
        try:
            # Perform semantic search
            search_results = search_client.search(
                search_text=user_message,
                query_type="semantic",
                semantic_configuration_name="semantic-config",
                top=5,
                select=["japanese_name", "scientific_name", "category", "content", "rank"]
            )
            
            # Collect search results
            documents = []
            for result in search_results:
                doc = {
                    "japanese_name": result.get("japanese_name", ""),
                    "scientific_name": result.get("scientific_name", ""),
                    "category": result.get("category", ""),
                    "rank": result.get("rank", ""),
                    "content": result.get("content", "")
                }
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents")
            
        except Exception as search_error:
            error_msg = f"Azure AI Search error: {str(search_error)}"
            logger.error(error_msg, exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    "error": "検索中にエラーが発生しました",
                    "details": error_msg
                }, ensure_ascii=False),
                mimetype="application/json",
                status_code=500
            )
        
        # Step 2: Build context from search results
        if documents:
            context = "以下は検索結果から得られた情報です:\n\n"
            for i, doc in enumerate(documents, 1):
                context += f"{i}. {doc['name']} ({doc['species']})\n"
                context += f"   カテゴリ: {doc['category']}\n"
                if doc['description']:
                    context += f"   説明: {doc['description']}\n"
                context += "\n"
        else:
            context = "関連する情報が見つかりませんでした。"
        
        # Step 3: Call Azure OpenAI with context
        logger.info("Calling Azure OpenAI with search context")
        openai_client = get_openai_client()
        
        messages = [
            {"role": "system", "content": "あなたは環境省のレッドリスト（絶滅危惧種）に関する専門家アシスタントです。提供された検索結果に基づいて、ユーザーの質問に正確かつ丁寧に回答してください。検索結果に情報がない場合は、その旨を伝えてください。"},
            {"role": "user", "content": f"検索コンテキスト:\n{context}\n\nユーザーの質問: {user_message}"}
        ]
        
        try:
            response = openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                stream=False,
                temperature=0.7,
                max_tokens=800
            )
            
            # Extract response content
            content = ""
            if response.choices:
                choice = response.choices[0]
                if choice.message.content:
                    content = choice.message.content
            
            logger.info("Response generated successfully")
            
            return func.HttpResponse(
                json.dumps({
                    "content": content,
                    "sources": documents
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
