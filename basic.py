import streamlit as st
from PyPDF2 import PdfReader
import docx
import pandas as pd
import fitz  # PyMuPDF for handling images
from dotenv import load_dotenv
import io
from PIL import Image


def count_characters_in_pdf(pdf_docs):
    total_characters = 0
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        content = ""
        for page in reader.pages:
            content += page.extract_text() or ""
        total_characters += len(content)
    return total_characters

# Function to count characters in Word files
def count_characters_in_docx(docx_files):
    total_characters = 0
    for doc in docx_files:
        doc_reader = docx.Document(doc)
        for para in doc_reader.paragraphs:
            total_characters += len(para.text)
    return total_characters

def count_images_in_pdf(pdf_docs):
    total_images = 0
    image_data = []
    
    for pdf in pdf_docs:
        # Reset file pointer to the beginning
        pdf.seek(0)
        
        try:
            doc = fitz.open(stream=pdf.read(), filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]
                image_list = page.get_images(full=True)
                total_images += len(image_list)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Convert image bytes to PIL Image for display
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        # Convert RGBA to RGB if necessary
                        if image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])
                            image = background
                        
                        # Convert image to bytes for storage
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format if image.format else 'PNG')
                        img_byte_arr = img_byte_arr.getvalue()
                        
                        image_data.append({
                            "page": page_index + 1,
                            "width": image.width,
                            "height": image.height,
                            "image_bytes": img_byte_arr,
                            "image_index": img_index + 1
                        })
                    except Exception as e:
                        st.warning(f"Error processing image: {str(e)}")
                        continue
                    finally:
                        if 'image' in locals():
                            image.close()
            doc.close()
        except Exception as e:
            st.warning(f"Error processing PDF: {str(e)}")
            continue
            
    return total_images, image_data

# Function to get document details (remains the same)
def get_document_details(pdf_docs, docx_files):
    total_characters = 0
    total_images = 0
    image_data = []

    if pdf_docs:
        total_characters += count_characters_in_pdf(pdf_docs)
        pdf_image_count, pdf_image_data = count_images_in_pdf(pdf_docs)
        total_images += pdf_image_count
        image_data.extend(pdf_image_data)

    if docx_files:
        total_characters += count_characters_in_docx(docx_files)

    return total_characters, total_images, image_data

# Main Streamlit application
def main():
    st.set_page_config(page_title="Document Analyzer", layout="wide")
    st.title("Document Analyzer")

    st.markdown(
        """
        <style>
        .main {
            background-color: #000000;
            padding: 2rem;
            font-family: Arial, sans-serif;
            color: #333;
        }
        .stImage {
            max-width: 300px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.header("Upload your documents to analyze 🤖")

    # Initialize session state
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'total_characters' not in st.session_state:
        st.session_state.total_characters = 0
    if 'total_images' not in st.session_state:
        st.session_state.total_images = 0
    if 'image_data' not in st.session_state:
        st.session_state.image_data = []

    doc_files = st.file_uploader("Upload your Documents", accept_multiple_files=True, type=["pdf", "docx"])

    if doc_files:
        pdf_docs = [doc for doc in doc_files if doc.type == "application/pdf"]
        docx_files = [doc for doc in doc_files if doc.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

        if st.button("Submit & Analyze"):
            with st.spinner("Analyzing..."):
                try:
                    total_chars, total_imgs, img_data = get_document_details(pdf_docs, docx_files)
                    st.session_state.total_characters = total_chars
                    st.session_state.total_images = total_imgs
                    st.session_state.image_data = img_data
                    st.session_state.analysis_complete = True
                    st.success("Analysis complete!")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    return

        # Only show query input if analysis is complete
        if st.session_state.analysis_complete:
            user_query = st.text_input("Ask something about the document (e.g., 'character count', 'image count', 'image details'):").lower()
            
            # Show results based on query
            if user_query:
                if "character" in user_query:
                    st.write(f"Character Count: {st.session_state.total_characters:,}")
                elif "image" in user_query and "detail" in user_query:
                    if st.session_state.image_data:
                        st.write("Images with details:")
                        for img_data in st.session_state.image_data:
                            st.write(f"Page {img_data['page']} - Image {img_data['image_index']}")
                            st.write(f"Dimensions: {img_data['width']}x{img_data['height']} pixels")
                            
                            # Display the image
                            try:
                                image = Image.open(io.BytesIO(img_data['image_bytes']))
                                max_display_size = (300, 300)
                                image.thumbnail(max_display_size)

                                st.image(image, caption=f"Page {img_data['page']} - Image {img_data['image_index']}", 
             use_column_width=False, width=300)
                            except Exception as e:
                                st.warning(f"Could not display image: {str(e)}")
                            
                            st.write("---")  # Add separator between images
                    else:
                        st.write("No images found in the document.")
                elif "image" in user_query:
                    st.write(f"Total Images: {st.session_state.total_images}")
                else:
                    st.write("Please ask about 'character count', 'image count', or 'image details'")

if __name__ == "__main__":
    main()


