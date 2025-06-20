# app/book_pdf_exporter.py
from weasyprint import HTML
from jinja2 import Template
import os

def save_book_as_pdf(title: str, book_text: str, filename: str) -> str:
    """
    Generates a PDF file from book text using a Jinja2 HTML template.
    This version includes an improved TOC and selective page numbering.
    """
    output_dir = "generated_books"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    pages = []
    for i, part in enumerate(book_text.split("## ")):
        if not part.strip():
            continue
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        chapter_id = f"chapter-{i+1}"
        content = lines[1].strip() if len(lines) > 1 else "Content for this chapter could not be generated."
        pages.append({"heading": heading, "content": content, "id": chapter_id})

    toc_entries = [{"title": p["heading"], "href": f"#{p['id']}"} for p in pages]

    html_template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{{ title }}</title>
        <style>
            /* --- PAGE NUMBERING SETUP --- */
            /* Define different "named" pages for special formatting */
            @page cover {
                /* No page number on the cover */
                @bottom-center { content: ""; }
            }
            @page toc {
                /* No page number on the table of contents */
                @bottom-center { content: ""; }
            }
            @page {
                /* Default style for all other pages (the chapters) */
                size: letter; 
                margin: 1in;
                @bottom-center {
                    content: "Page " counter(page);
                    font-size: 10pt;
                    font-style: italic;
                    color: #777;
                }
            }
            
            body { font-family: 'Garamond', 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; }
            h1, h2 { font-family: 'Georgia', serif; text-align: center; font-weight: normal; page-break-after: avoid; }

            /* --- PAGE TYPE ASSIGNMENT --- */
            .cover-page { 
                page: cover; /* Assign this div to the 'cover' page style */
                page-break-after: always;
            }
            .toc-page { 
                page: toc; /* Assign this div to the 'toc' page style */
                page-break-after: always;
            }
            .chapter-page { 
                page-break-before: always; 
            }
            
            /* Cover Page Styling */
            .cover { display: flex; align-items: center; justify-content: center; text-align: center; height: 90vh; }
            .cover-content h1 { font-size: 38pt; font-weight: 600; text-transform: capitalize; }
            .cover-content h2 { font-size: 18pt; font-style: italic; color: #555; }

            /* --- UPGRADED TABLE OF CONTENTS STYLING --- */
            .toc h1 { font-size: 24pt; margin-bottom: 1.5em; }
            .toc ul { list-style: none; padding: 0; }
            .toc li { 
                /* Use flexbox to separate title from page number */
                display: flex;
                justify-content: space-between; 
                align-items: baseline;
                margin-bottom: 0.9em;
                font-size: 14pt; /* Slightly larger for readability */
            }
            .toc .title {
                /* The title part takes up space, but allows the dots to fill */
                padding-right: 10px;
                white-space: nowrap;
            }
            .toc .page-number {
                /* The page number part */
                font-weight: bold;
                padding-left: 10px;
            }
            .toc .dots {
                /* This is the magic: it creates the dot leaders */
                flex-grow: 1;
                border-bottom: 2px dotted #aaa;
                position: relative;
                bottom: 4px;
            }

            /* Chapter Styling */
            .chapter-page h2 { font-size: 20pt; margin-top: 2em; margin-bottom: 1.5em; text-transform: uppercase; letter-spacing: 1px; }
            p { text-indent: 2em; margin-bottom: 0; text-align: justify; }
            p:first-of-type { text-indent: 0; }
            p:first-of-type::first-letter {
                font-size: 4em; font-weight: bold; float: left; padding-right: 8px; line-height: 0.8; padding-top: 8px;
            }
        </style>
    </head>
    <body>
        <div class="cover-page">
            <div class="cover">
                <div class="cover-content">
                    <h1>{{ title }}</h1>
                    <h2>A Star Wars Fan Novel</h2>
                </div>
            </div>
        </div>
                             
        <div class="toc-page">
            <div class="toc">
                <h1>Table of Contents</h1>
                <!-- We now generate the page numbers here using WeasyPrint's magic -->
                <ul weasy:is-for-p toc_pages></ul>
            </div>
        </div>

        {% for page in pages %}
        <div class="chapter-page" id="{{ page.id }}">
            <h2 weasy:is-for-h book_marks>{{ page.heading }}</h2>
            {% for paragraph in page.content.strip().split('\n\n') if paragraph.strip() %}
                <p>{{ paragraph.strip() }}</p>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    <script>
        // --- This script generates the TOC dynamically before rendering ---
        const tocList = document.querySelector('[weasy:is-for-p="toc_pages"]');
        const headings = document.querySelectorAll('[weasy:is-for-h="book_marks"]');
        
        headings.forEach((h, i) => {
            const pageNumber = weasy.get_page_number(h); // WeasyPrint specific function
            
            const li = document.createElement('li');
            
            const titleSpan = document.createElement('span');
            titleSpan.className = 'title';
            titleSpan.textContent = h.textContent;

            const dotsSpan = document.createElement('span');
            dotsSpan.className = 'dots';
            
            const pageSpan = document.createElement('span');
            pageSpan.className = 'page-number';
            pageSpan.textContent = pageNumber;
            
            li.appendChild(titleSpan);
            li.appendChild(dotsSpan);
            li.appendChild(pageSpan);
            
            tocList.appendChild(li);
        });
    </script>
    </html>
    """)

    # We need to enable JavaScript for the TOC generation to work
    rendered_html = html_template.render(title=title, pages=pages)
    html = HTML(string=rendered_html, base_url=os.path.abspath('.'))
    html.write_pdf(output_path, enable_javascript=True)
    
    return output_path