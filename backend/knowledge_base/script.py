import requests
from bs4 import BeautifulSoup

# Global list to store href values


def scrape_website(url):
    href_list = []
    try:
        # Send GET request to the website
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all divs with class "items"
        items_divs = soup.find_all('div', class_='items')
        
        # Iterate through each items div
        for items_div in items_divs:
            # Find all anchor tags with class "VPLink" inside the current items div
            vp_links = items_div.find_all('a', class_='VPLink')
            
            # Extract href values and add to global list
            for link in vp_links:
                href = link.get('href')
                if href:
                    href_list.append(href)
        prefix = "https://mavlink.io"
        results = []
        for href in href_list:
            if href.startswith('/en/messages'):
                results.append(prefix + href)
        return results
        
    except requests.RequestException as e:
        print(f"Error fetching the website: {e}")
        return []
    except Exception as e:
        print(f"Error processing the website: {e}")
        return []

def convert_to_md(url):
    try:
        # Send GET request to the website
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main content div
        main_content = soup.find('main', class_='main')
        
        if not main_content:
            print(f"Could not find main content for URL: {url}")
            return ""
            
        # Convert HTML to markdown using html2text
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False  # Preserve links
        h.ignore_images = False  # Preserve images
        h.body_width = 0  # Don't wrap text
        
        # Convert the main content to markdown
        markdown_content = h.handle(str(main_content))
        
        return markdown_content
        
    except requests.RequestException as e:
        print(f"Error fetching the website: {e}")
        return ""
    except Exception as e:
        print(f"Error converting to markdown: {e}")
        return ""

# Example usage
if __name__ == "__main__":
    target_url = "https://mavlink.io/en/"  # Replace with actual URL
    results = scrape_website(target_url)
    print(f"Found {len(results)} links:")
    knowledge_base = {}
    for url in results:
        md = convert_to_md(url)
        knowledge_base[url.split('/')[-1]] = md

    # print(knowledge_base['common.html'])
    import json
    with open('knowledge_base.json', 'w') as f:
        json.dump(knowledge_base, f)

    with open('knowledge_base.txt', 'w') as f:
        f.write('\n\n'.join(knowledge_base.values()))

    print(knowledge_base.keys())