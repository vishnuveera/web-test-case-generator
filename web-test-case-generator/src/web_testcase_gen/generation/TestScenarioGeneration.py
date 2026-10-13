import json
from typing import List, Dict
import os
import openai
import base64
import traceback
from openai import AzureOpenAI,APITimeoutError
from WebTestCaseGen.llm_utils import create_llm, call_llm_formatted_response
import logging 
from datetime import datetime
import sys
import copy
from tqdm import tqdm

def initialise_logger():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - Line:%(lineno)d - Thread:%(thread)d-  %(message)s', datefmt='%Y-%m-%d')
    # ---------------- Logger 1: General Logger ----------------
    logger = logging.getLogger('TestScenario')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    #logger.setLevel(logging.DEBUG)

    logFileName = 'ScenarioLog.log'
    
    outputlog_file_Part1 = os.path.join('sharedDir','ir_output','WebTestCaseFiles','Logs', logFileName)
    # global file_handler1
    file_handler1 = logging.FileHandler(outputlog_file_Part1, mode='a')
    file_handler1.setFormatter(formatter)
    
    logger.addHandler(file_handler1)
    

global llm


llm = create_llm()

# print(llm.invoke('Generate a JSON which is valid',response_format={"type": "json_object"}))
logger = logging.getLogger('TestScenario')




def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")



# Builds the LLM prompt using fields, rules, and context
def build_prompt(feature_name: str, fields: List[Dict], business_rules: List[str], chunks: str, n_scenarios: int, ) -> str:
    def format_field(f: Dict) -> str:
        parts = [f"**{f['fieldName']}**"]
        parts.append(f"Type: {f['fieldType']}")
        parts.append(f"DataType: {f['dataType']}")
        if f.get('required'):
            parts.append(f"Required: {'Yes' if f.get('required', {}).get('value') else 'No'}")

        constraints = f.get("constraints", {})

        # Format string constraints
        sc = constraints.get("stringConstraints", {})
        if sc:
            str_constraints = [f"{k}: {v['value']}" for k, v in sc.items() if v.get("value") is not None]
            if str_constraints:
                parts.append("String Constraints: " + "; ".join(str_constraints))

        # Format numeric constraints
        nc = constraints.get("numericConstraints", {})

        if nc:
            logger.info(f'Numeric constraint object : {nc}')
            num_constraints = [f"{k}: {v['value']}" for k, v in nc.items() if v.get("value") is not None]
            if num_constraints:
                parts.append("Numeric Constraints: " + "; ".join(num_constraints))

        # Format date constraints
        dc = constraints.get("dateConstraints", {})
        if dc:
            date_constraints = [f"{k}: {v['value']}" for k, v in dc.items() if v.get("value") is not None]
            if date_constraints:
                parts.append("Date Constraints: " + "; ".join(date_constraints))

        # Format enum constraints
        ec = constraints.get("enumConstraints", {}).get("allowedValues", {}).get("value", [])
        if ec:
            parts.append("Allowed Values: " + ", ".join(ec))

        # Validation messages
        val_msgs = f.get("validationMessages", [])
        if val_msgs:
            parts.append("Validation Messages: " + "; ".join(vm["text"] for vm in val_msgs))

        return "- " + " | ".join(parts)


    # def extract_text_from_chunks(chunks: List) -> List:
    #     for chunk in chunks:
    #         chunk.pop('associatedImages')
    #     return chunks
    if fields:
        field_text = "\n".join([format_field(f) for f in fields])
    else:
        field_text = ''
    if business_rules:
        rule_text = "\n".join(f"- {rule}" for rule in business_rules)
    else:
        rule_text = ''

#     prompt = f"""
# # You are an expert QA assistant.


# # ---
# # ### Critical Instructions:
# # 1. First, **identify all distinct user flows or actions** based on:
# #    - Buttons, links, or tabs visible in the image/UI.
# #    - Descriptions of features, fields, and business rules.
   
# # 2.Each test scenario must:
# # - Be **unique**
# # - Validate one specific behavior or goal
# # - Be **broad enough** that it could lead to multiple test cases later
# # - Belong to one of the following coverage types:
# #   - Positive
# #   - Negative
# #   - Boundary
# #   - Field Validation
# #   - Business Rule
# #   - UI Behavior
# #   - Integration / Flow
# # (Ensure you vary the types, and at least 3 coverage types per flow.)

# # 3.. Do NOT skip any button or possible user path. Even if it looks minor, include it as a separate flow.

# # 4.Scenarios must be **high-level** (NOT test cases) and be unique.
# # ---
# # ### Output Format:
# # Return each test scenario in **JSON format** with the following keys:
# # - `test_scenario_id`: Unique ID like TS_01, TS_02, etc.
# # - `flow_name`: The user flow this scenario belongs to (e.g., "Add Contact")
# # - `description`: High-level scenario goal (e.g., "Validate login with invalid or missing username")
# # - `type`: One of the 7 coverage types
# # - `steps`: Summary of the user/system actions involved in this scenario (NOT test case steps)
# # - `expected_result`: Outcome or behavior that should occur if the scenario is executed

