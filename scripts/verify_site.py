"""Verify the complete profile transcription, local links, assets and unique IDs."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self,path):
  super().__init__(convert_charrefs=True);self.path=path;self.ids=[];self.links=[];self.assets=[];self.blocks={};self.current=None;self.depth=0;self.skip=0;self.visible=[];self.feed(path.read_text(encoding='utf-8-sig'))
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='a' and 'href' in a:self.links.append(a['href'])
  if tag in ('img','script') and 'src' in a:self.assets.append(a['src'])
  if 'data-profile-block' in a:self.current=a['data-profile-block'];self.blocks.setdefault(self.current,[]).append('');self.depth=1
  elif self.current:self.depth+=1
  if tag in ('script','style'):self.skip+=1
 def handle_endtag(self,tag):
  if self.current:
   self.depth-=1
   if self.depth==0:self.current=None
  if tag in ('script','style'):self.skip-=1
 def handle_data(self,data):
  if self.current:self.blocks[self.current][-1]+=data
  if not self.skip:self.visible.append(data)
def norm(s):return ' '.join(s.split())
pages={p.name:Page(p) for p in ROOT.glob('*.html')};errors=[]
for name,page in pages.items():
 duplicates=[k for k,v in Counter(page.ids).items() if v>1]
 if duplicates:errors.append(f'{name}: duplicate IDs {duplicates}')
 for target in page.links+page.assets:
  u=urlsplit(target)
  if u.scheme or u.netloc:continue
  dest=unquote(u.path) or name
  if not (ROOT/dest).is_file():errors.append(f'{name}: missing file {target}');continue
  if u.fragment and dest in pages and unquote(u.fragment) not in pages[dest].ids:errors.append(f'{name}: missing fragment {target}')
 if re.search(r'Back to (?:Website|all services)',norm(' '.join(page.visible)),re.I):errors.append(f'{name}: redundant return link')
 for target in re.findall(r'url\([\'\"]?([^\)\'\"]+)',page.path.read_text()):
  if not urlsplit(target).scheme and not (ROOT/target).is_file():errors.append(f'{name}: missing CSS image {target}')
manifest=json.loads((ROOT/'docs/profile-source.json').read_text());count=0
assert [p['page'] for p in manifest]==list(range(1,23))
for source in manifest:
 page=pages[source['file']]
 for block in source['blocks']:
  count+=1
  actual=page.blocks.get(block['id'],[])
  if len(actual)!=1 or norm(actual[0])!=norm(block['text']):errors.append(f'{source["file"]}: source mismatch {block["id"]}')
if errors:
 print('\n'.join(errors));sys.exit(1)
print(f'PASS: {len(pages)} HTML pages, {sum(len(p.links) for p in pages.values())} links, 22 PDF pages, {count} exact source blocks; unique IDs and local assets verified.')
