from langchain.prompts.prompt import PromptTemplate
# from langchain.chains import ConversationChain, Chain
import json
from typing import List, Dict
from WebTestCaseGen.llm_utils import create_llm, call_llm_formatted_response
import logging
import os


def initialise_logger():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - Line:%(lineno)d - Thread:%(thread)d-  %(message)s', datefmt='%Y-%m-%d')
    # ---------------- Logger 1: General Logger ----------------
    logger = logging.getLogger('TestCase')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    #logger.setLevel(logging.DEBUG)

    logFileName = 'TestCase.log'
    
    outputlog_file_Part1 = os.path.join('sharedDir','ir_output','WebTestCaseFiles','Logs', logFileName)
    # global file_handler1
    file_handler1 = logging.FileHandler(outputlog_file_Part1, mode='a')
    file_handler1.setFormatter(formatter)
    
    logger.addHandler(file_handler1)
    




logger = logging.getLogger('TestCase')

llm = create_llm()


def remove_objects_with_null_value(obj):
    """
    Recursively remove any dict that contains a key `value`
    whose value is None.
    """
    if isinstance(obj, dict):
        # If this object has a 'value' field explicitly set to None → remove it
        if "value" in obj and obj["value"] is None:
            return None

        cleaned = {}
        for k, v in obj.items():
            cleaned_v = remove_objects_with_null_value(v)
            if cleaned_v is not None:
                cleaned[k] = cleaned_v

        return cleaned

    elif isinstance(obj, list):
        cleaned_list = []
        for item in obj:
            cleaned_item = remove_objects_with_null_value(item)
            if cleaned_item is not None:
                cleaned_list.append(cleaned_item)
        return cleaned_list

    else:
        return obj

# scenario_dict_full[0]['fields'] = remove_objects_with_null_value(scenario_dict_full[0].get('fields'))


from langchain.prompts.prompt import PromptTemplate
from tqdm import tqdm 