# # ---

# # Example Output:

# # ```json
# # {"test_scenarios":[
#   {{
#     "test_scenario_id": "TS_01",
#     "description": "Validate login with invalid or missing username",
#     "type": "Field Validation",
#     "steps": "User attempts to log in with a blank, short, or malformed username while providing a valid password.",
#     "expected_result": "System displays an appropriate error message and prevents login."
#   }},
#   {{
#     "test_scenario_id": "TS_02",
#     "description": "Check password length constraints during login",
#     "type": "Boundary",
#     "steps": "User enters passwords that are too short, exactly at the minimum, exactly at the maximum, and longer than allowed.",
#     "expected_result": "System validates length correctly and accepts/rejects the password accordingly."
#   }},
#   {{
#     "test_scenario_id": "TS_03",
#     "description": "Ensure account is locked after multiple failed login attempts",
#     "type": "Business Rule",
#     "steps": "User tries logging in with incorrect credentials consecutively more than the allowed limit.",
#     "expected_result": "System locks the account temporarily and informs the user appropriately."
#   }}]
# }


# Feature Name: **{feature_name}**

# ### Fields:
# {field_text}

# ### Business Rules:
# {rule_text}

# ### Functional Context:
# {chunks}

# Generate as many relevant test scenarios as possible considering all possible coverages.Use details from images provided if the images are relevant.
# Remember, the test scenarios and testcases have 1:many relation so for each testscenario, there
# will be n testcases. DO NOT GENERATE JUST 1 TEST SCENARIOS, I NEED AS MANY AS POSSIBLE.
# """
    json_example = [
            {
            "testScenarioId":1,
            "flowName":"Descriptive name",
            "description":"description",
            "type":"type of coverage",
            "steps":"steps"
                },
            {
            "testScenarioId":2,
            "flowName":"Descriptive name",
            "description":"description",
            "type":"type of coverage",
            "steps":"steps"
                }

        ]
    prompt = f'''You are an expert QA assistant.

    Goal:
    Generate **high-level, abstract, reusable test scenarios** for the provided feature and all user flows visible in the UI/image.  
    These scenarios must stay at a conceptual level, because detailed field-level and step-by-step validations will be handled later when generating test cases.  
    Therefore, **we do NOT want a large number of scenarios**—only high-value, consolidated, flow-level scenarios.

    Instructions:

    1. Identify all distinct **user flows**, **UI elements**, and **user actions** visible or implied from the UI/image  
    (e.g., buttons, links, tabs, form fields, dropdowns, icons, navigation, modals, file uploads, pagination, etc.).  
    Treat each interactive element as a potential flow **only if it initiates a meaningful action**.

    2. For each identified flow, generate **high-level test scenarios**.  
    Each scenario must:
    - Describe a **single broad test objective or behavior**, not detailed test steps.  
    - Be **unique**, focusing on a distinct functional or behavioral goal.  
    - Be **general enough** to support many detailed test cases later.  
    - Belong to ONE coverage type: Positive, Negative, Boundary, Field Validation, Business Rule, UI Behavior, Integration/Flow.  
    - Contain **only summarized actions**, with no explicit inputs, values, sequences, or step-by-step operations.

    3. **Merge scenarios that essentially validate the same objective.**  
    If multiple scenarios differ only in low-level specifics or examples, combine them into one high-level scenario.  
    Example:  
    - “Validate that username accepts allowed characters”  
    - “Validate that a user logs in successfully with valid credentials”  
    → should be merged into: “Validate successful login using valid credentials.”

    4. Do not produce redundant or overly granular scenarios.  
    Because each scenario will be expanded into multiple detailed test cases later, focus only on **core, distinct, high-level behaviors.**

    5. Do not omit any user path that results in meaningful system behavior change,  
    but avoid creating a separate scenario for every field-level variation—those belong to test cases, not scenarios.


    ### Inputs:

    Feature Name: **{feature_name}**

    ### Fields: {field_text}

    ### Business Rules: {rule_text}

    ### Functional Context: {chunks}
    

    Output format:
    Return an JSON object with key `scenarios` whose value is an array of scenario objects. Each scenario object must include:
    - `testScenarioId`: Unique ID (TS_01, TS_02, ...).
    - `flowName`: Name of the user flow the scenario belongs to.
    - `description`: A concise, high-level goal for the scenario.
    - `type`: One of the coverage types listed above.
    - `steps`: Short summary of user/system actions involved (NOT detailed step-by-step test case).
    - `expectedResult`: High-level expected outcome or system behavior.
    example JSON:
        {json_example}
        
    Notes:
    - Scenarios must be high-level (not test cases). Avoid exact input values, exact clicks-by-clicks, and implementation specifics.
    - Ensure broad coverage across types and include edge-case / error behavior.
    - Generate as many relevant scenarios as you reasonably can for the UI/image and the feature.
    - Only return a list of scenarios in the given format.
    '''

    return prompt.strip()




