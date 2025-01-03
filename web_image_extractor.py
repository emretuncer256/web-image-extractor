import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import mimetypes
import os
import zipfile
import io
from datetime import datetime
import hashlib
import urllib3
import warnings

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

if 'images' not in st.session_state:
    st.session_state.images = []
if 'selected_images' not in st.session_state:
    st.session_state.selected_images = {}
if 'select_all_state' not in st.session_state:
    st.session_state.select_all_state = False

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_url_content(url):
    try:
        # First try with verification
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except (requests.exceptions.SSLError, requests.exceptions.RequestException):
        try:
            # If that fails, try without verification
            response = requests.get(url, verify=False)
            response.raise_for_status()
            return response.content
        except Exception as e:
            st.error(f"Failed to fetch content: {str(e)}")
            return None

@st.cache_data(ttl=3600)
def fetch_url_headers(url):
    try:
        # First try with verification
        response = requests.head(url)
        return response.headers
    except (requests.exceptions.SSLError, requests.exceptions.RequestException):
        try:
            # If that fails, try without verification
            response = requests.head(url, verify=False)
            return response.headers
        except Exception as e:
            st.error(f"Failed to fetch headers: {str(e)}")
            return {}

@st.cache_data(ttl=3600)
def get_image_format(img_url):
    try:
        # First try to get format from URL extension
        ext = os.path.splitext(img_url)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            return 'JPG'
        elif ext == '.png':
            return 'PNG'
        elif ext == '.gif':
            return 'GIF'
        elif ext == '.webp':
            return 'WEBP'
        elif ext == '.svg':
            return 'SVG'
        
        # If no extension, try content-type header
        headers = fetch_url_headers(img_url)
        content_type = headers.get('content-type', '').lower()
        if 'gif' in content_type:
            return 'GIF'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            return 'JPG'
        elif 'png' in content_type:
            return 'PNG'
        elif 'webp' in content_type:
            return 'WEBP'
        elif 'svg' in content_type:
            return 'SVG'
            
        return 'IMG'
    except:
        return 'IMG'

@st.cache_data(ttl=3600)
def extract_images(url):
    try:
        if is_image_url(url):
            return [url]
            
        content = fetch_url_content(url)
        soup = BeautifulSoup(content, 'html.parser')
        img_tags = soup.find_all('img')
        
        # Use a set to store unique URLs
        image_urls = set()
        for img in img_tags:
            img_url = img.get('src')
            if img_url:
                absolute_url = urljoin(url, img_url)
                image_urls.add(absolute_url)
                
        # Convert set back to list before returning
        return list(image_urls)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def is_image_url(url):
    try:
        headers = fetch_url_headers(url)
        content_type = headers.get('content-type', '').lower()
        return content_type.startswith('image/')
    except:
        return mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith('image/')

def download_images(selected_images):
    def create_unique_filename(url, index, content_type):
        # Create a timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Create a short hash from the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        # Get the original filename without extension
        original_name = os.path.splitext(os.path.basename(url))[0]
        # Limit original name length and remove special characters
        original_name = ''.join(c for c in original_name if c.isalnum())[:20]
        
        # Determine extension based on content type
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        elif 'webp' in content_type:
            ext = '.webp'
        elif 'svg' in content_type:
            ext = '.svg'
        else:
            ext = ''
        
        # Combine all parts
        return f"{original_name}_{timestamp}_{url_hash}_{index}{ext}"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for index, img_url in enumerate(selected_images, 1):
            try:
                response = requests.get(img_url, verify=False)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    filename = create_unique_filename(img_url, index, content_type)
                    zip_file.writestr(filename, response.content)
            except Exception as e:
                st.error(f"Failed to download {img_url}: {str(e)}")
    
    return zip_buffer.getvalue()

def toggle_selection():
    # Toggle the state
    st.session_state.select_all_state = not st.session_state.select_all_state
    # Update all images based on the new state
    st.session_state.selected_images = {url: st.session_state.select_all_state for url in st.session_state.images}
    # Force rerun to update UI
    st.rerun()

