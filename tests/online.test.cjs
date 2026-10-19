const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
function provider({license='https://creativecommons.org/licenses/by/4.0/', fail=false}={}) {
  const context = vm.createContext({AbortController,setTimeout,clearTimeout,fetch:async url => {
    if(url==='free-catalog.json') return {ok:true,json:async()=>[{id:'free-1',sourceId:'album',title:'Jazz song',matchTitle:'Jazz song',artist:'Artist',genre:'Jazz',licenseName:'CC BY'}]};
    if(fail) throw Error('network');
    return {ok:true,json:async()=>({metadata:{licenseurl:license,creator:'Artist'},files:[{name:'Jazz song.mp3',length:'3:45',size:'1000'}]})};
  }});
  vm.runInContext(fs.readFileSync('js/online.js','utf8')+'\nglobalThis.provider=OnlineMusic;',context);
  return context.provider;
}
test('returns full-length encoded stream, duration and license',async()=>{
 const tracks=await provider().search('jazz');
 assert.equal(tracks.length,1);
 assert.equal(tracks[0].duration,225);
 assert.equal(tracks[0].file,'https://archive.org/download/album/Jazz%20song.mp3');
 assert.match(tracks[0].licenseName,/full track/);
});
test('empty search browses catalog; unknown search returns no tracks',async()=>{
 assert.equal((await provider().search('')).length,1);
 assert.equal((await provider().search('unknown')).length,0);
});
test('does not stream media without an open license',async()=>{
 assert.equal((await provider({license:''}).search('')).length,0);
});
test('provider network failure is actionable',async()=>{
 await assert.rejects(provider({fail:true}).search(''),/Cannot reach/);
});
