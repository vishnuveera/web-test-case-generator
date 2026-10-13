import os
import json
import base64
import subprocess
import uuid
import re
import unicodedata
import logging
import platform  # Added to detect OS
from collections import defaultdict
from dotenv import load_dotenv
from WebTestCaseGen.llm_utils import create_llm, call_llm_formatted_response, call_llm_string_response
import pypdfium2 as pdfium  # For Image Rendering
import pdfplumber  
from datetime import datetime
import traceback
import sys

import logging
import os


import logging
import os
from datetime import datetime

def initialise_logger():
    
    global logger
    # Define log format and formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - Line:%(lineno)d - Thread:%(thread)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # ---------------- Logger 1: Feature Extraction Logger ----------------
    logger = logging.getLogger('Feature')

    # Set the logging level for the logger
    logger.setLevel(logging.DEBUG)  # Capture all logs, change to INFO if you prefer less verbosity

    # Log file path
    logFileName = 'FeatureExtraction.log'
    outputlog_file_Part1 = os.path.join('sharedDir','ir_output', 'WebTestCaseFiles', 'Logs', logFileName)
    
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

    




global llm


llm = create_llm()



# Windows-specific library for DOCX conversion
try:
    from docx2pdf import convert as docx_convert
except ImportError:
    docx_convert = None

# --- Configuration ---
load_dotenv()



# Initialize global logger variable (will be set in main)

# Output Directory Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join('sharedDir', 'ir_output', 'WebTestCaseFiles')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Azure Config
# client = AzureOpenAI(
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
# )
# DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

# --- Helper Functions ---

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def is_json(text):
    try:
        json.loads(text)
        return True
    except:
        return False