def handle_checkbox_change(img_url):
    # Update the selected_images state directly from the checkbox state
    st.session_state.selected_images[img_url] = not st.session_state.selected_images.get(img_url, False)

def main():
    st.set_page_config(page_title="Image Extractor", page_icon="🖼️")
    st.title("🖼️ Web Image Extractor")
    
    # Add CSS for the format badge
    st.markdown("""
        <style>
        .format-badge {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8em;
            color: white;
            margin-left: 8px;
            display: inline-block;
        }
        .img-badge {
            background-color: #e0e0e0;
            color: #666;
        }
        .gif-badge {
            background-color: #ff69b4;
        }
        .jpg-badge {
            background-color: #4CAF50;
        }
        .png-badge {
            background-color: #2196F3;
        }
        .webp-badge {
            background-color: #9C27B0;
        }
        .svg-badge {
            background-color: #FF9800;
        }
        .link-format-container {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create URL input field
    url = st.text_input("Enter website URL or image URL:", "https://giphy.com/")
    
    # Sidebar controls
    with st.sidebar:
        # Column count slider
        col_count = st.slider("Number of columns", min_value=1, max_value=8, value=6)
        st.write("---")
        
        st.write("Download Options")
        if st.session_state.images:
            # Get currently selected images count
            selected = [url for url, is_selected in st.session_state.selected_images.items() if is_selected]
            selected_count = len(selected)
            total_count = len(st.session_state.images)
            
            # Display selection counter
            st.write(f"Selected: {selected_count} of {total_count} images")
            
            # Toggle button for selection
            button_text = "Deselect All" if st.session_state.select_all_state else "Select All"
            if st.button(button_text):
                toggle_selection()
            
            if selected:
                if st.button("Download Selected Images"):
                    zip_data = download_images(selected)
                    st.download_button(
                        label="Download ZIP",
                        data=zip_data,
                        file_name="images.zip",
                        mime="application/zip"
                    )
            else:
                st.write("No images selected")
    
    # Create extract button
    if st.button("Extract Images"):
        if url:
            with st.spinner("Processing URL..."):
                st.session_state.images = extract_images(url)
                if not st.session_state.images:
                    st.error("No images found on this URL!")
                else:
                    st.session_state.selected_images = {url: False for url in st.session_state.images}
        else:
            st.error("Please enter a URL!")
    
    # Display images if they exist in session state
    if st.session_state.images:
        st.success(f"Found {len(st.session_state.images)} image{'s' if len(st.session_state.images) > 1 else ''}!")
        
        # Create a container for the image grid
        with st.container():
            st.write("Select images to download:")
            
            # Display images in a grid with dynamic columns
            for i in range(0, len(st.session_state.images), col_count):
                cols = st.columns(col_count)
                for j, col in enumerate(cols):
                    if i + j < len(st.session_state.images):
                        with col:
                            img_url = st.session_state.images[i + j]
                            try:
                                st.image(img_url, use_container_width=True)
                                format_type = get_image_format(img_url)
                                badge_class = f"format-badge {format_type.lower()}-badge"
                                st.markdown(
                                    f'<div class="link-format-container">'
                                    f'<a href="{img_url}">Open↗</a>'
                                    f'<span class="{badge_class}">{format_type}</span>'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                                checkbox_key = f"img_{i}_{j}"
                                checked = st.session_state.selected_images.get(img_url, False)
                                if st.checkbox(
                                    "Select",
                                    key=checkbox_key,
                                    value=checked,
                                    on_change=handle_checkbox_change,
                                    args=(img_url,)
                                ):
                                    st.session_state.selected_images[img_url] = True
                                else:
                                    st.session_state.selected_images[img_url] = False
                            except:
                                st.error("Failed to load image")

    # Add footer with some spacing from the main content
    st.markdown("<br><br><br>", unsafe_allow_html=True)  # Add some space
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 10px; font-size: 0.8em;'>
            Developed by Emre Tuncer | <a style='color: #666; text-decoration: none; border-bottom: 1px solid #666;' 
            href="https://github.com/emretuncer256" target="_blank">@emretuncer256</a>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 