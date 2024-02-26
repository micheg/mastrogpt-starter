#--web true
#--param OPENAI_API_KEY $OPENAI_API_KEY
#--param OPENAI_API_HOST $OPENAI_API_HOST

from openai import AzureOpenAI
import re
import requests
import socket


ROLE = """
When requested to write code, pick Python.
When requested to show chess position, always use the FEN notation.
When showing HTML, always include what is in the body tag, 
but exclude the code surrounding the actual content. 
So exclude always BODY, HEAD and HTML .
"""

MODEL = "gpt-35-turbo"
AI = None

def req(msg):
    return [{"role": "system", "content": ROLE}, 
            {"role": "user", "content": msg}]

def ask(input):
    comp = AI.chat.completions.create(model=MODEL, messages=req(input))
    if len(comp.choices) > 0:
        content = comp.choices[0].message.content
        return content
    return "ERROR"


"""
import re
from pathlib import Path
text = Path("util/test/chess.txt").read_text()
text = Path("util/test/html.txt").read_text()
text = Path("util/test/code.txt").read_text()
"""
def extract(text):
    res = {}

    # search for a chess position
    pattern = r'(([rnbqkpRNBQKP1-8]{1,8}/){7}[rnbqkpRNBQKP1-8]{1,8} [bw] (-|K?Q?k?q?) (-|[a-h][36]) \d+ \d+)'
    m = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    #print(m)
    if len(m) > 0:
        res['chess'] = m[0][0]
        return res

    # search for code
    pattern = r"```(\w+)\n(.*?)```"
    m = re.findall(pattern, text, re.DOTALL)
    if len(m) > 0:
        if m[0][0] == "html":
            html = m[0][1]
            # extract the body if any
            pattern = r"<body.*?>(.*?)</body>"
            m = re.findall(pattern, html, re.DOTALL)
            if m:
                html = m[0]
            res['html'] = html
            return res
        res['language'] = m[0][0]
        res['code'] = m[0][1]
        return res
    return res

# custom

def slack_log(_str):
    _uri = 'https://nuvolaris.dev/api/v1/web/utils/demo/slack\?text={TEXT}'
    r = requests.get(_uri.replace('{TEXT}', _str))
    print('sending slack message')
    return r

def check_if_is_mail(_str):
    _finded = False
    _pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if(re.fullmatch(_pattern, _str)):
        r = slack_log(f'Hello from {_str}!')
        _finded = True
    return _finded

def extract_domains(_str):
    _pattern = r"(?<!\w)([a-z0-9-]{5,}\.[a-z]{2,6})(?!\w)"
    matches = re.finditer(_pattern, _str)
    domains = [match.group(1) for match in matches]
    if len(domains) <1: return None
    return domains

def get_ip_by_name(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except socket.herror:
        return None

def find_word(_word):
    return re.compile(r'\b({0})\b'.format(_word), flags=re.IGNORECASE).search

def get_chess_puzzle():
    print("aaa")
    endpoint = 'https://pychess.run.goorm.io/api/puzzle?limit=1'
    r = requests.get(endpoint)
    if r.status_code == 200:
        # do parsing here.
        pass
    return {}

def main(args):
    global AI
    (key, host) = (args["OPENAI_API_KEY"], args["OPENAI_API_HOST"])
    AI = AzureOpenAI(api_version="2023-12-01-preview", api_key=key, azure_endpoint=host)

    input = args.get("input", "")
    if input == "":
        res = {
            "output": "Welcome to the OpenAI demo chat",
            "title": "OpenAI Chat",
            "message": "You can chat with OpenAI. (TEST)"
        }
    else:
        # user has put just an email, no need for ai
        if check_if_is_mail(input):
            res['output'] = 'sended to slack'
            return {"body": res }
        
        # check for domain
        _domains = extract_domains(input)
        if _domains is not None:
            ip = get_ip_by_name(_domains[0])
            if ip is None:
                res['output'] = 'unable to get ip'
                return {"body": res }
            # add more prompt
            tmp = f'Assuming {_domains[0]} has IP address {ip}, answer to this question: ' + input
            slack_log(f'user request ip for {_domains[0]}')
            output = ask(tmp)
            res = extract(output)
            res['output'] = output
            return {"body": res }
        
        # check for chess
        if(False): # chess container is down
            if (find_word('chess')(input) is not None or find_word('scacchi')(input) is not None):
                tmp = f'is the following a request for a chess puzzle: "{input}": Answer Yes or No'
                output = ask(tmp)
                if output.lower() == 'yes':
                    _puzzle_data = get_chess_puzzle()                
                res = extract(output)
                res['output'] = output
                return {"body": res }
        output = ask(input)
        res = extract(output)
        res['output'] = output
    return {"body": res }
