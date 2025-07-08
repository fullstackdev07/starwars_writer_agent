# app/book_pdf_exporter.py
from weasyprint import HTML, CSS
from jinja2 import Template
import os
from datetime import datetime

def save_book_as_pdf(title: str, book_data: dict, filename: str) -> str:
    """
    Generates the final, professionally formatted PDF based on the new structure.
    """
    output_dir = "generated_books"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    # --- Prepare all data for the template ---
    all_sections_for_toc = []
    if book_data.get('prologue_text'):
        all_sections_for_toc.append({"title": "Prologue", "href": "#prologue"})
    for i, ch in enumerate(book_data.get("chapters", [])):
        all_sections_for_toc.append({"title": ch["heading"], "href": f"#chapter-{i+1}"})
    if book_data.get('epilogue_text'):
        all_sections_for_toc.append({"title": "Epilogue", "href": "#epilogue"})

    template_context = {
        "book_title": title,
        "print_date": datetime.now().strftime("%B %d, %Y"),
        "toc_entries": all_sections_for_toc,
        "page_count": len(book_data.get("chapters", [])) * 2 + 15,  # Estimate total pages
        **book_data
    }
    
    html_template = Template("""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>{{ book_title }}</title></head>
    <body>
        <div class="swapi-call-page debug-page"><h1>SWAPI API Call Context</h1><pre>{{ swapi_call_text }}</pre></div>
        <div class="swapi-json-page debug-page"><pre>{{ swapi_json_output }}</pre></div>
        <div class="blank-page"></div><div class="blank-page"></div><div class="blank-page"></div><div class="blank-page"></div>
        {% if image_path %}<div class="image-page"><div class="image-container"><img src="{{ image_path }}" alt="AI Generated Book Image"></div></div>{% endif %}
        <div class="title-page"><div class="title-content">
            <div class="title-decoration">✧</div>
            <h1 class="book-title">{{ book_title }}</h1>
            <div class="title-decoration">✦</div>
            <h2 class="subtitle">A STAR WARS FAN NOVEL</h2>
            <div class="title-decoration">✧</div>
            <p class="author-credit">INSPIRED BY A PROMPT<br>AND WRITTEN BY<br>THE NOVELIST-AGENT</p>
        </div></div>
        <div class="print-date-page"><p>A personalized edition created on<br>{{ print_date }}</p></div>
        <div class="blank-page"></div><div class="blank-page"></div>
        <div class="toc-container"><h1>Table of Contents</h1><div class="toc-list">{% for entry in toc_entries %}<div class="toc-entry"><span class="entry-title">{{ entry.title }}</span><a href="{{ entry.href }}">{{ loop.index }}</a></div>{% endfor %}</div></div>
        <div class="blank-page"></div>
        <div class="prologue-page content-page" id="prologue"><h2>Prologue</h2><div class="content-block">{% for p in prologue_text.split('\n\n') %}<p>{{ p }}</p>{% endfor %}</div></div>
        <div class="blank-page"></div>
        
        <div class="main-content-body">
            {% for chapter in chapters %}
            <div class="chapter-title-page"><div class="chapter-title"><span class="chapter-number">{{ loop.index }}</span><h2>{{ chapter.heading }}</h2></div></div>
            <div class="chapter-content-page content-page" id="chapter-{{ loop.index }}">
                <div class="content-block">
                {% for p in chapter.content.split('\n\n') %}<p>{{ p }}</p>{% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="epilogue-page content-page" id="epilogue"><h2>Epilogue</h2><div class="content-block">{% for p in epilogue_text.split('\n\n') %}<p>{{ p }}</p>{% endfor %}</div></div>
    </body>
    </html>
    """)
    rendered_html = html_template.render(template_context)

    # --- CSS Styling ---
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fonts'))
    font_config = f"""
    @font-face {{ font-family: 'Baskerville'; src: url('{os.path.join(fonts_dir, 'LibreBaskerville-Regular.ttf')}') format('truetype'); }}
    @font-face {{ font-family: 'Baskerville'; font-style: italic; src: url('{os.path.join(fonts_dir, 'LibreBaskerville-Italic.ttf')}') format('truetype'); }}
    @font-face {{ font-family: 'Baskerville'; font-weight: bold; src: url('{os.path.join(fonts_dir, 'LibreBaskerville-Bold.ttf')}') format('truetype'); }}
    """
    
    main_css = """
    @page { size: 140mm 216mm; margin: 32mm; @bottom-center { content: ""; } }
    @page main { @bottom-center { content: counter(page) " of " target-counter(#last-page, page); font-family: 'Baskerville', serif; font-size: 9pt; } }
    
    body { font-family: 'Baskerville', serif; font-size: 11pt; line-height: 1.6; counter-reset: page; background: #fff; -webkit-font-smoothing: antialiased; }
    .blank-page { height: 100vh; page-break-after: always; background: #fff; }
    div { page-break-after: always; }
    div:last-child { page-break-after: auto; }
    h1, h2 { text-align: center; font-weight: bold; margin: 0; }
    
    .debug-page pre { font-size: 6pt; white-space: pre-wrap; word-wrap: break-word; }
    .swapi-json-page { column-count: 2; column-gap: 10mm; }

    .image-page { display: flex; align-items: center; justify-content: center; height: 100vh; background: #fff; padding: 2em; }
    .image-container { width: 85%; max-width: 100%; margin: auto; text-align: center; }
    .image-container img { max-width: 100%; max-height: 80vh; width: auto; height: auto; display: inline-block; object-fit: contain; }
    
    .title-page { display: flex; align-items: center; justify-content: center; height: 100vh; background: #fff; }
    .title-content { text-align: center; padding: 2em; }
    .book-title { font-size: 36pt; font-weight: bold; margin: 1em 0; line-height: 1.2; }
    .subtitle { font-size: 16pt; margin: 1.5em 0; letter-spacing: 0.1em; }
    .title-decoration { font-size: 24pt; margin: 1.5em 0; color: #333; }
    .author-credit { font-size: 14pt; line-height: 1.8; margin-top: 3em; letter-spacing: 0.05em; }

    .print-date-page { display: flex; align-items: center; justify-content: center; height: 100vh; }
    .print-date-page p { text-align: center; font-style: italic; font-size: 10pt; }

    .toc-container { padding: 4em 2em; page-break-inside: avoid; }
    .toc-container h1 { font-size: 32pt; margin-bottom: 2em; font-family: 'Baskerville', serif; letter-spacing: 0.1em; }
    .toc-list { width: 90%; margin: 0 auto; }
    .toc-entry { display: flex; align-items: baseline; margin-bottom: 1.5em; position: relative; justify-content: space-between; }
    .toc-entry::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0.4em; border-bottom: 1px dotted rgba(0,0,0,0.4); z-index: -1; }
    .entry-title { font-size: 14pt; background: white; padding-right: 0.8em; font-family: 'Baskerville', serif; letter-spacing: 0.05em; }
    .toc-entry a { display: none; }

    .chapter-title-page { display: flex; align-items: center; justify-content: center; height: 100vh; background: #fff; }
    .chapter-title { text-align: center; padding: 2em; }
    .chapter-number { display: block; font-size: 18pt; margin-bottom: 1.5em; font-family: 'Baskerville', serif; }
    .chapter-title h2 { font-size: 28pt; text-transform: uppercase; letter-spacing: 0.15em; line-height: 1.4; }

    .content-page { padding: 2em 0; }
    .content-page h2 { font-size: 20pt; text-transform: uppercase; margin-bottom: 2.5em; letter-spacing: 0.1em; }
    .content-block { margin: 0 auto; max-width: 100%; }
    .content-block p { text-align: justify; text-indent: 2em; margin-bottom: 1em; hyphens: auto; }
    .content-block p:first-child { text-indent: 0; margin-top: 1em; }
    .content-block p:first-child::first-letter { font-size: 3em; float: left; line-height: 1; padding: 0.1em 0.2em 0 0; margin: 0 0.1em 0 0; font-family: 'Baskerville', serif; font-weight: bold; }

    .preface-page, .prologue-page, .main-content-body, .epilogue-page, .chapter-content-page { page: main; }
    .epilogue-page { position: relative; }
    .epilogue-page::after { content: ""; id: last-page; }
    """
    
    css = CSS(string=font_config + main_css)
    HTML(string=rendered_html, base_url=os.path.abspath('.')).write_pdf(output_path, stylesheets=[css])
    
    return output_path