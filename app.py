from flask import Flask, request, jsonify, Response, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

app = Flask(__name__)

# Helper function to ensure the URL has https://
def ensure_https(url):
    if not url.startswith('http://') and not url.startswith('https://'):
        return 'https://' + url
    return url

# Helper function to get metadata like title, OG tags, and favicon
def scrape_metadata(url):
    try:
        url = ensure_https(url)
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title_tag = soup.find('title')
        title = title_tag.string if title_tag else None  # Return the actual title if found

        # Extract Open Graph tags
        og_tags = {
            'og:title': soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title') else None,
            'og:description': soup.find('meta', property='og:description')['content'] if soup.find('meta', property='og:description') else None,
            'og:image': soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image') else None,
            'og:url': soup.find('meta', property='og:url')['content'] if soup.find('meta', property='og:url') else None
        }

              # Handle relative URLs for OG image
        if og_tags['og:image']:
            og_tags['og:image'] = urljoin(url, og_tags['og:image'])  # Resolve relative image path

        # Handle itemprop image
        itemprop_image = soup.find('meta', itemprop='image')
        itemprop_image_url = urljoin(url, itemprop_image['content']) if itemprop_image else None

        # Extract favicon (rel="icon" or rel="shortcut icon")
        favicon_tag = soup.find('link', rel=lambda x: x and 'icon' in x.lower())
        favicon_url = urljoin(url, favicon_tag['href']) if favicon_tag else None  # Resolve relative favicon path

        # Use itemprop image if OG image is not available
        if not og_tags['og:image'] and itemprop_image_url:
            og_tags['og:image'] = itemprop_image_url

        return {
            'title': title,
            'og_tags': og_tags,
            'favicon': favicon_url,
        }

      

    except requests.exceptions.RequestException as e:
        return {'error': f"Request error: {str(e)}"}
    except Exception as e:
        return {'error': f"An error occurred: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    only = request.args.get('only')  # Get the 'only' parameter

    if not url:
        return jsonify({'error': 'Please provide a URL'}), 400

    # Scrape the metadata
    metadata = scrape_metadata(url)

    # If an error occurred during scraping, return the error response
    if 'error' in metadata:
        return jsonify(metadata), 500

    # Handle the "only" parameter cases
    if only:
        try:
            if only == 'image':
                image_url = metadata.get('og_tags', {}).get('og:image')
                if image_url:
                    image_response = requests.get(image_url, stream=True)
                    image_response.raise_for_status()  # Ensure image request is successful
                    return Response(image_response.content, content_type=image_response.headers['Content-Type'])
                else:
                    return jsonify({'error': 'Image not found'}), 404

            elif only == 'title':
                return jsonify({'title': metadata['title']})

            elif only == 'og_tags':
                return jsonify({'og_tags': metadata['og_tags']})

            elif only == 'favicon':
                if metadata['favicon']:
                    favicon_response = requests.get(metadata['favicon'], stream=True)
                    favicon_response.raise_for_status()  # Ensure favicon request is successful
                    return Response(favicon_response.content, content_type=favicon_response.headers['Content-Type'])
                else:
                    return jsonify({'error': 'Favicon not found'}), 404

            else:
                return jsonify({'error': 'Invalid "only" parameter'}), 400

        except requests.exceptions.RequestException as e:
            return jsonify({'error': f"Request error while fetching resource: {str(e)}"}), 500
        except Exception as e:
            return jsonify({'error': f"An error occurred: {str(e)}"}), 500

    # If no "only" parameter is provided, return all metadata
    return jsonify(metadata)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
