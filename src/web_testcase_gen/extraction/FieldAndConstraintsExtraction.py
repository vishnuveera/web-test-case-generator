import os
import json
import uuid
from typing import List, Dict, Any
import tiktoken
from dotenv import load_dotenv
import logging
# --- 1. IMPORT FROM YOUR UTILS FILE ---
from WebTestCaseGen.llm_utils import create_llm, call_llm_formatted_response, call_llm_string_response

# --- CONFIGURATION ---
load_dotenv() # Load environment variables from .env file

TOKEN_THRESHOLD = 60000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def initialise_logger():
    
    global logger
    # Define log format and formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - Line:%(lineno)d - Thread:%(thread)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # ---------------- Logger 1: Feature Extraction Logger ----------------
    logger = logging.getLogger('Fields')

    # Set the logging level for the logger
    logger.setLevel(logging.DEBUG)  # Capture all logs, change to INFO if you prefer less verbosity

    # Log file path
    logFileName = 'FieldsExtraction.log'
    outputlog_file_Part1 = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles', 'Logs', logFileName)
    
    # Ensure that the directory exists
    os.makedirs(os.path.dirname(outputlog_file_Part1), exist_ok=True)

    # File handler for writing logs to a file
    file_handler1 = logging.FileHandler(outputlog_file_Part1, mode='a')  # Append mode
    file_handler1.setFormatter(formatter)
    logger.addHandler(file_handler1)

    # Stream handler for writing logs to the console (stdout)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)




# Create the client globally
# NOTE: Ensure the arguments below match exactly what your create_llm function expects.
# Common variations are (api_key, api_version, azure_endpoint, model)
client = create_llm()

# --- HELPER FUNCTIONS ---

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_next_version(output_dir: str) -> str:
    if not os.path.exists(output_dir): return "v1"
    versions = [d for d in os.listdir(output_dir) if d.startswith("v") and d[1:].isdigit()]
    if not versions: return "v1"
    version_nums = sorted([int(v[1:]) for v in versions])
    return f"v{version_nums[-1] + 1}"

def save_versioned_output(data: List[Dict], base_output_dir: str):
    version = get_next_version(base_output_dir)
    versioned_dir = os.path.join(base_output_dir, version)
    os.makedirs(versioned_dir, exist_ok=True)
    out_path = os.path.join(versioned_dir, "fields_and_constraints.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out_path

# --- CORE LOGIC: PREPARE PROMPT ---

def prepare_prompt_for_feature(feature: Dict) -> Dict:
    feature_id = feature.get("feature_id")
    featureName = feature.get("featureName")
    featureDescription = feature.get('description')
    category = feature.get('category')
    chunks = feature.get("chunks", [])
    
    # Extract images directly from the JSON object
    image_objects = feature.get("associatedImages", [])
    
    print(f'Processing {len(image_objects)} images for feature: {featureName}')

    full_text = ""
    for chunk in chunks:
        heading = chunk.get("heading") or "<No Heading>"
        txt = chunk.get("text") or chunk.get("chunk_text") or ""
        full_text += f"\n\n### Heading: {heading}\n{txt}"

    # JSON Structure (Must include "response" key)
    json_structure = """
    {
      "response": {
          "feature_name": "<string>",
          "fields": [
            {
              "fieldName": "<string>",
              "fieldType": "<string>",
              "dataType": "<string>",
              "required": { "value": "<bool>", "extracted": "<bool>" },
              "constraints": {
                "stringConstraints": {
                    "minLength": {
                        "value": 3,
                        "extracted": true
                    },
                    "maxLength": {
                        "value": 20,
                        "extracted": false
                    },
                    "allowedUppercase": {
                        "value": true,
                        "extracted": false
                    },
                    "allowedLowercase": {
                        "value": true,
                        "extracted": false
                    },
                    "allowedDigits": {
                        "value": true,
                        "extracted": false
                    },
                    "allowedSpecialChars": {
                        "value": "@_#",
                        "extracted": false
                    },
                    "allowSpaces": {
                        "value": false,
                        "extracted": false
                    }
                },
                "dateConstraints": {
                    "format": {
                        "value": "DD-MM-YYYY",
                        "extracted": true
                    },
                    "minDate": {
                        "value": "01-01-1900",
                        "extracted": true
                    },
                    "maxDate": {
                        "value": "31-12-2099",
                        "extracted": true
                    }
                },
                "enumConstraints": {
                    "allowedValues": {
                        "value": [
                            "ACCOUNTS",
                            "HR",
                            "SALES"
                        ],
                        "extracted": true
                    }
                },
                "numericConstraints": {
                    "minValue": {
                        "value": 1000000000,
                        "extracted": false
                    },
                    "maxValue": {
                        "value": 9999999999,
                        "extracted": false
                    },
                    "decimalPlaces": {
                        "value": 9999999999,
                        "extracted": false
                    }
                }
            },}

          ],

          "businessRules": [{
            "rule": "Description of the rules",
            "appliesTo": ["fieldName1", "fieldName2"], //name of fields where rule is applicaible
            "extracted": "<true|false>"  //true if rule is extracted from given data esle false
            }]
      }
    }"""


    prompt = f"""
    Context: {full_text}

    Analyze the feature "{featureName}" using the text and attached images.

    Description of the feature : {featureDescription}
    category of feature : {category}

    Extract input fields, constraints, and business rules.
    Return strictly JSON matching the structure below.
    IMPORTANT: The root object must have a key named "response".

    Structure:
    {json_structure}
    """

    # Build Payload
    images_payload = []
    for img_obj in image_objects:
        b64_string = img_obj.get("imageBase64")
        if b64_string:
            images_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_string}"}
            })
    
    return {
        "feature_id": feature_id,
        "messages": [
            {
                "role": "user",
                "content": images_payload + [{"type": "text", "text": prompt}]
            }
        ]
    }

