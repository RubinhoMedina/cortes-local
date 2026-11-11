import urllib.request,urllib.error,json,zipfile,io,hashlib
BASE='http://127.0.0.1:3781'
def get(path,headers=None,method=None,data=None):
    req=urllib.request.Request(BASE+path,headers=headers or {},method=method,data=data)
    try:
        r=urllib.request.urlopen(req,timeout=30)
        return r.status,r.headers,r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.headers,e.read()
assert get('/api/health')[0]==200
assert get('/api/jobs',method='POST',data=b'{}')[0]==403
assert get('/api/jobs',{'Origin':'https://example.org','X-Cortes-Local':'1'},'POST',b'{}')[0]==403
assert get('/media/../../app.py')[0]==404
assert get('/api/jobs',{'Host':'example.org'})[0]==403
jobs=json.loads(get('/api/jobs')[2])
ready=[j for j in jobs if j['status']=='ready']
assert ready
for job in ready:
    for clip in job['clips']:
        route='/media/'+job['id']+'/'+clip['media']
        status,headers,payload=get(route,{'Range':'bytes=0-99'})
        assert status==206 and len(payload)==100 and headers['Content-Range'].startswith('bytes 0-99/')
        assert get(route,{'Range':'bytes=9999999999-'})[0]==416
        assert len(clip['covers'])==3
        assert all(get('/media/'+job['id']+'/'+cover)[0]==200 for cover in clip['covers'])
        status,headers,payload=get('/api/bundle/'+job['id']+'/'+clip['id'])
        assert status==200
        z=zipfile.ZipFile(io.BytesIO(payload))
        assert z.testzip() is None
        assert any(name.endswith('.mp4') for name in z.namelist())
        assert any(name.endswith('.txt') for name in z.namelist())
        print(job['id'],clip['id'],'MP4 range, 3 capas e ZIP íntegros')
print('OK: origem, cabeçalho obrigatório, Host, travessia de diretórios, mídia e pacotes.')