def generate_testcases(scenario_dict: List, meta_data: Dict) -> Dict:
    description_temp_str1 = """You are an expert QA Testcase Generator.

    Goal:
    From a single test scenario, generate multiple detailed and logically distinct testcase description and other fields mentioned in the following required JSON structure.

    Reasoning:
    Think step-by-step internally about:
    1. All possible user actions
    2. Field-level validations
    3. Positive, negative, and boundary variations
    4. UI validations, data validations, and error-handling
    5. Preconditions and postconditions
    6. Test data combinations

    DO NOT reveal your chain-of-thought. Only output the final JSON array.

    ---

    Input Scenario:
    Scenario Description : {scenarioDescription}
    Scenario Expected Result : {scenarioResult}
    Scenario Steps : {scenarioSteps}
    Scenario Type : {scenarioType}
    Field details : {fieldList}
    Rules Applicable : {rulesList}
    ---

    Instructions:

    1. Generate multiple (at least one positive and negative) testcase description which can be derived from the scenario.
    2. Each testcase must have a unique description and purpose.
    3. “type” must be one of: ["Positive", "Negative", "Boundary"].
    4. “priority” must be one of: ["P0", "P1", "P2"] based on impact.
    5. “precondition” should include login page loaded, valid credentials available, etc.
    6. “testSteps” must be clear, numbered, action-oriented.
    7. “expectedResult” must align precisely with steps.

    Output Rules:
    - Respond **only** with the JSON array.
    - No explanations, no text outside JSON.
    """


    description_temp_str = """
    Role : You are an expert QA Testcase Generator

    Inputs:
    Scenario Description : {scenarioDescription}
    Scenario Expected Result : {scenarioResult}
    Scenario Steps : {scenarioSteps}
    Scenario Type : {scenarioType}
    Field details : {fieldList}
    Rules Applicable : {rulesList}


    Task:
    Generate **multiple detailed and logically distinct test cases** that collectively cover the scenario.

    Coverage requirements:
    - Include **positive, negative, and boundary** test cases
    - Include **field validation and UI behavior** where applicable
    - Ensure **each test case validates a distinct objective**
    - Do NOT generate trivial variations

    Output rules (STRICT):
    1. Respond with **ONLY a JSON array**.
    2. The array must contain **MORE THAN ONE** test case object.
    3. Each test case must follow EXACTLY this schema:
    {schema}
    4. `tc_id` values must be unique and sequential (TC_01, TC_02, ...).
    5. `testSteps` must be concise, ordered, and contain no implementation details.
    6. `testData` must include realistic sample values for all relevant input fields.
    7. Output must be **strictly valid JSON** (no comments, no trailing commas, no extra keys).
    8. Do NOT include explanations, notes, markdown, or text outside the JSON.
    9. Do NOT reveal chain-of-thought or reasoning.

    Now generate the JSON array.
    """

    description_temp_str2 = """Role : You are an expert QA Testcase Generator

        Inputs:
        Scenario Description : {scenarioDescription}
        Scenario Expected Result : {scenarioResult}
        Scenario Steps : {scenarioSteps}
        Scenario Type : {scenarioType}
        Field details : {fieldList}
        Rules Applicable : {rulesList}

        Task:
        Generate multiple detailed and logically distinct test cases that collectively cover the scenario.

        Coverage requirements:
        1. Include positive, negative, and boundary test cases
        2. Include field validation and UI behavior where applicable
        3. Ensure each test case validates a distinct objective
        4. Do NOT generate trivial variations

        Test Data Constraints (CRITICAL – MUST FOLLOW)
        1. testData MUST contain every field defined in Field details
        2. NO field from Field details may be omitted in testData
        3. testData MUST NOT contain any field that is NOT present in Field details
        4. Even for negative or boundary cases, ALL fields must be present with appropriate values
        5. Fields may only be excluded IF AND ONLY IF explicitly instructed in the input
        6. Field names in testData must exactly match the names in Field details (no renaming, no aliases)

        Output rules (STRICT):
        1. Respond with ONLY a JSON array
        2. The array must contain MORE THAN ONE test case object
        3. Each test case must follow EXACTLY this JSON schema: {schema}
        4. testCaseId values must be unique and sequential (TC_01, TC_02, …)
        5. testSteps must be concise, ordered, and contain no implementation details
        6. testData must include realistic sample values for ALL fields listed in Field details and ONLY those fields
        7. Output must be strictly valid JSON (no comments, no trailing commas, no extra keys)
        8. Do NOT include explanations, notes, markdown, or text outside the JSON
        9. Do NOT reveal chain-of-thought or reasoning
        
        Now generate the JSON array."""


    schema = str({
    "type": "object",
    "required": ["testcases"],
    "additionalProperties": 'false',
    "properties": {
        "testcases": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "required": [
            "testCaseId",
            "description",
            "type",
            "priority",
            "precondition",
            "testSteps",
            "testData",
            "expectedResult",
            "postcondition"
            ],
            "additionalProperties": 'false',
            "properties": {
            "testCaseId": {
                "type": "string",
                "pattern": "^TC_[0-9]+$"
            },
            "description": {
                "type": "string",
                "minLength": 1
            },
            "type": {
                "type": "string",
                "enum": [
                "Positive",
                "Negative",
                "Boundary",
                "UI",
                "Security",
                "Integration"
                ]
            },
            "priority": {
                "type": "string",
                "enum": ["P0", "P1", "P2", "P3"]
            },
            "precondition": {
                "type": "string"
            },
            "testSteps": {
                "type": "array",
                "minItems": 1,
                "items": {
                "type": "string",
                "minLength": 1
                }
            },
            "testData": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {
                "type": ["string", "number", "boolean"]
                }
            },
            "expectedResult": {
                "type": "string",
                "minLength": 1
            },
            "postcondition": {
                "type": "string"
            }
            }
        }
        }
    }
    })



    desc_obj = list()

    description_temp = PromptTemplate(template=description_temp_str2, input_variables=['scenarioDescription','scenarioResult','scenarioSteps','scenarioType','fieldList','rulesList','schema'])
    scenario_dict["fields"] = remove_objects_with_null_value(meta_data.get('fields'))

    description_gen_prompt = description_temp.format(scenarioDescription = scenario_dict.get('description'),scenarioResult = scenario_dict.get('expectedResult'),  scenarioSteps = scenario_dict.get('steps'), scenarioType = scenario_dict.get('type'), fieldList = meta_data.get('fields'),rulesList = meta_data.get('businessRules',[]), schema = schema)

    system_msg = {
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": "You are an expert QA test engineer who writes detailed and meaningful testcase descriptions."
        }
    ]
    }
    messages = [system_msg]

    content = [
        {
            "type": "text",
            "text": description_gen_prompt
        }
    ]

    try:
        images_payload = list()
        if meta_data.get("associatedImages"):
        
            for img_obj in meta_data["associatedImages"]:
                # print('adding image in payload')
                b64_string = img_obj.get("imageBase64")
                if b64_string:
                    images_payload.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_string}"}
                    })

        
    except:
        print('Error in attaching images!')


    messages.append({
        "role": "user",
        "content":  images_payload +  content
    })
    
    

    response = call_llm_formatted_response(messages, llm)
    if "response" in response.keys():
        response = response.get('response')
    logger.info(f'Response : {response}')
    logger.info(f'Response type : {type(response)}')
    
    scenarioId = scenario_dict.get('testScenarioId')
    logger.info(f"Type of testcases : {response.get('testcases')}")
    logger.info(f"Testcases : {response.get('testcases')}")
    
    for testcase in response.get('testcases'):
        if not isinstance(testcase, dict):
            try:
                testcase = ast.literal_eval(testcase)
                logger.info('Converted testcase to type dict')
            except:
                logger.info('Testcase type not dict and failed to convert')
                continue
        testcase['testScenarioId'] = scenarioId
        testcase['testSteps'] = str(testcase.get('testSteps'))
        testcase['testData'] = str(testcase.get('testData'))
        
    desc_obj.extend(response.get('testcases'))
    # break

    return desc_obj









def main(scenario_json: Dict) -> List:
    
    initialise_logger()
    testcases_json = list()
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles', 'req_testcase.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(scenario_json, f)
        except:
            logger.info('Exception while saving request') 

        
    # for sc_data in tqdm(scenario_json):
    meta_data = scenario_json.get('metaData')

    for scenario in tqdm(scenario_json.get('scenarios')):
        testcase = generate_testcases(scenario, meta_data)  
        testcases_json.extend(testcase)

    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles','testCases.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(testcases_json, f)
        except:
            logger.info('Exception while saving response')    
            
        # break
    return testcases_json



if __name__ == "__main__":
    
    scenario_path = r'C:\Users\2584177\WEB_CODE\outputFolders\SBS\cat3\Scenario\TestScenarios.json'

    testcases_path = r'C:\Users\2584177\WEB_CODE\outputFolders\SBS\cat3\TestCases\testCases.json'
    
    with open(scenario_path,'r') as f:
        scenario_data = json.load(f)

    testcase_list = main(scenario_data)

    # with open(testcases_path,'w') as f:
    #     json.dump(testcase_list, f)