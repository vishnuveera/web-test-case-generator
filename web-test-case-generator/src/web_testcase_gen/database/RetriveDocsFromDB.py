import os
import base64
from pathlib import Path
import logging
import psycopg2
import psycopg2.extras
from azure.identity import ManagedIdentityCredential




# import configurations_parser
logger = logging.getLogger('1')
logger.propagate = False
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')







def create_folder(appid,document_purpose):
    
    """
    Creates base folder path for the documents to be stored
    """
    
    try:
        #seperate folder for different applications based on the appid
        file_folder_path = 'Documents/'+document_purpose+'/'+str(appid)
        
        
        #file_folder_path = base_folder_path  + str(appid)
        #make the path system compatible
        PathlibCompatiblePath = file_folder_path.replace(os.sep, '/')
        osCompatibleFolderPath = Path(PathlibCompatiblePath) #osCompatibleFolderPath- Documents/application/appid

        #Create a folder at 'Documents/applications/<appid>'
        isExistFolderPath = os.path.exists(osCompatibleFolderPath)
        if not isExistFolderPath:
            os.makedirs(osCompatibleFolderPath, exist_ok = True)
    
        return osCompatibleFolderPath
    except Exception as e:
        # assistanceLogger.exception('Exception Occured while creating document folder')
        # dataGenLogger.exception('Exception Occured while creating document folder')
        # apiValidationLogger.exception('Exception Occured while creating document folder')
        pass

       
def write_decoded_data(memoryViewobj,file_name,appid,folderPath):
    
    """
    
    """
    encodings_to_try = ['utf-8', 'utf-16', 'latin-1', 'ascii']
    
    try:
        decoded_text = None
        byte_data = bytes(memoryViewobj)
        
        for encoding in encodings_to_try:
            try:
                message_bytes = base64.b64decode(byte_data)
                file_string_output = message_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                pass  # Continue to the next encoding if decoding fails
        
        if file_string_output is not None:
            file_string_output = file_string_output.replace(u'\ufeff', '') #BOM Character removed
            #apiValidationLogger.info(f'File data with removal of BOM character: {file_string_output}')
            file_string_output_encoded=file_string_output.encode(encoding)
            file_output_byte_array=bytearray(file_string_output_encoded)
        
            file_path = folderPath / file_name    #os.path.join(osCompatibleFolderPath,file_name)

            f = open(file_path,"wb")
            f.write(file_output_byte_array)
        
        
            f.close()
            # assistanceLogger.info(f'File {file_name} Decoded and stored at folder path')
            # dataGenLogger.info(f'File {file_name} Decoded and stored at folder path')
            # apiValidationLogger.info(f'File {file_name} Decoded and stored at folder path')
        else:
            # assistanceLogger.info(f'Unable to decode with any of the specified encodings')
            # dataGenLogger.info(f'Unable to decode with any of the specified encodings')
            # apiValidationLogger.info(f'Unable to decode with any of the specified encodings')
            pass
    except Exception as e:
        # assistanceLogger.exception('Exception Occured while writing decoded data to file')
        # dataGenLogger.exception('Exception Occured while writing decoded data to file')
        # apiValidationLogger.exception('Exception Occured while writing decoded data to file')
        print(e)


