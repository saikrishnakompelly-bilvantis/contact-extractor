import os
from PIL import Image
import pytesseract
import pandas as pd
import glob
import re
import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from settings import settings

def preprocess_image(image):
    """Preprocess image to improve OCR accuracy"""
    return image

def clean_text(text: str) -> str:
    """Clean extracted text while preserving structure"""
    # Remove multiple spaces while preserving newlines
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.isspace():
            # Remove special characters but keep basic punctuation
            line = re.sub(r'[^\w\s\-&,.():]', '', line)
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                lines.append(line)
    return '\n'.join(lines)

def get_llm():
    """Configure and return the LLM"""
    if settings.LLM_PROVIDER == "llama":
        llm = ChatOpenAI(
            base_url=settings.LLM.LLAMA.BASE_URL,
            api_key=settings.LLM.LLAMA.API_KEY,
            model=settings.LLM.LLAMA.MODEL,
            max_tokens=settings.LLM.LLAMA.MAX_TOKENS,
            temperature=settings.LLM.LLAMA.TEMPERATURE,
        )     
        # Configure the model to use the system message and JSON response format
        return llm.bind(
            response_format={"type": "json_object"},
        )
    raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

def extract_contacts_with_llm(text: str) -> List[Dict]:
    """Use LLM to extract structured contact information"""
    system_prompt = """You are a helpful assistant that extracts contact information from text.
Your task is to identify and structure information about people, including their names, job titles, and companies.
Return the information in valid JSON format with a 'contacts' array. Do not wrap the JSON in markdown code blocks."""

    user_prompt = f"""Extract contact information from the following text. For each person, provide their name, job title/designation, and company name in a structured format.
Only include real contacts - ignore UI elements, timestamps, and navigation items.

Text to process:
{text}

Format the output exactly like this, with no markdown formatting:
{{
    "contacts": [
        {{"name": "Person Name", "designation": "Job Title", "company": "Company Name"}},
        ...
    ]
}}"""

    try:
        llm = get_llm()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = llm.invoke(messages)
        
        # Get the content from the response
        response_content = response.content
        
        # If the response is wrapped in markdown code blocks, extract the JSON
        if response_content.startswith('```') and response_content.endswith('```'):
            # Extract content between the first and last ```
            response_content = response_content.split('```')[1]
            # Remove any language identifier if present (e.g. ```json)
            if '\n' in response_content:
                response_content = response_content.split('\n', 1)[1]
        
        # Parse the JSON
        data = json.loads(response_content)
        return data.get('contacts', [])
        
    except Exception as e:
        print(f"Error extracting contacts with LLM: {str(e)}")
        print("Response:", response if 'response' in locals() else 'No response')
        return []

def save_contacts_to_csv(contacts: List[Dict], csv_path: str, is_new_file: bool = False) -> None:
    """Save contacts to CSV file, either creating a new file or appending to existing"""
    df = pd.DataFrame(contacts)
    if is_new_file:
        df.to_csv(csv_path, index=False, mode='w')
    else:
        df.to_csv(csv_path, index=False, mode='a', header=False)
    print(f"Saved {len(contacts)} contacts to {csv_path}")

def process_images(images_folder: str, csv_path: str, batch_size: int = 10) -> List[Dict]:
    """Process images in batches and extract text
    
    Args:
        images_folder: Directory containing the images
        csv_path: Path to save the CSV file
        batch_size: Number of images to process in each batch (default: 10)
    """
    all_contacts = []
    current_batch_text = []
    current_batch_count = 0
    is_first_batch = True
    
    # Supported image formats
    image_patterns = ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']
    image_files = []
    
    # Get all image files
    for pattern in image_patterns:
        image_files.extend(glob.glob(os.path.join(images_folder, pattern)))
    
    total_images = len(image_files)
    print(f"Found {total_images} images in total")
    
    # Process each image
    for idx, image_path in enumerate(image_files, 1):
        try:
            print(f"\nProcessing image {idx}/{total_images}: {os.path.basename(image_path)}...")
            image = Image.open(image_path)
            
            # Preprocess image
            image = preprocess_image(image)
            
            # Configure tesseract for better accuracy with screenshots
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean the text
            cleaned_text = clean_text(text)
            print("\nExtracted text:")
            print(cleaned_text)
            
            # Add to current batch
            current_batch_text.append(cleaned_text)
            current_batch_count += 1
            
            # Process batch if we've reached batch_size or this is the last image
            if current_batch_count == batch_size or idx == total_images:
                print(f"\nProcessing batch of {current_batch_count} images with LLM...")
                combined_text = "\n\n".join(current_batch_text)
                batch_contacts = extract_contacts_with_llm(combined_text)
                all_contacts.extend(batch_contacts)
                
                # Save batch contacts to CSV
                save_contacts_to_csv(batch_contacts, csv_path, is_first_batch)
                is_first_batch = False
                
                # Print progress
                print(f"Extracted {len(batch_contacts)} contacts from this batch.")
                print(f"Total contacts so far: {len(all_contacts)}")
                
                # Reset batch
                current_batch_text = []
                current_batch_count = 0
            
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
    
    return all_contacts

def main():
    # Folder containing images (relative to script location)
    images_folder = "images2"
    csv_path = 'extracted_contacts2.csv'
    batch_size = 10  # Process 10 images at a time
    
    # Create images folder if it doesn't exist
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
        print(f"Created {images_folder} directory. Please place your images there.")
        return
    
    # Process all images in batches and save to CSV
    contacts = process_images(images_folder, csv_path, batch_size)
    
    if contacts:
        print(f"\nExtracted {len(contacts)} total contacts from all images")
        print(f"All results have been saved to {csv_path}")
        
        # Print preview of all extracted contacts
        print("\nAll extracted contacts:")
        df = pd.read_csv(csv_path)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        print(df)
    else:
        print("\nNo contacts were extracted from the images")

if __name__ == '__main__':
    main()

# list the port requirements for kiwi cat tools