def split_chunks(feature: Dict, token_limit: int = 6000) -> List[List[Dict]]:
    batches = []
    current_batch = []
    current_tokens = 0
    for chunk in feature.get("chunks", []):
        txt = chunk.get("text") or chunk.get("chunk_text") or ""
        
        # Skip empty chunks
        if not chunk.get("heading") and len(txt.split()) < 10: 
            continue
            
        token_count = estimate_tokens(txt)
        if current_tokens + token_count > token_limit:
            if current_batch: batches.append(current_batch)
            current_batch = [chunk]
            current_tokens = token_count
        else:
            current_batch.append(chunk)
            current_tokens += token_count
    if current_batch: batches.append(current_batch)
    return batches

# --- CORE LOGIC: PROCESSOR ---


def process_features_with_hybrid_strategy(feature: Dict, client_obj) -> Dict:
    final_results = []
    print('Processing features...')

    print(f'\nFeature: {feature.get("featureName", "Unknown")}')
    
    feature_id = feature.get("feature_id") or str(uuid.uuid4())
    feature["feature_id"] = feature_id

    # 1. Consolidate Images
    collected_images = []
    seen_names = set()
    
    imgs = feature.get("associatedImages", [])
    if isinstance(imgs, list):
        for img in imgs:
            if isinstance(img, dict) and "imageBase64" in img:
                name = img.get("name", str(uuid.uuid4()))
                if name not in seen_names:
                    collected_images.append(img)
                    seen_names.add(name)
    
    feature["associatedImages"] = collected_images
    
    # 2. Estimate Tokens
    full_text = " ".join([c.get("text") or c.get("chunk_text") or "" for c in feature.get("chunks", [])])
    full_token_estimate = estimate_tokens(full_text)

    # 3. Process
    if full_token_estimate <= TOKEN_THRESHOLD:
        print("Strategy: Single Pass")
        prompt_dict = prepare_prompt_for_feature(feature)
        
        result = call_llm_formatted_response(prompt_dict["messages"], client_obj)
        
        # Error check
        if result is None:
            print("Warning: LLM returned None.")
            result = {} 

        result = result.get('response')
        result['description'] = feature.get('description',None)
        result["category"] = feature.get('category',None)
        # result['docName'] = feature.get('docName', None)
        # result['pageNo'] = [str(pg) for pg in feature.get('pageNo',None)]

        # result["strategy_used"] = "single_call"
        # result["feature_id"] = feature_id 
        result["chunks"] = feature.get("chunks", [])
        result["associatedImages"] = feature.get("associatedImages", [])

        final_results = result
    else:
        print("Strategy: Multi-Batch Split")
        batched_chunks = split_chunks(feature)
        memory_buffer = ""
        all_partial = []

        for i, chunk_batch in enumerate(batched_chunks):
            batch_feature = {**feature, "chunks": chunk_batch} 
            batch_feature["associatedImages"] = feature["associatedImages"]
            
            prompt_dict = prepare_prompt_for_feature(batch_feature)
            if memory_buffer:
                prompt_dict["messages"].insert(0, {"role": "assistant", "content": memory_buffer})
            
            output = call_llm_formatted_response(prompt_dict["messages"], client_obj)
            
            if output is None: output = {}

            memory_buffer += "\n\n" + json.dumps(output)
            all_partial.append(output)

        merged_result = all_partial[-1] if all_partial else {}
        merged_result["strategy_used"] = "multi_batch"
        merged_result["feature_id"] = feature_id
        final_results = merged_result

    logger.info(f'results : {final_results}')

    
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir', 'ir_output','WebTestCaseFiles', 'Field.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(testcases_json, f)
        except:
            logger.info('Exception while saving response')    
            
    
    return final_results


# --- MAIN ENTRY POINT ---

def main(features_obj, output_base_dir):

    initialise_logger()
    logger = logging.getLogger('Fields')
    
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles', 'req_fieldExtraction.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(features_obj, f)
        except:
            logger.info('Exception while saving request') 

        
    # This grabs the 'client' variable created at the top of this file
    global client
    results = []
    # Safety Check: If client wasn't created, stop here
    if 'client' not in globals() or client is None:
        raise NameError("LLM Client is not defined. Check your API keys and create_llm call.")

    # if not isinstance(features_obj, list):
    #     raise ValueError("Main expects a LIST of features as input.")

    # Process
    # if isinstance(features_obj, dict):
    #     for featureName, features_data_list in features_obj.items():
    #         results.extend(process_features_with_hybrid_strategy(features_data_list, client))
            
    # elif isinstance(features_obj, list):
    #     results.extend(process_features_with_hybrid_strategy(features_obj, client))
    
    results = process_features_with_hybrid_strategy(features_obj, client)
    
    # Save Output
    saved_path = save_versioned_output(results, base_output_dir=output_base_dir)
    logger.info("\nProcessing Complete.")
    return results


if __name__ == "__main__":
    with open(r'C:\Users\2584177\WEB_CODE\outputFolders\irctc tatkal\cat3\FeatureExtraction\featureOutput.json', 'r') as f:
        features_obj  = json.load(f)
    output_dir = r'C:\Users\2584177\WEB_CODE\outputFolders\irctc tatkal\cat3\FieldExtraction'
    # print(features_list)
    # print(features_list.keys())
    result, saved_path = main(features_obj, output_dir)