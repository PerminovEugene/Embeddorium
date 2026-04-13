from dotenv import load_dotenv
import os

load_dotenv()

HG_TOKEN: str = os.getenv("HG_TOKEN", "")
