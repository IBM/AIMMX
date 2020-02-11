from os.path import join, dirname
from github3 import login, GitHubEnterprise, exceptions
import base64, re, os, json
from bs4 import BeautifulSoup
from markdown import markdown, Markdown
from io import StringIO

def markdown_to_text(markdown_string):
    """ Converts a markdown string to plaintext """
    # md -> html -> text since BeautifulSoup can extract text cleanly
    html = markdown(markdown_string)
    #print("html", html)
    # remove code snippets
    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code>', ' ', html)
    html = re.sub(r'<img>(.*?)</img>', ' ', html)
    html = re.sub(r'<a>(.*?)</a>', ' ', html)
    #print("html", html)
    # extract text
    soup = BeautifulSoup(html, "html.parser")
    # print("soup", soup)
    text = ''.join(soup.findAll(text=True))
    # print("text", text)
    return text

def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()

Markdown.output_formats["plain"] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False

def unmark(text):
    return __md.convert(text)

def markdownToText(md):

    md = md.strip()
    # double clena up with 2 different approaches:
    # 1. html markdown
    text = markdown_to_text(md)
    # 2. by text element
    text = unmark(text)
    # remove duplicate symbols
    text = re.sub(r'(=|:|\t|\"|_|-){2,}', "", text)
    # remove empty lines
    # plain = re.sub(r'^\s*$', "", plain)
    text = re.sub(r'\n\s*\n', '\n', text, re.MULTILINE)
    # remove URL
    # text = re.sub(r'\(?https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+\)?', '', text)
    text = re.sub(r'\(?http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\)?', '', text)
    #remove email
    text = re.sub(r'\S*@\S*\s?', '', text)

    # replace consecutives chars by a single one
    text = re.sub(r'(\s|\n)\1+', r'\1', text)

    return text.strip()

def readme_cleanup(markdown_readme):
    plain_readme = markdownToText(markdown_readme)

    return plain_readme