# Main function to generate test scenarios
def generate_test_scenarios(feature_name: str, fields: List[Dict], business_rules: List[str], chunks: str, associatedImages: List[Dict]= None , n_scenarios: int = 10) -> Dict:
    scenario_resp = list()
    logger.info(f'generating')
    user_prompt_obj = dict()
    # print('in gen scenario')
    system_msg = {
        "role": "system",
        "content": "You are an expert QA test engineer who writes detailed and meaningful test scenarios."
    }


    user_prompt = build_prompt(feature_name, fields, business_rules, chunks, n_scenarios)
    # print(user_prompt)
    # sys.exit()
    # logger.info(f" len of user prompt : {len(user_prompt)}")
    user_msg = {
        "role": "user",
        "content": user_prompt
    }

    base_messages = [system_msg, user_msg]
    logger.info(f'images > {len(associatedImages)}')
    if associatedImages:
        image_count = 0
        messages = copy.deepcopy(base_messages)
        image_paths = [imageDetails.get('imageBase64') for imageDetails in associatedImages]
        processed = False

        for image_path in image_paths:
            processed = False
            if not os.path.exists(image_path):
                print(f"[⚠] Skipping invalid image path: {image_path}")
                continue
            # print(image_path)
            try:
                base64_str = encode_image_to_base64(image_path)
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_str}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            except Exception as e:
                print(f"[⚠] Error encoding image {image_path}: {str(e)}")

            image_count += 1
            if image_count == 2:
                print("processing with 2 images")
                scenario_resp.extend(call_llm_formatted_response(messages, llm).get('scenarios'))
                image_count = 0
                messages = copy.deepcopy(base_messages)
                processed= True
            

        if processed == False:
            # print('image count <2, ',image_count)
            scenario_resp.extend(call_llm_formatted_response(messages, llm).get('scenarios'))

        # print(image_count)
    else:
        # print(f'No associated images {base_messages}')
        # print(f'messages : {base_messages}')
        scenario_resp.extend(call_llm_formatted_response(base_messages, llm).get('scenarios'))
        
    logger.info(f'resp from LLM {type(scenario_resp)}')
    logger.info(f'scenario resp from LLM : {scenario_resp}')
        
    json_path = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles', 'GeneratedScenario.json')
    try:
        with open(json_path, 'w') as f:
            json.dump(testcases_json, f)
    except:
        logger.info('Exception while saving response')    
        
    return scenario_resp



def main(data):
    initialise_logger()
    # print('loggrt done')
    # data = data[1]
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles', 'req_scenario.json')
        
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f)
        except:
            logger.info('Exception while saving request')    
    
    # for data in tqdm(data_list):
        # print(f'data : {data}')
    meta_data = dict()
    try:
        logger.info(f'feature Name : {data.get("featureName")}')
        logger.info(f'images : {len(data.get("associatedImages"))}')
        # sys.exit()
        test_scenario_output = dict()
        test_scenarios = generate_test_scenarios(data.get("featureName"), data.get("fields"), data.get("businessRules"), data.get("chunks"),data.get("associatedImages"))
        # result_obj = {
        #         "feature_name": data.get("feature_name"),
        #         "fields": data.get("fields", []),
        #         "business_rules": data.get("business_rules", []),
        #     }
        meta_data['businessRules'] = data.get("businessRules", [])
        meta_data['fields'] = data.get("fields", [])
        meta_data['associatedImages'] = data.get("associatedImages")
        test_scenario_output['scenarios'] = test_scenarios
        test_scenario_output['featureName'] = data.get('featureName')
        test_scenario_output['description'] = data.get('description')
        test_scenario_output['metaData'] = meta_data
        # test_scenario_output_list.append(result_obj)
        
    except Exception:
        exc_type, exc_val, exc_traceback = sys.exc_info()

        exception_dict = {
            "timestamp": datetime.now().isoformat(),
            'type' : str(exc_type.__name__),
            'message':str(exc_val),
            "traceback": traceback.format_exception(exc_type, exc_val, exc_traceback)
        }

        logger.info(f"Exception for {data.get('feature_name')} --- {exception_dict}")
        print(f"Exception for {data.get('feature_name')} --- {exception_dict}")
        

    # with open(r'ScenarioOutput.json','w') as f:
    #     json.dump(test_scenario_output,f)

    return test_scenario_output


if __name__ == '__main__':
    
    file_path = r"C:\Users\2584177\WEB_CODE\outputFolders\SBS\cat2\FieldExtraction\v1\fields_and_constraints.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print(len(data_list))
    scenario_list = main(data_list)

    # with open(r'C:\Users\2584177\WEB_CODE\outputFolders\SBS\cat2\Scenario\scenarios.json','w') as f:
    #     json.dump(scenario_list, f)