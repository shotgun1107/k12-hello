"""Untrusted Git tag release requests. This is NOT an approval mechanism."""
import re, json
PREFIX='release-request/'
SERVICE=re.compile(r'[a-z][a-z0-9-]{0,31}')
SEMVER=re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')
class InvalidRequest(ValueError): pass
def require(ok):
    if not ok: raise InvalidRequest()
def version_key(s):
    require(isinstance(s,str) and 1<=len(s)<=64)
    m=SEMVER.fullmatch(s); require(m is not None)
    numbers=tuple(int(n) for n in m.group(1,2,3)); require(max(numbers)<2**31)
    pre=m.group(4); parts=[]
    if pre:
        for p in pre.split('.'):
            require(not (p.isdigit() and len(p)>1 and p.startswith('0')))
            parts.append((0,int(p)) if p.isdigit() else (1,p))
    return (*numbers,1 if pre is None else 0,tuple(parts))
def text(value,limit=500):
    require(isinstance(value,str) and 1<=len(value)<=limit and value==value.strip())
    require(all(0x20<=ord(c)<=0x7e or 0xac00<=ord(c)<=0xd7a3 for c in value))
def pairs(items):
    d={}
    for k,v in items:
        require(k not in d); d[k]=v
    return d
def validate(raw,tag,expected_service,last_version=None):
    require(isinstance(raw,bytes) and len(raw)<=4096)
    require(tag.startswith(PREFIX))
    version=tag[len(PREFIX):]; key=version_key(version)
    obj=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs)
    require(isinstance(obj,dict) and set(obj)=={'schema','service','version','summary','tests','requester'})
    require(type(obj['schema']) is int and obj['schema']==1)
    require(isinstance(obj['service'],str) and SERVICE.fullmatch(obj['service']) is not None and obj['service']==expected_service)
    require(obj['version']==version and obj['requester']=='k12-dev-ai')
    text(obj['summary']); text(obj['tests'])
    if last_version is not None: require(key>version_key(last_version))
    return obj
def annotation(raw,tag):
    require(len(raw)<=8192)
    head,sep,body=raw.partition(b'\n\n'); require(sep==b'\n\n')
    fields={}
    for line in head.splitlines():
        k,sep,v=line.partition(b' ')
        require(sep==b' ' and k not in fields); fields[k]=v
    require(set(fields)=={b'object',b'type',b'tag',b'tagger'})
    require(fields[b'type']==b'commit' and fields[b'tag']==tag.encode('ascii'))
    commit=fields[b'object'].decode('ascii')
    require(re.fullmatch('[0-9a-f]{40}',commit) is not None)
    return commit,body
