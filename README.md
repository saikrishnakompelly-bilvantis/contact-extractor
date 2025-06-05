# Contact Information Extractor

This tool extracts contact information (Name, Company, and Designation) from images and saves them to Excel files. It now includes both a command-line interface and a user-friendly Streamlit web application.

## Prerequisites

1. Python 3.7 or higher
2. Tesseract OCR must be installed on your system:
   - For macOS: `brew install tesseract`
   - For Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
   - For Windows: Download and install from [GitHub Tesseract Release](https://github.com/UB-Mannheim/tesseract/wiki)

## Installation

1. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Option 1: Streamlit Web App (Recommended)

The easiest way to use this tool is through the web interface:

1. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app.py
   ```
   Or use the helper script:
   ```bash
   python run_streamlit.py
   ```

2. Open your web browser and go to `http://localhost:8501`

3. Use the web interface to:
   - Upload single or multiple images
   - Preview uploaded images
   - Extract contacts with real-time progress
   - View extracted contacts in a table
   - Download results as Excel files (.xlsx)

#### Features:
- **Single Image Mode**: Upload and process one image at a time
- **Batch Processing**: Upload multiple images and process them together
- **Real-time Progress**: See processing status and progress bars
- **Interactive Results**: View extracted data in sortable tables
- **Excel Download**: Get formatted Excel files with professional styling
- **Settings**: Adjust batch size for optimal performance
- **Authentication**: Secure login system

### Option 2: Command Line Interface

For automated processing or integration into other workflows:

1. Place your images containing contact information in the `images2` folder (it will be created automatically if it doesn't exist)
   - Supported formats: JPG, JPEG, PNG, TIFF, BMP

2. Run the script:
   ```bash
   python run.py
   ```

3. The script will:
   - Process all images in the `images2` folder in batches
   - Extract contact information using OCR and LLM
   - Save the results to `extracted_contacts2.csv`

## Docker Deployment

For easy deployment on EC2 or other cloud platforms:

1. Build and run with Docker:
   ```bash
   # Using Docker Compose (recommended)
   docker-compose up -d
   
   # Or build manually
   docker build -t contact-extraction .
   docker run -p 8501:8501 contact-extraction
   ```

2. Use the deployment script for EC2:
   ```bash
   chmod +x deploy/deploy.sh
   ./deploy/deploy.sh deploy
   ```

## Output Format

The generated Excel file will contain:

### Main Sheet - "Contacts":
- **name**: The person's name
- **designation**: Job title/role  
- **company**: Company name

### Metadata Sheet:
- Generation timestamp
- Total contacts count
- Application information
- File format details

### Excel Features:
- **Professional Formatting**: Headers with blue background and white text
- **Auto-sized Columns**: Automatically adjusted column widths
- **Multiple Sheets**: Main data + metadata information
- **Timestamp**: Files include generation timestamp for tracking

## Configuration

The application uses LLM (Language Learning Model) for intelligent contact extraction. Configuration is managed in `src/settings.py`:

- **LLM Provider**: Currently configured to use Llama via OpenRouter
- **Model Settings**: Temperature, max tokens, and other parameters
- **API Configuration**: Base URL and authentication

## Authentication

The web application includes a secure login system:
- **Username**: `admin`
- **Password**: `Admin@123`

## Notes

- The tool works best with clear, high-resolution images
- Each image can contain multiple contacts
- The extraction accuracy depends on the quality of the image and the clarity of the text
- The LLM-powered extraction provides better accuracy than traditional regex-based methods
- Batch processing in the web app optimizes LLM usage and reduces processing time
- Excel files include professional formatting and metadata for better usability

## Troubleshooting

- **Tesseract not found**: Make sure Tesseract OCR is installed and in your system PATH
- **LLM API errors**: Check your API key and internet connection in `src/settings.py`
- **Memory issues**: Reduce batch size in the web app settings
- **Poor extraction quality**: Try uploading higher resolution images with clearer text
- **Excel download issues**: Ensure openpyxl is installed: `pip install openpyxl` 