def clean_json_like_string(text):
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    json_match = re.search(r'(\[\s*{.*}\s*\])', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    json_match_obj = re.search(r'(\{\s*".*"\s*:.*\})', text, re.DOTALL)
    if json_match_obj:
        return json_match_obj.group(1).strip()
    return text.strip()

def normalize_text(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.replace('’', "'").replace('\u00A0', ' ')
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*\(\s*', ' (', s)
    s = re.sub(r'\s*\)\s*', ') ', s)
    return s.lower().strip()


# --- Core Logic Class ---

class DocumentProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.job_id = f"RUN_{datetime.timestamp}"
        self.job_dir = os.path.join(OUTPUT_FOLDER, self.job_id)
        self.images_dir = os.path.join(self.job_dir, "images")
        self.extracted_images_dir = os.path.join(self.job_dir, "extracted_images")
        
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.extracted_images_dir, exist_ok=True)
        
        logger.info(f"Initialized processing. Job ID: {self.job_id}. Output directory: {self.job_dir}")

    def convert_docx_to_pdf(self):
        # 1. If input is already PDF, return it
        if self.file_path.lower().endswith(".pdf"):
            logger.info("Input is already a PDF.")
            return self.file_path

        # 2. Define output PDF path
        filename = os.path.splitext(os.path.basename(self.file_path))[0] + ".pdf"
        pdf_path = os.path.join(self.job_dir, filename)

        # 3. Detect OS and choose strategy
        current_os = platform.system()
        
        if current_os == "Windows":
            logger.info("Detected Windows OS. Using docx2pdf (Requires MS Word)...")
            
            if docx_convert is None:
                raise ImportError("Please install docx2pdf: pip install docx2pdf")
                
            try:
                # WINDOWS LOGIC (Active)
                docx_convert(self.file_path, pdf_path)
                logger.info(f"PDF generated successfully at: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.error(f"Windows conversion failed: {e}")
                raise RuntimeError("Failed to convert DOCX to PDF on Windows.")

        else: 
            # LINUX / MAC LOGIC
            logger.info("Detected Non-Windows OS (Linux/Mac).")
            try:
                logger.info("Attempting LibreOffice conversion...")
                subprocess.run([
                    "libreoffice", "--headless", "--convert-to", "pdf",
                    "--outdir", self.job_dir, self.file_path
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return pdf_path
            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice failed: {e.stderr.decode()}")
                raise RuntimeError("LibreOffice conversion failed.")

    def convert_pdf_to_images(self, pdf_path, scale=2):
        logger.info("Converting PDF to Images using pypdfium2...")
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            n_pages = len(pdf)
            image_paths = []
            
            for i in range(n_pages):
                page = pdf[i]
                pil_image = page.render(scale=scale).to_pil()
                page_filename = f"page_{i + 1}.png"
                page_path = os.path.join(self.images_dir, page_filename)
                pil_image.save(page_path, format="PNG")
                image_paths.append(page_path)

            return image_paths
        
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise e

    def detect_excluded_pages(self, image_paths, fraction=0.25, max_limit=10):
        logger.info("Detecting excluded pages (TOC, Preface, etc.)...")
        total_pages = len(image_paths)
        k = max(2, min(int(total_pages * fraction), max_limit))
        if total_pages <= 2: k = total_pages
        
        excluded_pages = []
        seen_keep = False

        for i in range(k):
            if seen_keep: break
            
            try:
                encoded_img = encode_image_to_base64(image_paths[i])
                # --- REFINED PROMPT ---
                system_instruction = """
                You are a Business Analyst filtering a document for Feature Extraction. 
                Your task is to classify if a page contains detailed Software Requirements (UI, Logic, Steps) or if it is just Metadata.
                
                CRITICAL RULES:
                1. Reply 'EXCLUDE' for:
                   - Cover Pages / Title Pages.
                   - Table of Contents (TOC) / Indexes / Agendas.
                   - Document History / Version Control tables.
                   - Legal Disclaimers / Blank pages.
                   - High-level Introductions that list features but do not describe inputs/logic.
                
                2. Reply 'KEEP' for:
                   - Pages with Screenshots of the software.
                   - Pages describing specific Input Fields, Buttons, or Validation Rules.
                   - Step-by-step user instructions (e.g., "1. Click Save").
                
                NOTE: A Table of Contents lists feature names but does not define them. This is useless for extraction. EXCLUDE it.
                
                Reply strictly with one word: 'KEEP' or 'EXCLUDE'.
                """
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}},
                        {"type": "text", "text": system_instruction}
                    ]
                }]
                try:
                    decision = call_llm_string_response(messages, llm)
                except:
                    decision = 'exclude'
                # response = client.chat.completions.create(model=DEPLOYMENT_NAME, messages=messages)
                # decision = response.choices[0].message.content.strip().lower()
                logger.info(f"Page {i+1} Decision: {decision}")
                
                if "exclude" in decision:
                    excluded_pages.append(i + 1)
                else:
                    seen_keep = True
            except Exception as e:
                logger.error(f"Error checking page {i+1}: {e}")
        
        return excluded_pages

    def analyze_images_to_extract_features(self, image_paths, excluded_pages, FILE_NAME):
        logger.info("Analyzing images for features via LLM...")
        results = []
        # memory_buffer = ""
        batch_size = 2
        
        json_feature = {
            "response": [
                {
                "featureName": "string",
                "category": "string",
                "description": "string"
                }
            ]
            }
        
            

        actual_page_numbers = [i for i in range(1, len(image_paths) + 1) if i not in excluded_pages]
        iterator = 1
        for i in range(0, len(actual_page_numbers), batch_size):
            try:
                batch_indices = actual_page_numbers[i:i + batch_size]
                batch_paths = [image_paths[j - 1] for j in batch_indices]
                
                logger.info(f"Processing pages {batch_indices}...")
                

                prompt_text = f'''
                Analyze the following {len(batch_paths)} pages, including all visible TEXT and INFORMATION PRESENT IN ATTACHED IMAGES.

                Your task is to extract **HIGH-LEVEL PRODUCT / SYSTEM FEATURES** described or implied in the content.

                Guidelines:
                - Consider both written text and visual information in images (forms, buttons, flows, labels, options).
                - Focus on **WHAT the system can do**, not UI implementation details.
                - Group similar capabilities into a single feature when appropriate.
                - Do NOT include low-level steps or screen navigation.
                - Do NOT infer features that are not explicitly or clearly implied.
                - Each feature must be meaningful at a **requirement or product level**.

                Return output in **STRICT JSON ONLY** (no extra text):
                JSON Example:
                {json_feature}
                
                '''


                images_payload = [{'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{encode_image_to_base64(p)}'}} for p in batch_paths]
                
                
                messages = [{'role': 'user', 'content': images_payload + [{'type': 'text', 'text': prompt_text}]}]
                
                #why are we inserting history in messages, not needed here
                # if memory_buffer:
                #     messages.insert(0, {'role': 'assistant', 'content': memory_buffer})

                try:
                    llm_output = call_llm_formatted_response(messages, llm)
                    # response = client.chat.completions.create(
                    #     model=DEPLOYMENT_NAME,
                    #     messages=messages,
                    #     response_format={"type": "json_object"}
                    # )
                    # llm_output = response
                    print(f'llm_output type : {type(llm_output)}')
                    # memory_buffer += "\n" + str(llm_output)
                    
                    if not is_json(llm_output) and not isinstance(llm_output, dict) and not isinstance(llm_output, list):
                        llm_output = clean_json_like_string(llm_output)
                        llm_output = json.loads(llm_output)

                    parsed = llm_output
                    items = parsed.get('response')

                    if isinstance(items, dict): items = [items]
                    
                    for obj in items:
                        logger.info(f'Objj is {obj}')
                        obj["feature_id"] = str(uuid.uuid4())
                        obj["actual_doc_page_ids"] = batch_indices
                        obj['docName'] = [FILE_NAME]
                        obj['pageNo'] = batch_indices
                        results.append(obj)
                    
                    iterator+=1
                    
                except Exception as e:
                    logger.error(f"Error in feature extraction: {e}")

            except Exception as e: 
                exc_type, exc_val, exc_traceback = sys.exc_info()

                exception_dict = {
                    "timestamp": datetime.now().isoformat(),
                    'type' : str(exc_type.__name__),
                    'message':str(exc_val),
                    "traceback": traceback.format_exception(exc_type, exc_val, exc_traceback)
                } 

                logger.error(f"Exception while analyzing images for page : {actual_page_numbers[i:i + batch_size]}\n --- \n{exception_dict}")

        logger.info(f"Found {len(results)} features.")
        return results

    def extract_text_and_images_coords(self, pdf_path, excluded_pages):
        """
        Replaced PyMuPDF (fitz) with pdfplumber + pypdfium2
        """
        logger.info("Extracting Text and Image Coordinates via pdfplumber...")
        result = []
        
        # Open PDF for rendering crops
        pdf_renderer = pdfium.PdfDocument(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    page_number = i + 1
                    if page_number in excluded_pages: continue
                    
                    page_data = {"page_number": page_number, "text_blocks": [], "images": []}
                    
                    # 1. Extract Text
                    words = page.extract_words()
                    for w in words:
                        page_data["text_blocks"].append({
                            "text": w["text"],
                            "bbox": {"x0": w["x0"], "y0": w["top"], "x1": w["x1"], "y1": w["bottom"]}
                        })

                    # 2. Extract Images (BBoxes only from pdfplumber)
                    # pdfplumber finds the location of images
                    # We use pypdfium2 to actually render that crop
                    if page.images:
                        saved_count = 0
                        renderer_page = pdf_renderer[i]
                        page_height = page.height
                        
                        for img in page.images:
                            if saved_count >= 6: break
                            
                            # pdfplumber coords: x0, top, x1, bottom
                            x0, top, x1, bottom = img["x0"], img["top"], img["x1"], img["bottom"]
                            
                            # Convert to pypdfium2 crop format
                            # pypdfium2 usually needs exact pixel sizes or scale factors, 
                            # but we can just render the page and crop the PIL image for simplicity.
                            try:
                                # Render full page at decent quality
                                pil_page = renderer_page.render(scale=2).to_pil()
                                
                                # Scale coordinates (because we rendered at scale=2)
                                w_scale = pil_page.width / page.width
                                h_scale = pil_page.height / page.height
                                
                                crop_box = (x0 * w_scale, top * h_scale, x1 * w_scale, bottom * h_scale)
                                pil_crop = pil_page.crop(crop_box)
                                
                                img_name = f"p{page_number}_img{saved_count}.png"
                                img_path = os.path.join(self.extracted_images_dir, img_name)
                                pil_crop.save(img_path)
                                
                                with open(img_path, "rb") as f:
                                    b64 = base64.b64encode(f.read()).decode("utf-8")
                                
                                page_data["images"].append({
                                    "name": img_name,
                                    "bbox": {"x0": x0, "y0": top, "x1": x1, "y1": bottom},
                                    "base64": b64
                                })
                                saved_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to crop image on p{page_number}: {e}")

                    result.append(page_data)
            

                except Exception as e: 
                    exc_type, exc_val, exc_traceback = sys.exc_info()

                    exception_dict = {
                        "timestamp": datetime.now().isoformat(),
                        'type' : str(exc_type.__name__),
                        'message':str(exc_val),
                        "traceback": traceback.format_exception(exc_type, exc_val, exc_traceback)
                    } 

                    logger.error(f"Exception while analyzing page with pdfplumber: {i} \n --- \n{exception_dict}")

        return result

    def chunk_and_associate_images(self, features, enriched_pages):
        logger.info("Chunking text and associating images...")
        pages_map = {p['page_number']: p for p in enriched_pages}
        final_output = []
        
        grouped_features = defaultdict(list)
        logger.info(f'Features : {features}')
        for f in features:
            logger.info('--------------------------------')
            logger.info(f'feature is : {f}')
            grouped_features[f['featureName'].strip().lower()].append(f)

        for fname, group in grouped_features.items():
            all_page_ids = set()
            all_headings = []
            for item in group:
                all_page_ids.update(item.get('actual_doc_page_ids', []))
                all_headings.extend(item.get('headings', []))
            
            feature_text_blocks = []
            all_images = []
            for pid in sorted(all_page_ids):
                if pid in pages_map:
                    feature_text_blocks.extend(pages_map[pid]['text_blocks'])
                    all_images.extend(pages_map[pid]['images'])

            full_text = " ".join([b['text'] for b in feature_text_blocks])
            chunks = self._create_chunks(full_text, all_headings)
            
            chunk_entries = []
            for chunk in chunks:
                if not chunk['text'].strip(): continue
                matched_images = self._match_images_llm(group[0]['featureName'], chunk['text'], all_images)
                

                associatedImages = []
                seen = set()
                for img in matched_images:
                    if img['name'] not in seen:
                        img_obj  = {}
                        img_obj['imageName'] = img['name']
                        img_obj['imageBase64'] = img['base64']
                        associatedImages.append(img_obj)
                        seen.add(img['name'])

                chunk_entries.append({
                    "heading": chunk['heading'],
                    "text": chunk['text'],
                })

            final_output.append({
                "feature_id": group[0]['feature_id'],
                "featureName": group[0]['featureName'],
                "description" : group[0]['description'],
                "category" : group[0]["category"],
                "docName": group[0]["docName"],
                "pageNo": group[0]["pageNo"],
                "chunks": chunk_entries,
                "associatedImages" : associatedImages
            })
            
        return final_output

    def _create_chunks(self, text, headings):
        chunks = []
        norm_text = normalize_text(text)
        if not headings: return [{"heading": None, "text": text}]

        current_pos = 0
        sorted_headings = []
        for h in headings:
            h_norm = normalize_text(h)
            idx = norm_text.find(h_norm, current_pos)
            if idx != -1:
                sorted_headings.append((idx, h))
                current_pos = idx 
        
        if not sorted_headings: return [{"heading": None, "text": text}]

        if sorted_headings[0][0] > 0:
            chunks.append({"heading": None, "text": norm_text[:sorted_headings[0][0]]})
            
        for i in range(len(sorted_headings)):
            start_idx, heading = sorted_headings[i]
            end_idx = sorted_headings[i+1][0] if i+1 < len(sorted_headings) else len(norm_text)
            chunks.append({"heading": heading, "text": norm_text[start_idx+len(heading):end_idx].strip()})
            
        return chunks

    def _match_images_llm(self, featureName, chunk_text, candidate_images):
        if not candidate_images: return []
        matched = []
        batch_size = 5
        
        for i in range(0, len(candidate_images), batch_size):
            batch = candidate_images[i:i+batch_size]
            img_inputs = [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img['base64']}"}} for img in batch]

            messages = [
                {"role": "system", "content": "Return JSON: {\"indices\": [0, 2]} for images relevant to the text."},
                {"role": "user", "content": [{"type": "text", "text": f"Feature: {featureName}\nText: {chunk_text}\nWhich images match?"}] + img_inputs}
            ]
            
            try:
                data = call_llm_formatted_response(messages, llm)
                # response = client.chat.completions.create(
                #     model=DEPLOYMENT_NAME,
                #     messages=messages,
                #     response_format={"type": "json_object"}
                # )
                # data = json.loads(response)
                indices = data.get("indices", [])
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(batch):
                        matched.append(batch[idx])
            except Exception:
                pass
        return matched


def main(INPUT_DIR):
    
    initialise_logger()
    final_result = list()
    logger = logging.getLogger('Feature')
    logger.info(f'files in dir :{os.listdir(INPUT_DIR)} ')
    
    for FILE_NAME in os.listdir(INPUT_DIR):
        # if FILE
        INPUT_FILE_PATH = os.path.join(INPUT_DIR, FILE_NAME)
        if not os.path.exists(INPUT_FILE_PATH):
            print(f"Error: File not found at {INPUT_FILE_PATH}")
        else:
            try:
                processor = DocumentProcessor(INPUT_FILE_PATH)
                
                # 1. Conversion
                pdf_path = processor.convert_docx_to_pdf()
                
                # 2. Page Exclusion
                image_paths = processor.convert_pdf_to_images(pdf_path)
                excluded_pages = processor.detect_excluded_pages(image_paths)
                
                # 3. Feature Extraction
                features_data = processor.analyze_images_to_extract_features(image_paths, excluded_pages, FILE_NAME)
                
                # 4. Text & Coord Extraction
                enriched_pages = processor.extract_text_and_images_coords(pdf_path, excluded_pages)
                
                # 5. Chunking & Matching
                final_result.extend(processor.chunk_and_associate_images(features_data, enriched_pages))
                
                # Save Output
                output_json = os.path.join(processor.job_dir, "final_output.json")
                
                    
                print("\n" + "="*50)
                print("SUCCESS! Processing Complete.")
                print(f"Output saved to: {output_json}")
                print(f"Log saved to: FeatureExtractionLog.log")
                print("="*50)
                
            except Exception as e:
                if logger:
                    logger.exception("An error occurred during processing.")
                else:
                    print(f"Critical error before logger init: {e}")

    # with open(output_json, "w", encoding="utf-8") as f:
    #     json.dump(final_result, f, indent=4)
    logger.info(f'len of resp returned {(len(final_result))}')
    if os.getenv('DEPLOYMENT_ENV') == 'local':
        json_path = os.path.join('sharedDir','WebTestCaseFiles', 'Features.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(final_result, f)
        except:
            logger.info('Exception while saving response')    
        
            
    return final_result

# --- Main Execution Block ---
if __name__ == "__main__":
    # Initialize logger first
    
    # Get input
    INPUT_FILE_PATH = input("Enter file path :") 
    
    # Remove quotes if user pastes path with them
    INPUT_FILE_PATH = INPUT_FILE_PATH.strip('"').strip("'")
    
    res = main(INPUT_FILE_PATH)
