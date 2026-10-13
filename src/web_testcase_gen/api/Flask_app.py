from flask import Flask, request, jsonify
import retriveDocsFromDB
from UnstructuredDocExtraction import doc_util
from TestCaseGen import controller, utils
import os
import json
import asyncio
from datetime import datetime
import config
import logging
import socket
from py_eureka_client import eureka_client
import TestCaseGen.global_vars
from datetime import datetime

app = Flask(__name__)
app.config.from_object(config.Config)

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

try:
    eureka_client.init(
    eureka_server=app.config["EUREKA_SERVICE_URL"],
    app_name=app.config["SERVICE_NAME"],
    instance_port=app.config["PORT"],
    instance_ip = ip_address,
    instance_host = ip_address,
    )
except:
    logging.info(f'Unable to register to eureka, Error {Exception}')
    print(f'Unable to register to eureka, Error {Exception}')


logger = logging.getLogger('host')
logger.propagate = False
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')




def initialize_logger():
    # logging initialization
    logging.getLogger('RootLogger').setLevel(logging.INFO)  # Set root logger level to INFO
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)  # Remove existing handlers from root logger

    outputlog_file = os.path.join("sharedDir","logoutput.log")
    
    # If the file exists, remove it; otherwise, print message
    if os.path.isfile(outputlog_file):
        os.remove(outputlog_file)
    else:
        print('No existing log file.')

    # Set up file handler to log to file
    file_handler = logging.FileHandler(outputlog_file, mode='w')  # 'w' for overwrite
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Set timestamp for logging
    Timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Start logging
    logger.info('----------------------------------Logging started----------------------------------------')
    logger.info(f"Start Timestamp = {Timestamp}")



@app.route('/testcase-gen-using-llm/<appId>',methods=["POST"])
def generate_testcase(appId):
    logger.info(f'Testcase generation request for app id {appId} received')
    dt = datetime.now()
    print(f'Testcase generation request for app id {appId} received')
    # appId = 1173920
    scriptSelected = None
    document_purpose = "REST_API_TC" # document purpose for storing files in folders as per functionality requirement
    # create connection with PostgresSQL database
    ic_file = request.get_json() #ic is input contract    
    selected_doc_names = ic_file.get('documents')
    scriptSelected = ic_file.get('scriptSelected')
    # return scriptSelected
    condition = "appid=" + str(appId) + " and document_purpose='Rest API'" + " and (api_documentation_type = 'Business Rule/Requirement Doc' or api_documentation_type = 'Jira')" #pending for BR Field map docs and selected doc names
    
    query = "SELECT filename,pgp_sym_decrypt_bytea(filedata,'fecd2bf5f4d32f0def01978572883f2274d26863264ff5008f9eeaea7ca0be66'),api_documentation_type FROM data_assit_docs WHERE " + condition
    
    # print(f'query : {query}')
    docsFolderPath,extracted_rows_list = retriveDocsFromDB.retrieve_docs_from_db(appId,document_purpose,query)
    

    # document_purpose = "FIELD_SELECTION" # document purpose for storing files in folders as per functionality requirement
    # condition_cf = "appid=" + str(appId) + " and document_purpose='Rest API'" + " and api_documentation_type = 'Business Rule/Requirement Field Map'" #for BR Field map docs 
    # query_cf = "SELECT filename,pgp_sym_decrypt_bytea(filedata,'fecd2bf5f4d32f0def01978572883f2274d26863264ff5008f9eeaea7ca0be66'),api_documentation_type FROM data_assit_docs WHERE " + condition
    # docsFolderPath_cf,extracted_rows_list_cf = retriveDocsFromDB.retrieve_docs_from_db(appId,document_purpose_cf,query_cf)
    processed_cf = None
    if scriptSelected == 'true' or scriptSelected:
        processed_cf = process_conf_table(appId, selected_doc_names)
        print(processed_cf)
        processed_cf = processed_cf.get_json()
        # return jsonify(processed_cf)
 
    doc_data = []
    BR_data = list() #make it a dict or list so that multiple docs can be added.
    print(f'doc path {docsFolderPath}')
    try:
        if docsFolderPath!=None and len(extracted_rows_list)!=0:
            for fileName in os.listdir(docsFolderPath):
                if fileName in selected_doc_names:
                    # return fileName
                    print('fileName is ',fileName)
                    filePath = os.path.join(docsFolderPath,fileName)
                    print(fileName, '-',filePath)
                    BR_data.append(doc_util.info_extraction_model(filePath,fileName)) 
                    logger.info(f'BR Data is {BR_data}')
                    print(f'BR Data is {BR_data}')
                    # return BR_data
    except Exception as e:
        logger.error(f'Error occured while extracting BR_data {e}')
        return f"BR Doc not uploaded for appId {appId} or {e}, {os.listdir(docsFolderPath)}"

    try:
        if BR_data:
            API_name = ic_file['apiName']
            if scriptSelected == "true" or scriptSelected == True:
                output_contract = asyncio.run(controller.main(BR_data,ic_file,API_name,dt, True,processed_cf))
            else:
                output_contract = asyncio.run(controller.main(BR_data,ic_file,API_name,dt, False))       
            return jsonify(output_contract)
        else:
            return [{'error':f"BR Docs {selected_doc_names} not found in DB or No Data in uploaded docs"}]
    except Exception as e:
        logger.error(e)


