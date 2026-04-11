import requests
from html_parser import HtmlParser
from text_splitter import TextSplitter

url = "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764&p=20260321&tn=0"

response = requests.get(url, timeout=10, verify=False)

parser = HtmlParser()
text = parser.parse(response.text, url)

splitter = TextSplitter()
chunks = splitter.split(text)


for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i + 1} ---")
    print(chunk["text"])
    if chunk["links"]:
        print("Links:", chunk["links"])
    print()
