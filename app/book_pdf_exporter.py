# app/book_pdf_exporter.py
from weasyprint import HTML
from jinja2 import Template
import os

def save_book_as_pdf(title: str, book_text: str, filename: str) -> str:
    """
    Generates a PDF file. This version includes the definitive fix for professional
    page numbering (numbers start at 1 on the first chapter).
    """
    output_dir = "generated_books"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    chapters = []
    for i, part in enumerate(book_text.split("## ")):
        if not part.strip():
            continue
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        chapter_id = f"chapter-{i+1}"
        content = lines[1].strip() if len(lines) > 1 else "Content for this chapter could not be generated."
        chapters.append({"heading": heading, "content": content, "id": chapter_id})

    # This is only for the TOC display, we'll remove the numbers from the list itself
    toc_entries = [{"title": p["heading"], "href": f"#{p['id']}"} for p in chapters]

    html_template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{{ title }}</title>
        <style>
            /* --- DEFINITIVE PAGE NUMBERING FIX --- */

            /* 1. Define a special page style for pages WITHOUT numbers */
            @page no-number {
                @bottom-center { content: ""; }
            }
            
            /* 2. The default style for ALL pages. It HAS a page number. */
            @page {
                size: letter;
                margin: 1in;
                @bottom-center {
                    /* Display the 'page' counter, which we will manage below */
                    content: counter(page);
                    font-size: 10pt;
                    font-style: italic;
                    color: #666;
                }
            }

            body {
                font-family: 'Garamond', serif; font-size: 12pt;
                line-height: 1.6; color: #333;
                /* 3. Initialize a counter named 'page' for the whole document */
                counter-reset: page; 
            }
            h1, h2 {
                font-family: 'Georgia', serif; text-align: center;
                font-weight: normal; page-break-after: avoid; color: #111;
            }

            /* --- PAGE LAYOUT & BREAKS --- */
            .cover-page {
                page: no-number; /* 4. Apply the 'no-number' style to the cover */
                page-break-after: always;
            }
            .toc-container {
                page: no-number; /* 5. Apply the 'no-number' style to the TOC */
                page-break-after: always;
            }
            .chapter {
                page-break-before: always;
                /* 6. For each new chapter, the page number goes up by 1 */
                counter-increment: page;
            }
            /* The very first chapter should not have a page break before it */
            .chapter:first-child {
                page-break-before: auto;
            }

            /* --- COVER PAGE --- */
            .cover-page { display: flex; align-items: center; justify-content: center; text-align: center; height: 9in; }
            .cover-page h1 { font-size: 42pt; text-transform: capitalize; margin-bottom: 0.5em; }
            .cover-page h2 { font-size: 18pt; font-style: italic; color: #555; }

            /* --- TABLE OF CONTENTS (without page numbers) --- */
            .toc-container h1 { font-size: 28pt; margin-bottom: 1.5em; }
            .toc ul { list-style: none; padding: 0; margin: 0 0.5in; }
            .toc li { margin-bottom: 1.1em; font-size: 13pt; }
            .toc a {
                color: #333;
                text-decoration: none;
            }
            
            /* --- CHAPTER STYLING --- */
            .chapter h2 {
                font-size: 22pt; margin-top: 1.5em; margin-bottom: 2em;
                text-transform: uppercase; letter-spacing: 1px;
            }
            .chapter p { text-align: justify; text-indent: 2em; margin-bottom: 0; }
            .chapter p:first-of-type { text-indent: 0; }
            .chapter p:first-of-type::first-letter {
                font-family: 'Georgia', serif; font-size: 4.5em;
                font-weight: bold; 
                line-height: 0.8;
                margin-left: -0.1em;
            }
        </style>
    </head>
    <body>
        <div class="cover-page">
            <div><h1>{{ title }}</h1><h2>A Star Wars Fan Novel</h2></div>
        </div>
                             
        <div class="toc-container">
            <div class="toc">
                <h1>Table of Contents</h1>
                <ul>
                {% for entry in toc_entries %}
                    <li><a href="{{ entry.href }}">{{ entry.title }}</a></li>
                {% endfor %}
                </ul>
            </div>
        </div>

        {% for chapter in chapters %}
        <div class="chapter" id="{{ chapter.id }}">
            <h2>{{ chapter.heading }}</h2>
            {% for paragraph in chapter.content.strip().split('\n\n') if paragraph.strip() %}
                <p>{{ paragraph.strip() }}</p>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """)

    rendered_html = html_template.render(title=title, chapters=chapters, toc_entries=toc_entries)
    HTML(string=rendered_html).write_pdf(output_path)
    return output_path