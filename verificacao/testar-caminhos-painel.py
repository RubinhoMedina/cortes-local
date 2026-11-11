from pathlib import Path
import os,subprocess,sys
root=Path(r'C:/Users/Windows/edicao-ia/cortes-app')
sys.path.insert(0,str(root))
os.environ['PATH']=r'C:\Windows\System32'
import app
for name in app.TOOL_PATHS:
    result=subprocess.run([name,'--version' if name in {'deno','yt-dlp'} else '-version'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,(name,result.stderr)
    print(name,'OK com PATH inicial restrito ao Windows')