def parse_db_rows(extracted_rows_list,appid,document_purpose):
    """
    Inputs:
    extracted_rows_list=List of all rows extracted from database
    appid = application id 
    
    Returns:
    docsfolderPath=The path at which the documents have been stored 'Documents/applcations/<app-id>'
    
    """
    Flag = False
    api_documentation_type=""
    
    docsfolderPath = create_folder(appid,document_purpose)
    # assistanceLogger.info(f'Docs Folder Path created successfully at {docsfolderPath} ')
    # dataGenLogger.info(f'Docs Folder Path created successfully at {docsfolderPath} ')
    # apiValidationLogger.info(f'Docs Folder Path created successfully at {docsfolderPath} ')
    
    try:
        for row in range(len(extracted_rows_list)):
            file_name = extracted_rows_list[row][0]
            memoryViewobj = extracted_rows_list[row][1]
            print(f'document_purpose = {document_purpose}')
            # apiValidationLogger.info(f'document_purpose {document_purpose} ')
            if document_purpose in ['REST_API_TC','FIELD_SELECTION','WEB']:
            # if document_purpose == "REST_API_TC" or document_purpose == 'FIELD_SELECTION':
                
                Flag = True
                api_documentation_type = extracted_rows_list[row][2] #api_documentation_type-type of json file
                print(f'api_documentation_type = {api_documentation_type}')
                
            print(f' file = {memoryViewobj} \n type_of_file = {type(memoryViewobj)} \n file_name = {file_name} \n ')
            
            # assistanceLogger.info(f' file = {memoryViewobj} \n type_of_file = {type(memoryViewobj)} \n file_name = {file_name} \n ')
            # dataGenLogger.info(f' file = {memoryViewobj} \n type_of_file = {type(memoryViewobj)} \n file_name = {file_name} \n ')
            # apiValidationLogger.info(f' file = {memoryViewobj} \n type_of_file = {type(memoryViewobj)} \n file_name = {file_name} \n ')
            # 
            write_decoded_data(memoryViewobj,file_name,appid,docsfolderPath)
    
    except Exception as e:
        # assistanceLogger.exception('Exception Occured while parsing db rows')
        # dataGenLogger.exception('Exception Occured while parsing db rows')
        # apiValidationLogger.exception('Exception Occured while parsing db rows')
        pass
    
    print(f'api_documentation_type = {api_documentation_type}')
    return docsfolderPath,api_documentation_type





def retrieve_docs_from_db(appid, document_purpose, query):
    """
    Connects to the PostgreSQL database server, executes 'SELECT' query in the database, and retrieves the uploaded
    documents from the db, stores them at a specific location, and then closes the connection with the db.
    
    Input:
    appid - The application for which the documents have been uploaded
    
    Returns:
    docsfolderPath=The path at which the documents have been stored 'Documents/applications/<app-id>'
    extracted_rows_list= List of all extracted rows from db
    api_documentation_type = Type of API documentation
    """
    conn = None
    docsfolderPath = None
    extracted_rows_list = []
    api_documentation_type = None
    
    try:
        print('Connecting to the PostgreSQL database...')
        logger.info('Connecting to the PostgreSQL database...')
        
        if os.getenv('DEPLOYMENT_ENV') == 'local':
            logger.info('Deployment env Local so using username password')
            db_host = '10.100.124.69'
            db_name = 'testdatabase'
            db_user = 'postgres'
            db_password ='tcs#1234'
            conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)

        else:
            logger.info('Deployment env is not local so using token for connection')
            db_host=os.getenv('POSTGRES_HOST') #FOR PROD ENV
            db_name=os.getenv('POSTGRES_DBNAME') #FOR PROD ENV

            credential = ManagedIdentityCredential(client_id=os.getenv('UAMI_CLIENT_ID'))
            token = credential.get_token(os.getenv('AZURE_POSTGRESQL_SCOPE')).token
            logger.info(f'len of token : {len(token)}')
            logger.info(f'first 3 chars in tokens : {token[:3]}')
            
            conn = psycopg2.connect(dbname=db_name, user="anindc1digi1uami", password=token,host=db_host,sslmode="require")

        logger.info("Connected Successfully!!!")
        print("Connected Successfully!!!")
        
        # create a dictionary cursor
        cur = conn.cursor()
        
        logger.info('Executing Query in database')
        cur.execute(query)
        extracted_rows_list = cur.fetchall()
        logger.info(f'No. of fetched rows = {len(extracted_rows_list)}')
        logger.info(f'extracted rows = \n {extracted_rows_list}')
        print(f'No. of fetched rows = {len(extracted_rows_list)}')
        print(f'extracted rows = \n {extracted_rows_list}')
        
        docsfolderPath, api_documentation_type = parse_db_rows(extracted_rows_list, appid, document_purpose)
        
        # close the communication with PostgreSQL
        cur.close()
        return docsfolderPath, extracted_rows_list
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        logger.error(f"Error: {error}")
        return docsfolderPath, extracted_rows_list  # Ensure values are always returned
    
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
            logger.info('Database connection closed.')

# Example usage