@app.route('/process-confluence-data/<appId>/<DocName>',methods = ['GET'])
def process_conf_table(appId,DocName):
    logger.info('Request recieved for confluence processing')
    # DocNameList = list()
    # DocNameList.append(DocName)
    # doc_names_str = ', '.join(f"'{name}'" for name in DocName)
    # doc_names_str =  f'"{DocName[1:-1]}"'
    document_purpose = "FIELD_SELECTION"
    condition_cf = f"appid= {str(appId)} and document_purpose='Rest API' and api_documentation_type = 'Business Rule/Requirement Field Map'"
    # print(condition_cf)
    query = "SELECT filename,pgp_sym_decrypt_bytea(filedata,'fecd2bf5f4d32f0def01978572883f2274d26863264ff5008f9eeaea7ca0be66'),api_documentation_type FROM data_assit_docs WHERE "
    # return condition_cfu
    
    docsFolderPath_cf, extracted_rows_list_cf = retriveDocsFromDB.retrieve_docs_from_db(appId,document_purpose,query+condition_cf)
    # return str(extracted_rows_list_cf)
    cf_data_unprocessed = dict()
    # return [extracted_rows_list_cf,condition_cf]
    try:
        if docsFolderPath_cf!=None and len(extracted_rows_list_cf)!=0:
            for fileName in os.listdir(docsFolderPath_cf):
                if fileName in DocName:
                    print('fileName is ',fileName)
                    filePath = os.path.join(docsFolderPath_cf,fileName)
                    print(fileName, '-',filePath)
                    cf_data_unprocessed = (doc_util.info_extraction_model(filePath,fileName)) 
                    logger.info(f'CF data is {cf_data_unprocessed}')
                    # return cf_data_unprocessed
                # print(f'CF Data is {cf_data_unprocessed}')
                # return BR_data
    except Exception as e:
        logger.error(f'Error occured while extracting CF data {e}')
        raise Exception(f"CF data not uploaded for appId {appId}")
        # return e

    try:
        # return ({"cf_data" : cf_data_unprocessed})
        processed_cf_data = (utils.extract_consumer_names_with_hierarchy(cf_data_unprocessed))
        return jsonify(processed_cf_data)
    except Exception as e:
        logger.error(f'Error occured while processing confluence data {e}')
        raise Exception(f'Error occured while processing confluence data {e}')





@app.route('/info',methods=['GET'])
def info():
    logger.info(f'Server is running, time:{datetime.now()}')
    return f'Server is running, time:{datetime.now()}'

