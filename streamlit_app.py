import streamlit as st
import pandas as pd
import tempfile
import os
from PIL import Image
import pytesseract
import json
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from src.settings import settings
import zipfile
import io
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Contact Extraction App",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Static credentials
ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "Admin@123"

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def create_excel_file(df: pd.DataFrame, filename: str) -> bytes:
    """Create Excel file from DataFrame and return bytes"""
    output = io.BytesIO()
    
    # Create Excel writer object
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write DataFrame to Excel
        df.to_excel(writer, sheet_name='Contacts', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Contacts']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Add some formatting
        from openpyxl.styles import Font, PatternFill, Alignment
        
        # Header formatting
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for cell in worksheet[1]:  # First row (headers)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Add metadata sheet
        metadata_df = pd.DataFrame({
            'Property': ['Generated Date', 'Total Contacts', 'Application', 'File Format'],
            'Value': [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                len(df),
                'Bilvantis Contact Extraction',
                'Excel (.xlsx)'
            ]
        })
        metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
    
    output.seek(0)
    return output.getvalue()

def login_page():
    """Display login page"""
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Bilvantis Contact Extraction")
        st.markdown("Please enter your credentials to access the application")
        with st.container():
            st.markdown("### Login Form")
            
            # Login form
            with st.form("login_form"):
                email = st.text_input("Email/Username", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_button = st.form_submit_button("Login", use_container_width=True)
                
                if submit_button:
                    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                        st.session_state['authenticated'] = True
                        st.session_state['user_email'] = email
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
                        st.info("💡 Hint: Use 'admin' and 'Admin@123'")
            

def logout():
    """Logout function"""
    st.session_state['authenticated'] = False
    st.session_state['user_email'] = None
    st.rerun()

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
        st.error(f"Error extracting contacts with LLM: {str(e)}")
        return []

def process_single_image(image) -> tuple[str, List[Dict]]:
    """Process a single image and return extracted text and contacts"""
    try:
        # Preprocess image
        image = preprocess_image(image)
        
        # Configure tesseract for better accuracy with screenshots
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # Clean the text
        cleaned_text = clean_text(text)
        
        # Extract contacts using LLM
        contacts = extract_contacts_with_llm(cleaned_text)
        
        return cleaned_text, contacts
        
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return "", []

def process_multiple_images(uploaded_files, batch_size: int = 5) -> List[Dict]:
    """Process multiple images in batches"""
    all_contacts = []
    current_batch_text = []
    current_batch_count = 0
    
    total_images = len(uploaded_files)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"Processing image {idx + 1}/{total_images}: {uploaded_file.name}")
            
            # Load image
            image = Image.open(uploaded_file)
            
            # Preprocess image
            image = preprocess_image(image)
            
            # Configure tesseract for better accuracy with screenshots
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean the text
            cleaned_text = clean_text(text)
            
            # Add to current batch
            current_batch_text.append(cleaned_text)
            current_batch_count += 1
            
            # Process batch if we've reached batch_size or this is the last image
            if current_batch_count == batch_size or idx == total_images - 1:
                status_text.text(f"Processing batch with LLM...")
                combined_text = "\n\n".join(current_batch_text)
                batch_contacts = extract_contacts_with_llm(combined_text)
                all_contacts.extend(batch_contacts)
                
                # Reset batch
                current_batch_text = []
                current_batch_count = 0
            
            # Update progress
            progress_bar.progress((idx + 1) / total_images)
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    status_text.text("Processing complete!")
    return all_contacts

def main_app():
    """Main application interface (shown after login)"""
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📇 Bilvantis Contact Extraction")
        st.markdown("Upload images containing contact information and extract structured data as Excel")
    with col2:
        st.markdown(f"**Welcome, {st.session_state.get('user_email', 'User')}!**")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        batch_size = st.slider("Batch Size", min_value=1, max_value=20, value=5, 
                              help="Number of images to process together with LLM")
        
        st.header("👤 User Info")
        st.info(f"Logged in as: **{st.session_state.get('user_email', 'Unknown')}**")
        
        st.header("ℹ️ About")
        st.markdown("""
        This app uses:
        - **OCR** (Tesseract) to extract text from images
        - **LLM** to structure contact information
        - **Excel** for data export with formatting
        """)
    
    # Main content
    tab1, tab2 = st.tabs(["Single Image", "Multiple Images"])
    
    with tab1:
        st.header("Upload Single Image")
        uploaded_file = st.file_uploader(
            "Choose an image file", 
            type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
            key="single_image"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📷 Uploaded Image")
                image = Image.open(uploaded_file)
                st.image(image, caption=uploaded_file.name, use_container_width=True)
            
            with col2:
                st.subheader("🔄 Processing")
                if st.button("Extract Contacts", key="single_extract"):
                    with st.spinner("Processing image..."):
                        extracted_text, contacts = process_single_image(image)
                    
                    if contacts:
                        st.success(f"Extracted {len(contacts)} contacts!")
                        
                        # Display results
                        df = pd.DataFrame(contacts)
                        st.subheader("📊 Extracted Contacts")
                        st.dataframe(df, use_container_width=True)
                        
                        # Generate Excel file
                        filename = f"contacts_{uploaded_file.name.split('.')[0]}.xlsx"
                        excel_data = create_excel_file(df, filename)
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Excel",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Show extracted text in expander
                        with st.expander("🔍 View Extracted Text"):
                            st.text_area("Raw OCR Text", extracted_text, height=200)
                    else:
                        st.warning("No contacts found in the image.")
    
    with tab2:
        st.header("Upload Multiple Images")
        uploaded_files = st.file_uploader(
            "Choose image files", 
            type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
            accept_multiple_files=True,
            key="multiple_images"
        )
        
        if uploaded_files:
            st.write(f"📁 {len(uploaded_files)} files uploaded")
            
            # Show preview of uploaded files
            with st.expander("👀 Preview Uploaded Files"):
                cols = st.columns(min(len(uploaded_files), 4))
                for idx, file in enumerate(uploaded_files[:4]):
                    with cols[idx % 4]:
                        image = Image.open(file)
                        st.image(image, caption=file.name, use_container_width=True)
                if len(uploaded_files) > 4:
                    st.write(f"... and {len(uploaded_files) - 4} more files")
            
            if st.button("🚀 Extract All Contacts", key="multiple_extract"):
                with st.spinner("Processing all images..."):
                    all_contacts = process_multiple_images(uploaded_files, batch_size)
                
                if all_contacts:
                    st.success(f"🎉 Extracted {len(all_contacts)} total contacts from {len(uploaded_files)} images!")
                    
                    # Display results
                    df = pd.DataFrame(all_contacts)
                    st.subheader("📊 All Extracted Contacts")
                    st.dataframe(df, use_container_width=True)
                    
                    # Generate Excel file with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"all_extracted_contacts_{timestamp}.xlsx"
                    excel_data = create_excel_file(df, filename)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download All Contacts Excel",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Contacts", len(all_contacts))
                    with col2:
                        st.metric("Images Processed", len(uploaded_files))
                    with col3:
                        avg_per_image = len(all_contacts) / len(uploaded_files) if uploaded_files else 0
                        st.metric("Avg per Image", f"{avg_per_image:.1f}")
                else:
                    st.warning("No contacts found in any of the images.")

def main():
    """Main function that handles authentication and routing"""
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    # Route based on authentication status
    if check_authentication():
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main() 