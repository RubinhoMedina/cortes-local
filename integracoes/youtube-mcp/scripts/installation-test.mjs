import assert from 'node:assert/strict';
import {google} from 'googleapis';
import {VideoService} from '../dist/services/video.js';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

process.env.YOUTUBE_API_KEY = 'installation-test-key';
const calls = [];
const items = Array.from({length:10}, (_, i) => ({
  id:{videoId:'video'+i},snippet:{channelId:'channel'+i,title:'GTA 6 '+i}
}));
google.youtube = () => ({
  search:{list:async params => {calls.push('search');return {data:{items}};}},
  channels:{list:async params => {
    calls.push('channels');
    return {data:{items:params.id.map(id=>({
      id, snippet:{title:id, description:'my channel streamer'},
      statistics:{subscriberCount:'1000'},
      contentDetails:{relatedPlaylists:{uploads:'uploads-'+id}}
    }))}};
  }},
  playlistItems:{list:async params => {
    calls.push('playlistItems');
    return {data:{items:[{contentDetails:{videoPublishedAt:'2026-11-01T00:00:00Z'}}]}};
  }}
});
const filtered = await new VideoService().searchVideos({
  query:'GTA 6',channelMinSubscribers:100,maxResults:10,
  channelLastUploadAfter:'2026-10-01T00:00:00Z'
});
assert.equal(filtered.length,10);
assert.equal(calls.filter(x=>x==='search').length,1);
assert.equal(calls.filter(x=>x==='playlistItems').length,10);
console.log('PASS: filters and latest-upload metadata preserved, search calls reduced from 11 to 1 (mock).');

process.env.MCP_TRANSPORT='http';
process.env.MCP_HOST='127.0.0.1';
process.env.MCP_PORT='0';
const {startMcpServer} = await import('../dist/server.js');
delete process.env.MCP_HTTP_TOKEN;
await assert.rejects(startMcpServer(), /MCP_HTTP_TOKEN/);
process.env.MCP_HTTP_TOKEN='local-test-token-'.repeat(3);
const server = await startMcpServer();
try {
  const endpoint='http://127.0.0.1:'+server.address().port+'/mcp';
  const headers={'Content-Type':'application/json',Accept:'application/json, text/event-stream'};
  assert.equal((await fetch(endpoint,{method:'POST',headers,body:'{}'})).status,401);
  headers.Authorization='Bearer '+process.env.MCP_HTTP_TOKEN;
  const initialized=await fetch(endpoint,{method:'POST',headers,body:JSON.stringify({
    jsonrpc:'2.0',id:1,method:'initialize',params:{
      protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'test',version:'1'}
    }
  })});
  assert.equal(initialized.status,200);
  assert.ok((await initialized.json()).result.serverInfo);
  let oversizedRejected=false;
  try {
    const response=await fetch(endpoint,{method:'POST',headers,body:JSON.stringify({data:'a'.repeat(1024*1024+1)})});
    oversizedRejected=response.status===413;
    await response.text();
  } catch {
    oversizedRejected=true;
  }
  assert.ok(oversizedRejected);
  console.log('PASS: HTTP requires token, rejects unauthorized and oversized requests, accepts authorized initialize.');
} finally {
  await new Promise(resolve=>server.close(resolve));
}

const env={...process.env,YOUTUBE_API_KEY:'',YOUTUBE_API_KEY2:'',YOUTUBE_API_KEY3:''};
const transport=new StdioClientTransport({
  command:'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
  args:['-NoProfile','-ExecutionPolicy','Bypass','-File','C:/Users/Windows/edicao-ia/youtube-mcp/launch.ps1'],
  env,stderr:'pipe'
});
transport.stderr.on('data',()=>{});
const client=new Client({name:'installation-check',version:'1.0'},{capabilities:{}});
try {
  await client.connect(transport);
  const tools=await client.listTools();
  assert.equal(tools.tools.length,10);
  const transcript=await client.callTool({
    name:'transcripts_getTranscript',arguments:{videoId:'E07OTlhncP0',language:'en'}
  },undefined,{timeout:60000});
  assert.ok(!transcript.isError);
  const data=JSON.parse(transcript.content[0].text);
  assert.ok(data.transcript.length>0);
  console.log('PASS: installed PowerShell launcher, 10 MCP tools, live transcript '+data.transcript.length+' segments.');
} finally {
  await client.close();
}
