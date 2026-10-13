import os
# from openai import AzureChatOpenAI
from langchain_openai import AzureChatOpenAI
from typing import List, Dict
import json
from datetime import datetime
import traceback
import sys
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import ManagedIdentityCredential
from azure.core.exceptions import ClientAuthenticationError



class UAMICredential(TokenCredential):
    def __init__(self, token):
        self._token = token

    def get_token(self, *scopes, **kwargs):
        # provide AccessToken with pseudo long expiry
        return AccessToken(self._token, expires_on=9999999999)


def authenticate_with_uami():
    """
    Authenticate to Azure OpenAI using User-Assigned Managed Identity (UAMI).
    """
    # Initialize the ManagedIdentityCredential with UAMI Client ID
    credential = ManagedIdentityCredential(client_id=os.getenv('UAMI_CLIENT_ID'))
    #credential = ManagedIdentityCredential()

    try:
        # Fetch the token for Cognitive Services (OpenAI)
        token = credential.get_token(os.getenv('AZURE_AI_SCOPE'))
        #print(token.token)
        return token.token
    except ClientAuthenticationError as e:
        return None




# Creating LLM client to call LLM using langchain
def create_llm():
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        try:

            llm = AzureChatOpenAI(
                api_key = os.getenv('GPT_LLM_API_KEY'),
                api_version=  os.getenv('GPT_LLM_API_VERSION'),
                azure_endpoint = os.getenv('GPT_LLM_ENDPOINTS'),
                azure_deployment = os.getenv('GPT_MODEL_NAME'),
            )
            return llm
            
        except Exception as e:
            
            raise Exception(f"An error occurred while creating the LLM: {str(e)}")
    
    #token based authentication for prod env.
    else:
        token = authenticate_with_uami()
        if token:
            try:
                llm = AzureChatOpenAI(azure_ad_token=token,azure_endpoint=os.getenv('GPT_LLM_ENDPOINTS'),api_version=os.getenv('GPT_LLM_API_VERSION'),
                                      azure_deployment = os.getenv('GPT_MODEL_NAME'))
                return llm
            
            except Exception as e:    
                raise Exception(f'Exception {e} while creating LLM')
            

        else:
            raise Exception (f"Failed to fetch token for {os.getenv('GPT_LLM_ENDPOINTS')}")


def call_llm_string_response(messages : List[Dict], llm) -> str:
    try:
        response = llm.invoke(messages)

        return response.content

    except Exception:
        exc_type, exc_val, exc_traceback = sys.exc_info()

        exception_dict = {
            "timestamp": datetime.now().isoformat(),
            'type' : str(exc_type.__name__),
            'message':str(exc_val),
            "traceback": traceback.format_exception(exc_type, exc_val, exc_traceback)
        }

        print(f"Exception  {exception_dict}")

    return 'Error'


def call_llm_formatted_response(messages: List[Dict], llm) -> Dict:
    try:
        response = llm.invoke(
            messages,
            response_format={"type": "json_object"}
        )
        # response_json = json.loads(response.content)
        # print(type(response))
        # print(f'Response from LLM : {response}')
        return json.loads(response.content)
    except Exception:
        exc_type, exc_val, exc_traceback = sys.exc_info()

        exception_dict = {
            "timestamp": datetime.now().isoformat(),
            'type' : str(exc_type.__name__),
            'message':str(exc_val),
            "traceback": traceback.format_exception(exc_type, exc_val, exc_traceback)
        }
        # sys.exit()
        print(f"[!] Error: {exception_dict}")
        return {}