@app.route('/dummy_api/<appId>',methods=["POST"])
def dummy_api(appId):
    ic_file = request.get_json() #ic is input contract    
    print('in dummy_api')
    output = [{'TestCaseAlias': 'TestCase_1', 'TestCaseDescription': 'An organization can create multiple contracts for each product version.', 'TestCaseName': 'TestCase_1', 'BrDescription': 'An organization can have multiple contracts for different product versions.', 'BrId': '1205', 'TestData': {'body': [], 'parameters': []}, 'Validation': {'expectedResult': 'Pass', 'expectedValue': '', 'operator': '=', 'validationType': 'status code'}}, {'TestCaseAlias': 'TestCase_2', 'TestCaseDescription': 'An organization can update existing contracts for each product version.', 'TestCaseName': 'TestCase_2', 'BrDescription': 'An organization can have multiple contracts for different product versions.', 'BrId': '1205', 'TestData': {'body': [{'fieldDataType': 'numeric', 'fieldName': 'id', 'fieldValue': '1'}, {'fieldDataType': 'numeric', 'fieldName': 'orgid', 'fieldValue': '1'}, {'fieldDataType': 'string', 'fieldName': 'orderformid', 'fieldValue': 'Test123'}, {'fieldDataType': 'string', 'fieldName': 'startdate', 'fieldValue': '12/23/2024'}, {'fieldDataType': 'string', 'fieldName': 'enddate', 'fieldValue': '12/31/2024'}, {'fieldDataType': 'numeric', 'fieldName': 'isdeleted', 'fieldValue': 'false'}], 'parameters': []}, 'Validation': {'expectedResult': 'Pass', 'expectedValue': '200', 'operator': '=', 'validationType': 'status code'}}, {'TestCaseAlias': 'TestCase_2', 'TestCaseDescription': 'An organization can update existing contracts for each product version.', 'TestCaseName': 'TestCase_2', 'BrDescription': 'An organization can have multiple contracts for different product versions.', 'BrId': '1205', 'TestData': {'body': [{'fieldDataType': 'numeric', 'fieldName': 'id', 'fieldValue': '1'}, {'fieldDataType': 'numeric', 'fieldName': 'orgid', 'fieldValue': '1'}, {'fieldDataType': 'string', 'fieldName': 'orderformid', 'fieldValue': 'Test123'}, {'fieldDataType': 'string', 'fieldName': 'startdate', 'fieldValue': '12/23/2024'}, {'fieldDataType': 'string', 'fieldName': 'enddate', 'fieldValue': '12/31/2024'}, {'fieldDataType': 'numeric', 'fieldName': 'isdeleted', 'fieldValue': 'false'}], 'parameters': []}, 'Validation': {'expectedResult': 'Pass', 'expectedValue': '200', 'operator': '=', 'validationType': 'status code'}}, {'TestCaseAlias': 'TestCase_2', 'TestCaseDescription': 'An organization can update existing contracts for each product version.', 'TestCaseName': 'TestCase_2', 'BrDescription': 'An organization can have multiple contracts for different product versions.', 'BrId': '1205', 'TestData': {'body': [{'fieldDataType': 'numeric', 'fieldName': 'id', 'fieldValue': '1'}, {'fieldDataType': 'numeric', 'fieldName': 'orgid', 'fieldValue': '1'}, {'fieldDataType': 'string', 'fieldName': 'orderformid', 'fieldValue': 'Test123'}, {'fieldDataType': 'string', 'fieldName': 'startdate', 'fieldValue': '12/23/2024'}, {'fieldDataType': 'string', 'fieldName': 'enddate', 'fieldValue': '12/31/2024'}, {'fieldDataType': 'numeric', 'fieldName': 'isdeleted', 'fieldValue': 'false'}], 'parameters': []}, 'Validation': {'expectedResult': 'Pass', 'expectedValue': '200', 'operator': '=', 'validationType': 'status code'}}, {'TestCaseAlias': 'TestCase_2', 'TestCaseDescription': 'An organization can update existing contracts for each product version.', 'TestCaseName': 'TestCase_2', 'BrDescription': 'An organization can have multiple contracts for different product versions.', 'BrId': '1205', 'TestData': {'body': [{'fieldDataType': 'numeric', 'fieldName': 'id', 'fieldValue': '1'}, {'fieldDataType': 'numeric', 'fieldName': 'orgid', 'fieldValue': '1'}, {'fieldDataType': 'string', 'fieldName': 'orderformid', 'fieldValue': 'Test123'}, {'fieldDataType': 'string', 'fieldName': 'startdate', 'fieldValue': '12/23/2024'}, {'fieldDataType': 'string', 'fieldName': 'enddate', 'fieldValue': '12/31/2024'}, {'fieldDataType': 'numeric', 'fieldName': 'isdeleted', 'fieldValue': 'false'}], 'parameters': []}, 'Validation': {'expectedResult': 'Pass', 'expectedValue': '200', 'operator': '=', 'validationType': 'status code'}}]
    print('in dummy_api')

    return jsonify(output)
    

if __name__ == "__main__":
    try:
        initialize_logger()

        logger.info("STARTING SERVER")
        app.run( port=app.config["PORT"])
        logger.info('Server Started')
        
    except:
        logger.exception("Could not start server.")
        raise Exception
