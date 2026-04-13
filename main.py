from dotenv import load_dotenv
load_dotenv()

import requests
from html_parser import HtmlParser
from text_splitter import TextSplitter
from hg_client import HgClient

url = "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764&p=20260321&tn=0"
url = "https://www.evgeniiperminov.dev/"

response = requests.get(url, timeout=10, verify=False)
print(f"got url", response)
parser = HtmlParser()
text = parser.parse(response.text, url)
print(f"parsed", text)

splitter = TextSplitter()
chunks = splitter.split(text)

print(f"chunks amount", len(chunks))

hg_client = HgClient()
model = hg_client.get_model("Qwen/Qwen3-Embedding-8B")

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i + 1} ---")
    print(chunk["text"])
    if chunk["links"]:
        print("Links:", chunk["links"])
    print()

    
